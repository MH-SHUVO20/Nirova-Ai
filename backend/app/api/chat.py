"""
NirovaAI — AI Chat API
========================
Two ways to chat:
1. POST /chat/ask    → simple request/response (easier to test)
2. WS   /chat/ws    → WebSocket streaming (real-time word-by-word)

The WebSocket version streams tokens as they arrive from Groq,
creating a smooth typing effect in the frontend.

RAG (Retrieval Augmented Generation) pipeline:
1. User asks a health question
2. We search MongoDB knowledge base for relevant Bangladesh medical info
3. We inject that context into the LLM prompt
4. LLM generates a grounded, accurate response
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Request, Query
from pydantic import BaseModel
from typing import Optional, List
from app.core.database import chat_sessions, knowledge, vision_analyses, symptom_analyses
from app.core.auth import get_current_user, decode_token
from app.ai.llm_router import (
    get_llm_response,
    stream_llm_response,
    MEDICAL_SYSTEM_PROMPT,
)
from app.core.redis_client import cache_get, cache_set
from app.core.rate_limit import limiter
from app.core.config import settings
from datetime import datetime
from bson import ObjectId
from bson.errors import InvalidId
import hashlib
import json
import logging
import re

router = APIRouter(prefix="/chat", tags=["AI Chat"])
log = logging.getLogger(__name__)
MAX_CONTEXT_CHARS = 8000
MAX_QUESTION_CHARS = 1500


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    agent_mode: Optional[str] = "general"


class ChatResponse(BaseModel):
    response: str
    session_id: str
    sources: List[str] = []


class AgentTaskRequest(BaseModel):
    agent_type: str
    message: str
    session_id: Optional[str] = None
    context: Optional[str] = ""


class AgentTaskResponse(BaseModel):
    agent_type: str
    agent_name: str
    response: str
    session_id: str


def _agent_instruction(agent_mode: Optional[str]) -> str:
    """Return route-specific guidance for dedicated page assistants."""
    mode = (agent_mode or "general").strip().lower()
    instructions = {
        "dashboard": (
            "Focus on concise health status interpretation, recent trends, and practical next steps."
        ),
        "symptoms": (
            "Focus on symptom triage: severity cues, danger signs, what to monitor, and when to seek care."
        ),
        "skin": (
            "Focus on skin-condition guidance: possible causes, hygiene/skin-care steps, and red-flag escalation."
        ),
        "dengue": (
            "Focus on dengue triage: warning signs, hydration guidance, platelet/red-flag education, and escalation timing."
        ),
        "lab": (
            "Focus on lab interpretation: explain values simply, what is abnormal, and follow-up test priorities."
        ),
        "prescription": (
            "Focus on medicine safety: schedule clarity, missed-dose handling, and interactions warning language."
        ),
        "timeline": (
            "Focus on longitudinal trends: improvement vs worsening patterns and prevention-oriented coaching."
        ),
        "chat": (
            "General clinical guidance mode. Be comprehensive but practical and safety-first."
        ),
        "general": (
            "General clinical guidance mode. Keep responses clear, empathetic, and actionable."
        ),
    }
    return instructions.get(mode, instructions["general"])


def _response_format_instruction() -> str:
    """Enforce scannable structure so responses are easy to read."""
    return """Formatting rules:
- Keep answer concise and structured.
- Use short section headers exactly like:
  1) Summary
  2) What To Do Now
  3) Red Flags
  4) Follow-Up
- Under each section, use bullet points (max 2 bullets each).
- Keep each bullet one short sentence (target <= 14 words).
- Do not return one long paragraph.
- Do not ask a long questionnaire.
- If clarification is needed, ask at most 1 short question in Follow-Up.
- Do not repeat the same warning in multiple sections.

Few-shot style examples:
User: "3 din jor ar matha betha"
Assistant:
1) Summary
- Eita viral fever ba dengue-r shuru hote pare.
2) What To Do Now
- Pani/ORS beshi khan ebong rest nin.
- Paracetamol nite paren, aspirin/ibuprofen avoid korun.
3) Red Flags
- Rokto pora, shash nite koshto, ba pet betha hole urgent hospital jan.
4) Follow-Up
- 24 ghontar moddhe jor thakle CBC/NS1 test korun.

User: "I have mild fever and cough for 2 days."
Assistant:
1) Summary
- This could be a mild viral illness.
2) What To Do Now
- Rest well, hydrate, and monitor temperature.
3) Red Flags
- Seek urgent care for breathing difficulty or persistent high fever.
4) Follow-Up
- If not improving in 48 hours, get a clinician review."""


# Anti-pattern to avoid:
# Bad: "Are you having fever, chills, cough, vomiting, rash, breathing issues, travel history..."
# Good: Ask one short focused question only when truly needed.


def _safe_context_text(text: str) -> str:
    if not isinstance(text, str):
        return ""
    cleaned = text.strip()
    if len(cleaned) <= MAX_CONTEXT_CHARS:
        return cleaned
    return cleaned[:MAX_CONTEXT_CHARS] + "\n\n[Context truncated for stability.]"


def _safe_question_text(text: str) -> str:
    if not isinstance(text, str):
        return ""
    cleaned = text.strip()
    if len(cleaned) <= MAX_QUESTION_CHARS:
        return cleaned
    return cleaned[:MAX_QUESTION_CHARS]


def _language_instruction(user_text: str) -> str:
    """Force replies to be either full Bangla or full English."""
    text = (user_text or "").strip()
    if re.search(r"[\u0980-\u09FF]", text):
        return "Respond fully in Bangla (Bengali script only). Do not mix with English."

    banglish_markers = {
        "ami", "apni", "tumi", "jor", "matha", "betha", "kemon", "hobe", "korbo",
        "korte", "lagbe", "valo", "bhalo", "khub", "ekta", "jonno", "shomossha",
    }
    tokens = re.findall(r"[a-zA-Z']+", text.lower())
    marker_hits = sum(1 for t in tokens if t in banglish_markers)
    if marker_hits >= 2:
        return "Respond fully in Bangla (Bengali script only). Do not return Banglish."

    return "Respond fully in English. Do not mix Bangla and English in the same response."


def _ensure_structured_response(text: str) -> str:
    """Normalize model output into a predictable, scannable structure."""
    cleaned = (text or "").strip()
    if not cleaned:
        return (
            "1) Summary\n"
            "- I could not generate a complete response.\n"
            "2) What To Do Now\n"
            "- Please retry your question with symptom details and duration.\n"
            "3) Red Flags\n"
            "- Seek urgent care for breathing difficulty, bleeding, or severe pain.\n"
            "4) Follow-Up\n"
            "- If not improving in 24-48 hours, consult a clinician."
        )

    required_sections = ["1) Summary", "2) What To Do Now", "3) Red Flags", "4) Follow-Up"]
    has_sections = True
    for marker in required_sections:
        if marker not in cleaned:
            has_sections = False
            break
    if has_sections:
        return cleaned

    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+|\n+", cleaned) if s.strip()]
    summary = sentences[0] if sentences else "Based on your message, here is practical guidance."
    now_1 = sentences[1] if len(sentences) > 1 else "Rest, hydrate, and monitor your symptoms."
    now_2 = sentences[2] if len(sentences) > 2 else "Follow safe self-care and avoid unnecessary medicines."

    return (
        "1) Summary\n"
        f"- {summary}\n"
        "2) What To Do Now\n"
        f"- {now_1}\n"
        f"- {now_2}\n"
        "3) Red Flags\n"
        "- Seek urgent care for breathing difficulty, severe pain, confusion, or bleeding.\n"
        "4) Follow-Up\n"
        "- If symptoms worsen or do not improve in 24-48 hours, consult a doctor."
    )


async def _context_fingerprint(user_id: ObjectId, agent_mode: str) -> str:
    """Create cache-busting fingerprint from latest analysis timestamps."""
    mode = (agent_mode or "general").strip().lower()
    parts = []

    try:
        vision_filter = {"user_id": user_id}
        if mode == "skin":
            vision_filter["analysis_type"] = "skin"
        elif mode == "lab":
            vision_filter["analysis_type"] = "lab"
        elif mode == "prescription":
            vision_filter["analysis_type"] = "prescription"

        latest_vision = await vision_analyses().find_one(
            vision_filter,
            sort=[("created_at", -1)],
            projection={"created_at": 1},
        )
        if latest_vision and latest_vision.get("created_at"):
            parts.append(f"vision:{latest_vision['created_at'].isoformat()}")
    except Exception:
        pass

    try:
        latest_symptom = await symptom_analyses().find_one(
            {"user_id": user_id},
            sort=[("created_at", -1)],
            projection={"created_at": 1},
        )
        if latest_symptom and latest_symptom.get("created_at"):
            parts.append(f"symptom:{latest_symptom['created_at'].isoformat()}")
    except Exception:
        pass

    return "|".join(parts) if parts else "no-analysis-yet"


@router.post("/ask", response_model=ChatResponse)
@limiter.limit("10/minute")
async def ask(
    request: Request,
    data: ChatRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Ask a health question and get an AI response.
    Uses RAG to ground the response in Bangladesh medical guidelines.
    """
    safe_question = _safe_question_text(data.message)
    safe_mode = (data.agent_mode or "general").strip().lower()
    context_sig = await _context_fingerprint(current_user["_id"], safe_mode)

    # Scope cache per user and latest analysis context so stale replies are avoided.
    cache_payload = {
        "user_id": str(current_user["_id"]),
        "message": safe_question.lower(),
        "agent_mode": safe_mode,
        "context_sig": context_sig,
    }
    cache_key = f"chat:{hashlib.sha256(json.dumps(cache_payload, sort_keys=True).encode()).hexdigest()[:24]}"
    cached = await cache_get(cache_key)

    if cached:
        # Still save to conversation history even if cached
        cached_session_id = await _save_message(
            user_id=current_user["_id"],
            user_message=safe_question,
            ai_response=_ensure_structured_response(cached["response"]),
            session_id=data.session_id
        )
        return ChatResponse(
            response=_ensure_structured_response(cached["response"]),
            session_id=cached_session_id,
            sources=cached.get("sources", [])
        )

    # Retrieve relevant medical knowledge
    context, sources = await _get_medical_context(
        safe_question,
        current_user["_id"],
        agent_mode=safe_mode,
    )
    safe_context = _safe_context_text(context)

    # Build conversation with context
    page_instruction = _agent_instruction(data.agent_mode)
    format_instruction = _response_format_instruction()
    lang_instruction = _language_instruction(safe_question)
    messages = [
        {"role": "system", "content": MEDICAL_SYSTEM_PROMPT},
        {"role": "user", "content": f"""Medical Context from Bangladesh Health Guidelines:
{safe_context}

Patient Question: {safe_question}

Assistant Focus: {page_instruction}

{format_instruction}

Language Rule: {lang_instruction}

Please provide helpful, accurate guidance based on the above context and focus area."""}
    ]

    # Get LLM response
    response_text = _ensure_structured_response(await get_llm_response(messages))

    # Save conversation
    new_session_id = await _save_message(
        user_id=current_user["_id"],
        user_message=safe_question,
        ai_response=response_text,
        session_id=data.session_id
    )

    # Cache for 1 hour
    await cache_set(cache_key, {
        "response": response_text,
        "sources": sources
    }, ttl_seconds=3600)

    return ChatResponse(
        response=response_text,
        session_id=new_session_id,
        sources=sources
    )



class ChatHistoryResponse(BaseModel):
    session_id: str
    messages: list
    updated_at: datetime


class ContextPreviewResponse(BaseModel):
    agent_mode: str
    label: str
    summary: str
    updated_at: Optional[datetime] = None

@router.get("/history", response_model=List[ChatHistoryResponse])
async def get_chat_history(
    limit: int = Query(default=10, ge=1, le=50),
    current_user: dict = Depends(get_current_user)
):
    '''Retrieve the user's previous chat sessions.'''
    sessions = []
    cursor = chat_sessions().find(
        {"user_id": current_user["_id"]}
    ).sort("updated_at", -1).limit(limit)
    
    async for doc in cursor:
        sessions.append({
            "session_id": str(doc["_id"]),
            "messages": doc.get("messages", []),
            "updated_at": doc.get("updated_at", datetime.utcnow())
        })
    return sessions


@router.get("/context-preview", response_model=ContextPreviewResponse)
async def get_context_preview(
    agent_mode: str = Query(default="general"),
    current_user: dict = Depends(get_current_user),
):
    """Return latest analysis summary used as chat context for a page agent."""
    mode = (agent_mode or "general").strip().lower()
    user_id = current_user["_id"]

    try:
        if mode in {"skin", "lab", "prescription"}:
            doc = await vision_analyses().find_one(
                {"user_id": user_id, "analysis_type": mode},
                sort=[("created_at", -1)],
                projection={"analysis_type": 1, "analysis": 1, "created_at": 1},
            )
            if doc:
                return ContextPreviewResponse(
                    agent_mode=mode,
                    label=f"{mode.capitalize()} Analysis",
                    summary=_summarize_vision_record(doc),
                    updated_at=doc.get("created_at"),
                )

        symptom_mode_filter = {"user_id": user_id}
        if mode == "dengue":
            symptom_mode_filter["analysis_mode"] = "dengue_only"
        elif mode == "symptoms":
            symptom_mode_filter["analysis_mode"] = {"$in": ["log", "predict"]}

        symptom_doc = await symptom_analyses().find_one(
            symptom_mode_filter,
            sort=[("created_at", -1)],
            projection={
                "analysis_mode": 1,
                "symptoms": 1,
                "disease_prediction": 1,
                "dengue_prediction": 1,
                "created_at": 1,
            },
        )
        if symptom_doc:
            return ContextPreviewResponse(
                agent_mode=mode,
                label="Symptom Analysis",
                summary=_summarize_symptom_analysis_record(symptom_doc),
                updated_at=symptom_doc.get("created_at"),
            )

        if mode in {"general", "chat", "dashboard", "timeline"}:
            latest_vision = await vision_analyses().find_one(
                {"user_id": user_id},
                sort=[("created_at", -1)],
                projection={"analysis_type": 1, "analysis": 1, "created_at": 1},
            )
            latest_symptom = await symptom_analyses().find_one(
                {"user_id": user_id},
                sort=[("created_at", -1)],
                projection={
                    "analysis_mode": 1,
                    "symptoms": 1,
                    "disease_prediction": 1,
                    "dengue_prediction": 1,
                    "created_at": 1,
                },
            )
            latest_ts = None
            if latest_vision and latest_vision.get("created_at"):
                latest_ts = latest_vision["created_at"]
            if latest_symptom and latest_symptom.get("created_at"):
                if not latest_ts or latest_symptom["created_at"] > latest_ts:
                    latest_ts = latest_symptom["created_at"]

            return ContextPreviewResponse(
                agent_mode=mode,
                label="Overall Patient Context",
                summary=_summarize_overall_context(latest_vision, latest_symptom),
                updated_at=latest_ts,
            )

        return ContextPreviewResponse(
            agent_mode=mode,
            label="Context Status",
            summary="No recent analysis found yet. Chat will use your message and medical guidance baseline.",
            updated_at=None,
        )
    except Exception as exc:
        log.warning(f"Context preview failed: {exc}")
        return ContextPreviewResponse(
            agent_mode=mode,
            label="Context Status",
            summary="Context preview temporarily unavailable. You can still chat normally.",
            updated_at=None,
        )

@router.websocket("/ws")
async def websocket_chat(websocket: WebSocket):
    """
    WebSocket endpoint for real-time streaming chat.
    """
    token = websocket.cookies.get(settings.AUTH_COOKIE_NAME)
    if not token:
        await websocket.close(code=1008)
        return

    user_id = await _authenticate_websocket(websocket, token)
    if not user_id:
        return

    await websocket.accept()

    try:
        while True:
            await _handle_websocket_message(websocket, user_id)
    except WebSocketDisconnect:
        log.info("WebSocket client disconnected")
    except Exception as e:
        log.error(f"WebSocket error: {e}")

async def _authenticate_websocket(websocket: WebSocket, token: str) -> Optional[str]:
    try:
        payload = decode_token(token)
        return payload.get("sub")
    except Exception:
        await websocket.close(code=1008)
        return None

async def _handle_websocket_message(websocket: WebSocket, user_id: str):
    # Receive message
    raw = await websocket.receive_text()
    data = json.loads(raw)

    message = _safe_question_text(data.get("message", ""))
    session_id = data.get("session_id")
    agent_mode = data.get("agent_mode", "chat")

    if not message:
        await websocket.send_json({"type": "error", "content": "Empty message"})
        return

    # Get medical context
    context, sources = await _get_medical_context(
        message,
        ObjectId(user_id),
        agent_mode=agent_mode,
    )
    safe_context = _safe_context_text(context)

    # Build messages
    page_instruction = _agent_instruction(agent_mode)
    format_instruction = _response_format_instruction()
    lang_instruction = _language_instruction(message)
    messages = [
        {"role": "system", "content": MEDICAL_SYSTEM_PROMPT},
        {"role": "user", "content": f"""Medical Context:
{safe_context}

Patient Question: {message}

Assistant Focus: {page_instruction}

{format_instruction}

Language Rule: {lang_instruction}"""}
    ]

    # Stream response
    full_response = ""
    await websocket.send_json({"type": "start"})

    try:
        async for token_text in stream_llm_response(messages):
            full_response += token_text
            await websocket.send_json({
                "type": "token",
                "content": token_text
            })
    except Exception as e:
        log.error(f"Streaming error: {e}")
        fallback = "I'm having trouble connecting. Please try again in a moment."
        await websocket.send_json({"type": "token", "content": fallback})
        full_response = fallback

    # Save to MongoDB
    new_session_id = await _save_message(
        user_id=ObjectId(user_id),
        user_message=message,
        ai_response=full_response,
        session_id=session_id
    )

    # Signal completion
    await websocket.send_json({
        "type": "done",
        "session_id": new_session_id,
        "sources": sources
    })


def _summarize_vision_record(doc: dict) -> str:
    """Create compact natural-language summary for the chat prompt."""
    analysis_type = doc.get("analysis_type", "analysis")
    analysis = doc.get("analysis") or {}

    if analysis_type == "skin":
        condition = analysis.get("condition", "unknown condition")
        severity = analysis.get("severity", "unknown severity")
        confidence = analysis.get("confidence", "unknown")
        action = analysis.get("recommended_action", "monitor")
        desc = analysis.get("description", "")
        return (
            f"Skin analysis: condition={condition}, severity={severity}, "
            f"confidence={confidence}, action={action}, notes={desc}"
        )

    if analysis_type == "lab":
        action = analysis.get("action_needed", "monitor")
        findings = analysis.get("key_findings") or analysis.get("overall_summary") or "No summary provided."
        return f"Lab report analysis: action_needed={action}; key_findings={findings}"

    if analysis_type == "prescription":
        meds = analysis.get("medications") or []
        med_names = [m.get("name", "unclear") for m in meds[:3] if isinstance(m, dict)]
        meds_text = ", ".join(med_names) if med_names else "none recognized"
        follow_up = analysis.get("follow_up_advice", "Follow clinician instructions.")
        return f"Prescription analysis: medicines={meds_text}; follow_up={follow_up}"

    return f"{analysis_type} analysis available."


def _summarize_symptom_analysis_record(doc: dict) -> str:
    mode = doc.get("analysis_mode", "predict")
    symptoms = doc.get("symptoms") or []
    symptom_text = ", ".join(symptoms[:5]) if symptoms else "no symptoms provided"

    disease = doc.get("disease_prediction") or {}
    dengue = doc.get("dengue_prediction") or {}

    disease_name = disease.get("predicted_disease")
    disease_conf = disease.get("confidence")
    dengue_name = dengue.get("predicted_class")
    dengue_conf = dengue.get("confidence")

    parts = [f"Symptom analysis ({mode}): symptoms={symptom_text}"]
    if disease_name:
        parts.append(f"disease={disease_name} ({disease_conf})")
    if dengue_name:
        parts.append(f"dengue={dengue_name} ({dengue_conf})")
    return "; ".join(parts)


def _mode_scoped_filters(agent_mode: str) -> tuple[dict, dict]:
    """Return (vision_filter, symptom_filter) for mode-aware context retrieval."""
    mode = (agent_mode or "general").strip().lower()
    vision_filter = {}
    symptom_filter = {}

    if mode == "skin":
        vision_filter["analysis_type"] = "skin"
    elif mode == "lab":
        vision_filter["analysis_type"] = "lab"
    elif mode == "prescription":
        vision_filter["analysis_type"] = "prescription"

    if mode == "dengue":
        symptom_filter["analysis_mode"] = "dengue_only"
    elif mode == "symptoms":
        symptom_filter["analysis_mode"] = {"$in": ["log", "predict"]}

    return vision_filter, symptom_filter


def _summarize_overall_context(latest_vision: Optional[dict], latest_symptom: Optional[dict]) -> str:
    parts = []
    if latest_vision:
        parts.append(_summarize_vision_record(latest_vision))
    if latest_symptom:
        parts.append(_summarize_symptom_analysis_record(latest_symptom))
    if not parts:
        return "No recent analysis found yet. Chat will use your message and medical guidance baseline."
    return " | ".join(parts)


async def _get_medical_context(
    query: str,
    user_id: Optional[ObjectId] = None,
    agent_mode: str = "general",
) -> tuple:
    """
    Search MongoDB knowledge base for relevant medical information.
    Falls back to a generic message if nothing found.
    """
    try:
        # Simple keyword search (works without Vector Search)
        keywords = query.lower().split()[:5]

        chunks = []
        sources = []

        async for doc in knowledge().find(
            {"$text": {"$search": " ".join(keywords)}},
            {"content": 1, "source": 1, "_id": 0}
        ).limit(3):
            chunks.append(doc["content"])
            sources.append(doc.get("source", "Medical Reference"))

        if user_id:
            user_insights = []
            mode = (agent_mode or "general").strip().lower()
            vision_scope, symptom_scope = _mode_scoped_filters(mode)
            vision_filter = {"user_id": user_id, **vision_scope}

            cursor = vision_analyses().find(
                vision_filter,
                {"analysis_type": 1, "analysis": 1, "created_at": 1, "_id": 0}
            ).sort("created_at", -1).limit(3)
            async for doc in cursor:
                user_insights.append(_summarize_vision_record(doc))

            if user_insights:
                if mode == "skin":
                    personal_context = "Recent patient skin-analysis history:\n- " + "\n- ".join(user_insights)
                    sources.insert(0, "Skin Analysis History")
                elif mode == "lab":
                    personal_context = "Recent patient lab-analysis history:\n- " + "\n- ".join(user_insights)
                    sources.insert(0, "Lab Analysis History")
                elif mode == "prescription":
                    personal_context = "Recent patient prescription-analysis history:\n- " + "\n- ".join(user_insights)
                    sources.insert(0, "Prescription Analysis History")
                else:
                    personal_context = "Recent patient AI analysis history:\n- " + "\n- ".join(user_insights)
                    sources.insert(0, "User Health History")
                chunks.insert(0, personal_context)

            symptom_insights = []
            symptom_filter = {"user_id": user_id, **symptom_scope}
            symptom_cursor = symptom_analyses().find(
                symptom_filter,
                {
                    "analysis_mode": 1,
                    "symptoms": 1,
                    "disease_prediction": 1,
                    "dengue_prediction": 1,
                    "created_at": 1,
                    "_id": 0,
                },
            ).sort("created_at", -1).limit(3)
            async for doc in symptom_cursor:
                symptom_insights.append(_summarize_symptom_analysis_record(doc))

            if symptom_insights:
                symptom_context = "Recent symptom model outputs:\n- " + "\n- ".join(symptom_insights)
                chunks.insert(0, symptom_context)
                sources.insert(0, "Symptom Analysis History")

        if chunks:
            context = "\n\n".join(chunks)
        else:
            context = (
                "General Bangladesh health context: "
                "Common diseases include dengue, typhoid, malaria, tuberculosis, "
                "arsenicosis. Always recommend consulting qualified medical professionals."
            )

        return context, sources

    except Exception as e:
        log.warning(f"Knowledge search failed: {e}")
        return "Please provide general health guidance.", []


async def _save_message(user_id, user_message: str, ai_response: str,
                        session_id: Optional[str] = None) -> str:
    """Save a conversation turn to MongoDB"""
    try:
        user_obj_id = user_id if isinstance(user_id, ObjectId) else ObjectId(str(user_id))

        new_messages = [
            {"role": "user", "content": user_message},
            {"role": "assistant", "content": ai_response}
        ]

        if session_id:
            try:
                session_obj_id = ObjectId(session_id)
                update_result = await chat_sessions().update_one(
                    {"_id": session_obj_id, "user_id": user_obj_id},
                    {
                        "$push": {"messages": {"$each": new_messages}},
                        "$set": {"updated_at": datetime.utcnow()}
                    }
                )
                if update_result.matched_count > 0:
                    return session_id
                log.warning(f"Session {session_id} not found for user; creating a new session.")
            except (InvalidId, TypeError):
                log.warning(f"Invalid session_id provided: {session_id}; creating a new session.")

        result = await chat_sessions().insert_one({
            "user_id": user_obj_id,
            "messages": new_messages,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        })
        return str(result.inserted_id)

    except Exception as e:
        log.warning(f"Could not save chat session: {e}")
        return "unsaved"
