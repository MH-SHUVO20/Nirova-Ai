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

Medical Safety:
- All inputs are validated for length and content
- Medical emergency keywords trigger safe fallback responses
- LLM timeouts have graceful recovery with safe guidance
- No medical data is ever exposed in error messages
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Request, Query
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from app.core.database import chat_sessions, vision_analyses, symptom_analyses
from app.core.auth import get_current_user
from app.ai.llm_router import (
    get_llm_response,
    stream_llm_response,
    MEDICAL_SYSTEM_PROMPT,
)
from app.ai.agents.langgraph_orchestrator import run_langgraph_chat, ChatGraphDeps
from app.ai.rag.retriever import retrieve_knowledge, build_knowledge_context
from app.core.redis_client import cache_get, cache_set
from app.core.rate_limit import limiter
from app.core.config import settings
from datetime import datetime, timezone
from bson import ObjectId
from bson.errors import InvalidId
import hashlib
import json
import logging
import re
import asyncio

router = APIRouter(prefix="/chat", tags=["AI Chat"])
log = logging.getLogger(__name__)
MAX_CONTEXT_CHARS = 8000
MAX_QUESTION_CHARS = 1500
MAX_CLIENT_CONTEXT_CHARS = 2000
WEBSOCKET_TIMEOUT_SECONDS = 60
CACHE_SCHEMA_VERSION = "chat-v2"


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=MAX_QUESTION_CHARS)
    session_id: Optional[str] = Field(None, max_length=100)
    agent_mode: Optional[str] = Field("general", max_length=50)
    client_context: Optional[str] = Field("", max_length=MAX_CLIENT_CONTEXT_CHARS)
    language: Optional[str] = Field("en", max_length=10)  # "en" or "bn"
    
    @field_validator('message')
    def validate_message(cls, v):
        """Validate message content for safety."""
        v = v.strip()
        if not v:
            raise ValueError("Message cannot be empty")
        if len(v) > MAX_QUESTION_CHARS:
            raise ValueError(f"Message too long (max {MAX_QUESTION_CHARS} characters)")
        # Check for potential injection attacks
        if any(char in v for char in ['\x00', '\r']):
            raise ValueError("Invalid characters in message")
        return v
    
    @field_validator('agent_mode')
    def validate_agent_mode(cls, v):
        """Validate agent mode."""
        valid_modes = [
            "general", "dashboard", "symptoms", "skin", "dengue",
            "lab", "prescription", "timeline", "chat"
        ]
        if v and v.lower() not in valid_modes:
            raise ValueError(f"Invalid agent mode. Must be one of: {', '.join(valid_modes)}")
        return v or "general"
    
    @field_validator('client_context')
    def validate_client_context(cls, v):
        """Validate client context."""
        if not v:
            return ""
        v = v.strip()
        if len(v) > MAX_CLIENT_CONTEXT_CHARS:
            return v[:MAX_CLIENT_CONTEXT_CHARS]
        return v


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


def _is_conversational_only(text: str) -> bool:
    """Detect if a question is purely conversational (identity, greeting) with no health content."""
    text = (text or "").strip().lower()
    
    # Health-related keywords that indicate this is NOT purely conversational
    health_keywords = [
        "symptom", "fever", "pain", "ache", "disease", "sick", "illness", "disorder",
        "problem", "issue", "medicine", "doctor", "hospital", "treatment", "cure",
        "condition", "suffer", "weak", "tired", "headache", "stomach", "chest",
        "breath", "cough", "cold", "flu", "dengue", "malaria", "vaccine", "blood",
        "test", "report", "prescription", "drug", "pill", "tablet", "injection",
        "skin", "rash", "allergy", "infection", "swelling", "bleeding", "wound",
        "vomit", "diarrhea", "nausea", "dizziness", "anxiety", "depression",
        "health", "fitness", "diet", "exercise", "sleep", "stress", "anxiety",
        # Bengali health keywords
        "সমস্যা", "সিম", "সিমটম", "রোগ", "অসুস্থ", "চিকিৎসা", "ওষুধ", "ডাক্তার",
        "জ্বর", "ব্যথা", "ঘা", "রক্ত", "পরীক্ষা", "প্রেসক্রিপশন",
        # Banglish health keywords
        "hoise", "hoyese", "osudh", "roggy", "daktar", "jor", "betha", "khom"
    ]
    
    # Check if any health keyword exists and this isn't JUST a language request
    has_health_keyword = any(kw in text for kw in health_keywords)
    
    # Even if "banglai bolo" is present, if there's a health keyword, it's not purely conversational
    if has_health_keyword:
        return False
    
    # Conversational patterns (only language/greeting/identity requests with no health content)
    conversational_patterns = [
        r"^\s*(who|what).{0,20}are you",
        r"^\s*(hi|hello|hey)\s*[?.]?\s*$",
        r"^\s*(kemon|kemono|komon|kiman).{0,5}(acho|acen|achhen)\s*[?.]?\s*$",  # Bengali: how are you
        r"^\s*(tumi|apni|ami).{0,5}(ke|keo)\s*[?.]?\s*$",  # Bengali: who are you
        r"^\s*(তুমি|আপনি).{0,10}(কে|কী)\s*[?.]?\s*$",  # Bengali script: who are you
        r"(banglai|bengali|बangla).*\b(bolo|bol|speak)\b",  # "speak in bengali" (only if no health keywords)
        r"^\s*help\s*[?.]?\s*$",
        r"^\s*intro\s*[?.]?\s*$",
    ]
    
    for pattern in conversational_patterns:
        if re.search(pattern, text):
            return True
    return False


def _response_format_instruction() -> str:
    """Enforce scannable structure so responses are easy to read for HEALTH queries only."""
    return """CRITICAL FORMAT RULES:

** FOR CONVERSATIONAL QUERIES ONLY (greetings like "Hi", "Hello", identity questions like "Who are you?", "তুমি কে?"):
- NEVER use 4-section format
- NEVER use numbered sections  
- NEVER use bullets like "1) Summary" or "- " lists
- Respond as a SINGLE natural paragraph or 2-3 short paragraphs
- Be warm and friendly
- Simply answer their question naturally

** FOR HEALTH/SYMPTOM QUERIES ONLY:
- Use EXACTLY this 4-section format with headers:
  1) Summary
  2) What To Do Now
  3) Red Flags
  4) Follow-Up
- Under each section use bullet points (max 2-3 bullets)
- Keep bullets short (≤14 words each)

EXAMPLES:
---
User: "Hi"
Assistant: Hi! I'm NirovaAI, your health assistant. I'm here to help you understand symptoms and get guidance on next steps. What's bothering you?
[WRONG FORMAT - no sections, just natural text]

User: "Who are you?"  
Assistant: I'm NirovaAI, a primary-level health AI assistant built for Bangladesh. I help people understand their symptoms and suggest when to see a doctor. How can I help you today?
[WRONG FORMAT - no sections, just warm intro]

User: "I have fever for 2 days"
Assistant:
1) Summary
- Fever for 2 days could be viral or dengue.
2) What To Do Now
- Rest and drink plenty of water.
3) Red Flags
- See a doctor immediately if severe headache, vomiting, or difficulty breathing.
4) Follow-Up
- Get tested if fever continues beyond 48 hours.
[CORRECT - uses 4 sections for health query]

---

KEY DETECTION: If the user's message contains ANY health-related words (fever, pain, symptom, medicine, doctor, etc.), use the 4-section format. Otherwise, respond naturally."""


def _conversational_brief_instruction() -> str:
    """Force short, natural greeting/identity replies for conversational-only prompts."""
    return (
        "Conversational-only rule: Reply in 1-2 short sentences (max 35 words total). "
        "Do not provide diagnosis, triage sections, or detailed advice unless user asks a health question. "
        "Be warm, direct, and concise."
    )


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


def _language_instruction(user_text: str, language_pref: Optional[str] = None) -> str:
    """Force replies to be either full Bangla or full English."""
    # If user explicitly selected a language in the frontend, respect that FIRST
    if language_pref:
        if language_pref.lower() in ["bn", "bangla"]:
            return "Respond fully in Bangla (Bengali script only). Do not mix with English or Banglish."
        elif language_pref.lower() in ["en", "english"]:
            return "Respond fully in English. Do not mix Bangla and English in the same response."
    
    text = (user_text or "").strip()
    lower_text = text.lower()

    # Explicit language request in English words (user's intention in message overrides frontend setting).
    if any(kw in lower_text for kw in ["in bangla", "bangla", "bengali", "বাংলা"]):
        return "Respond fully in Bangla (Bengali script only). Do not mix with English."
    if any(kw in lower_text for kw in ["in english", "english"]):
        return "Respond fully in English. Do not mix Bangla and English in the same response."

    if re.search(r"[\u0980-\u09FF]", text):
        return "Respond fully in Bangla (Bengali script only). Do not mix with English."

    banglish_markers = {
        "ami", "apni", "tumi", "jor", "matha", "betha", "kemon", "hobe", "korbo",
        "korte", "lagbe", "valo", "bhalo", "khub", "ekta", "jonno", "shomossha",
        "amar", "ki", "kora", "uchit", "akhn", "ekhon", "hoise", "hoyese", "bolo",
        "bolen", "kisu", "kichu", "shorir", "osudh", "rog", "bujhte",
    }
    tokens = re.findall(r"[a-zA-Z']+", text.lower())
    marker_hits = sum(1 for t in tokens if t in banglish_markers)
    if marker_hits >= 2:
        return "Respond fully in Bangla (Bengali script only). Do not return Banglish."

    # Extra banglish phrase signal (common romanized Bengali question pattern).
    if re.search(r"\b(ki|keno|kibhabe|amar|korbo|uchit|akhn|ekhon)\b", text.lower()):
        return "Respond fully in Bangla (Bengali script only). Do not return Banglish."

    return "Respond fully in English. Do not mix Bangla and English in the same response."


def _rewrite_language_switch_message(user_text: str) -> str:
    """
    If user sends only a language-switch command (e.g. 'in bangla'),
    convert it to a clear instruction tied to latest context.
    """
    text = (user_text or "").strip()
    lower_text = text.lower()
    compact = re.sub(r"\s+", " ", lower_text)

    bangla_only_cmds = {
        "bangla", "in bangla", "বাংলা", "bangla answer", "reply in bangla", "বাংলায় বলো", "বাংলায় বলো"
    }
    english_only_cmds = {
        "english", "in english", "english answer", "reply in english"
    }

    if compact in bangla_only_cmds:
        return "Please explain my latest health context in Bangla, briefly and without repeating points."
    if compact in english_only_cmds:
        return "Please explain my latest health context in English, briefly and without repeating points."
    return text


def _grounding_instruction(external_evidence_available: bool) -> str:
    if external_evidence_available:
        return (
            "Grounding rule: Use only facts supported by provided context and patient data. "
            "If information is missing, say uncertainty clearly and ask one focused follow-up question."
        )
    return (
        "Grounding rule: External guideline evidence is weak for this query. "
        "Do not invent facts. Give conservative guidance and ask one focused follow-up question."
    )


def _requires_bangla(lang_instruction: str) -> bool:
    return "Bangla (Bengali script only)" in (lang_instruction or "")



def _all_sections_bangla(text: str) -> bool:
    """Check if all four sections contain Bengali script."""
    if not text:
        return False
    # Find the four sections
    pattern = re.compile(
        r"(1\)\s*Summary|2\)\s*What\s*To\s*Do\s*Now|3\)\s*Red\s*Flags|4\)\s*Follow-?\s*Up)",
        re.IGNORECASE,
    )
    matches = list(pattern.finditer(text))
    if len(matches) < 4:
        return False
    for i, m in enumerate(matches):
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        section_body = text[start:end]
        if not re.search(r"[\u0980-\u09FF]", section_body):
            return False
    return True

async def _enforce_output_language(text: str, lang_instruction: str) -> str:
    """
    Ensure language rule is respected. If Bangla is required, all four sections must be in Bangla script.
    If not, ask the model to rewrite in Bangla script while keeping structure.
    """
    output = (text or "").strip()
    if not _requires_bangla(lang_instruction):
        return output

    # If all four sections are in Bangla, keep it.
    if _all_sections_bangla(output):
        return output

    try:
        rewrite_prompt = [
            {"role": "system", "content": MEDICAL_SYSTEM_PROMPT},
            {"role": "user", "content": (
                "Rewrite the following response fully in Bangla (Bengali script only). "
                "Keep the same four-section structure and concise bullet points.\n\n"
                f"Response to rewrite:\n{output}"
            )},
        ]
        rewritten = (await get_llm_response(rewrite_prompt)).strip()
        if _all_sections_bangla(rewritten):
            return rewritten
    except Exception as exc:
        log.warning(f"Bangla rewrite enforcement failed: {exc}")

    return output


def _is_self_intro_response(text: str) -> bool:
    """Check if response is introducing itself (not health-related)."""
    text = (text or "").strip().lower()
    intro_markers = [
        "i am nirova",
        "i'm nirovaai",
        "primary-level health",
        "health assistant",
        "আমি nirova",
        "আমি nirovaai",
        "স্বাস্থ্য সহায়ক",
    ]
    return any(marker in text for marker in intro_markers)


def _ensure_structured_response(text: str) -> str:
    """Normalize model output into a predictable, scannable structure for HEALTH queries only."""
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

    # If this is a self-introduction or conversational response, return as-is (no structure)
    if _is_self_intro_response(cleaned):
        return cleaned

    # Normalize markdown/bold wrappers before heading detection.
    normalized = cleaned.replace("**", "").replace("__", "")
    heading_pattern = re.compile(
        r"(1\)\s*Summary|2\)\s*What\s*To\s*Do\s*Now|3\)\s*Red\s*Flags|4\)\s*Follow-?\s*Up)",
        re.IGNORECASE,
    )
    
    # Check if response has 3+ section headings (health-structured response)
    matches = list(heading_pattern.finditer(normalized))
    if len(matches) >= 3:
        return _sanitize_structured_sections(normalized)

    # If no structure detected, return as-is (conversational/natural response)
    return cleaned


def _sanitize_structured_sections(text: str) -> str:
    """Convert mixed markdown/plain output into a strict 4-section bullet format."""
    normalized = (text or "").replace("\r\n", "\n").replace("\r", "\n").strip()
    headings = ["1) Summary", "2) What To Do Now", "3) Red Flags", "4) Follow-Up"]
    pattern = re.compile(
        r"(1\)\s*Summary|2\)\s*What\s*To\s*Do\s*Now|3\)\s*Red\s*Flags|4\)\s*Follow-?\s*Up)",
        re.IGNORECASE,
    )
    matches = list(pattern.finditer(normalized))
    if not matches:
        return normalized

    blocks = []
    for i, m in enumerate(matches):
        raw_heading = m.group(1)
        heading = (
            "1) Summary" if raw_heading.lower().startswith("1)") else
            "2) What To Do Now" if raw_heading.lower().startswith("2)") else
            "3) Red Flags" if raw_heading.lower().startswith("3)") else
            "4) Follow-Up"
        )
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(normalized)
        raw_body = normalized[start:end].strip(" :-\n\t")

        body = raw_body.replace("•", "- ")
        body = re.sub(r"(?m)^\s*\*\s*", "- ", body)
        body = re.sub(r"\s+\*\s+", "\n- ", body)
        body = re.sub(r"(?m)^\s*-\s*", "- ", body)
        body = re.sub(r"\s{2,}", " ", body)
        body = re.sub(r"\n{2,}", "\n", body).strip()

        bullet_lines = [ln.strip() for ln in body.split("\n") if ln.strip()]
        bullet_lines = [ln if ln.startswith("- ") else f"- {ln}" for ln in bullet_lines]
        if not bullet_lines:
            bullet_lines = ["- Not enough details were provided."]
        bullet_lines = bullet_lines[:2]
        blocks.append(f"{heading}\n" + "\n".join(bullet_lines))

    by_heading = {b.split("\n", 1)[0]: b for b in blocks}
    final_blocks = []
    for h in headings:
        final_blocks.append(by_heading.get(h, f"{h}\n- Not enough details were provided."))
    return "\n".join(final_blocks)


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
    safe_question = _safe_question_text(_rewrite_language_switch_message(data.message))
    safe_mode = (data.agent_mode or "general").strip().lower()
    safe_language = (data.language or "en").strip().lower()  # NEW: Get explicit language preference
    is_conversational = _is_conversational_only(safe_question)  # NEW: Detect if purely conversational
    context_sig = await _context_fingerprint(current_user["_id"], safe_mode)
    
    # DEBUG: Log mode for debugging cache issues
    log.info(f"[Chat Ask] User: {str(current_user.get('_id', 'unknown'))[:8]}... | Mode: {safe_mode} | Q_len: {len(safe_question)}")

    # Scope cache per user and latest analysis context so stale replies are avoided.
    cache_payload = {
        "v": CACHE_SCHEMA_VERSION,
        "user_id": str(current_user["_id"]),
        "message": safe_question.lower(),
        "agent_mode": safe_mode,
        "context_sig": context_sig,
        "client_context": (data.client_context or "").strip()[:800],
    }
    cache_key = f"chat:{hashlib.sha256(json.dumps(cache_payload, sort_keys=True).encode()).hexdigest()[:24]}"
    cached = await cache_get(cache_key)

    if cached:
        # Still save to conversation history even if cached
        cached_session_id = await _save_message(
            user_id=current_user["_id"],
            user_message=safe_question,
            ai_response=cached["response"],  # CHANGED: Don't force structure for conversational
            session_id=data.session_id,
            agent_mode=safe_mode
        )
        return ChatResponse(
            response=cached["response"],  # CHANGED: Return as-is
            session_id=cached_session_id,
            sources=cached.get("sources", [])
        )

    async def _context_wrapper(question: str, mode: str):
        return await _get_medical_context(
            question,
            current_user["_id"],
            agent_mode=mode,
        )

    # Create format instruction factory that knows about conversational status
    def _get_format_instruction_for_query(mode: str = None) -> str:
        """Return appropriate format instruction based on query type."""
        if is_conversational:
            return _conversational_brief_instruction()
        else:
            return _response_format_instruction()

    # Create language instruction factory that knows about language preference
    def _get_language_instruction_for_query(mode: str = None) -> str:
        """Return language instruction based on user preference and message content."""
        return _language_instruction(safe_question, safe_language)
    
    deps = ChatGraphDeps(
        system_prompt=MEDICAL_SYSTEM_PROMPT,
        get_context=_context_wrapper,
        get_page_instruction=_agent_instruction,
        get_format_instruction=_get_format_instruction_for_query,
        get_language_instruction=_get_language_instruction_for_query,
        get_grounding_instruction=_grounding_instruction,
        llm_respond=get_llm_response,
        enforce_output_language=_enforce_output_language,
        ensure_structured_response=_ensure_structured_response,
        safe_context_text=_safe_context_text,
    )

    # Orchestrate chat generation with LangGraph (or sequential fallback).
    use_langgraph = (settings.CHAT_ORCHESTRATION_MODE or "langgraph").strip().lower() == "langgraph"
    graph_result = await run_langgraph_chat(
        {
            "question": safe_question,
            "mode": safe_mode,
            "client_context": data.client_context or "",
        },
        deps,
        enable_graph=use_langgraph,
    )
    response_text = graph_result.get("final_response") or ""
    sources = graph_result.get("sources") or []

    # Save conversation
    new_session_id = await _save_message(
        user_id=current_user["_id"],
        user_message=safe_question,
        ai_response=response_text,
        session_id=data.session_id,
        agent_mode=safe_mode
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

@router.get("/history")
async def get_chat_history(
    skip: int = Query(default=0, ge=0, description="Number of records to skip"),
    limit: int = Query(default=15, ge=1, le=50, description="Records per page (max 50)"),
    agent_mode: str = Query(default="general"),
    current_user: dict = Depends(get_current_user)
):
    '''
    Retrieve the user's previous chat sessions with pagination.
    
    Query Parameters:
    - skip: Number of sessions to skip (default 0)
    - limit: Sessions per page (default 15, max 50)
    - agent_mode: Filter by agent mode (default "general")
    '''
    try:
        mode = (agent_mode or "general").strip().lower()
        
        # Get total count
        total_count = await chat_sessions().count_documents({
            "user_id": current_user["_id"],
            "agent_mode": mode
        })
        
        # Get paginated sessions
        sessions = []
        cursor = chat_sessions().find({
            "user_id": current_user["_id"],
            "agent_mode": mode
        }).sort("created_at", -1).skip(skip).limit(limit)
        
        async for doc in cursor:
            sessions.append({
                "session_id": str(doc["_id"]),
                "messages": doc.get("messages", [])[:100],  # Limit to last 100 messages
                "agent_mode": doc.get("agent_mode", "general"),
                "updated_at": (doc.get("updated_at") or doc.get("created_at", datetime.now(timezone.utc))).isoformat()
            })
        
        return {
            "total": total_count,
            "returned": len(sessions),
            "skip": skip,
            "limit": limit,
            "hasMore": skip + len(sessions) < total_count,
            "sessions": sessions
        }
    except Exception as e:
        log.error(f"Error fetching chat history: {e}")
        return {
            "error": True,
            "message": "Unable to fetch chat history",
            "sessions": []
        }


@router.get("/context-preview", response_model=ContextPreviewResponse)
async def get_context_preview(
    agent_mode: str = Query(default="general"),
    current_user: dict = Depends(get_current_user),
):
    """Return latest analysis summary used as chat context for a page agent."""
    mode = (agent_mode or "general").strip().lower()
    user_id = current_user["_id"]

    try:
        vision_scope, symptom_scope, allow_pooling = _mode_scoped_filters(mode)
        
        # For specialized modes: ONLY get their specific context, NEVER pool
        if not allow_pooling:
            # Try vision analysis first (for skin, lab, prescription)
            if vision_scope:
                vision_filter = {"user_id": user_id, **vision_scope}
                doc = await vision_analyses().find_one(
                    vision_filter,
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
            
            # Try symptom analysis (for symptoms, dengue)
            if symptom_scope:
                symptom_filter = {"user_id": user_id, **symptom_scope}
                symptom_doc = await symptom_analyses().find_one(
                    symptom_filter,
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
            
            # Specialized mode but no data found
            return ContextPreviewResponse(
                agent_mode=mode,
                label="Context Status",
                summary="No recent analysis found yet. Chat will use your message and medical guidance baseline.",
                updated_at=None,
            )
        
        # For overview modes: CAN pool context from all sources
        # (dashboard, chat, timeline, general)
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


@router.post("/clear-session")
async def clear_chat_session(current_user: dict = Depends(get_current_user)):
    """
    Clear all chat sessions and cached context for the current user.
    Called on logout to destroy all session data.
    """
    try:
        # Delete all chat sessions for this user
        result = await chat_sessions().delete_many({
            "user_id": current_user["_id"]
        })
        deleted_sessions = result.deleted_count
        
        log.info(f"Cleared {deleted_sessions} chat sessions for user {current_user['_id']}")
        
        return {
            "status": "success",
            "message": f"Cleared {deleted_sessions} chat session(s)",
            "sessions_deleted": deleted_sessions
        }
    except Exception as e:
        log.error(f"Error clearing sessions: {e}")
        return {
            "status": "error",
            "message": "Unable to clear sessions",
        }


@router.post("/clear-context")
async def clear_page_context(
    agent_mode: str = Query(default="general"),
    current_user: dict = Depends(get_current_user)
):
    """
    Clear cached analysis context for a specific agent mode.
    This doesn't affect chat history, only the context cache.
    """
    try:
        mode = (agent_mode or "general").strip().lower()
        # Note: Context is cached on frontend with localStorage, 
        # this endpoint is for logging the action server-side
        log.info(f"Context cleared for mode '{mode}' by user {current_user['_id']}")
        
        return {
            "status": "success",
            "message": f"Context cleared for {mode} mode",
            "cleared_mode": mode
        }
    except Exception as e:
        log.error(f"Error clearing context: {e}")
        return {
            "status": "error",
            "message": "Unable to clear context",
        }


@router.post("/logout-cleanup")
async def logout_cleanup(current_user: dict = Depends(get_current_user)):
    """
    Complete session cleanup on logout: clears all chat sessions and analysis cache.
    Frontend should call this, then clear localStorage cache.
    """
    try:
        # Delete all chat sessions
        session_result = await chat_sessions().delete_many({
            "user_id": current_user["_id"]
        })
        
        log.info(
            f"Logout cleanup for user {current_user['_id']}: "
            f"deleted {session_result.deleted_count} sessions"
        )
        
        return {
            "status": "success",
            "message": "Session cleanup complete",
            "sessions_deleted": session_result.deleted_count,
            "frontend_action": "Clear all localStorage caches"
        }
    except Exception as e:
        log.error(f"Error during logout cleanup: {e}")
        return {
            "status": "error",
            "message": "Logout cleanup failed",
        }


@router.websocket("/ws")
async def websocket_chat(websocket: WebSocket):
    """
    WebSocket endpoint for real-time streaming chat with medical safety.
    Includes timeout handling and graceful fallback for provider failures.
    """
    token = websocket.cookies.get(settings.AUTH_COOKIE_NAME)
    if not token:
        await websocket.close(code=1008, reason="No authentication token")
        return

    user_id = await _authenticate_websocket(websocket, token)
    if not user_id:
        return

    await websocket.accept()

    try:
        while True:
            await _handle_websocket_message(websocket, user_id)
    except WebSocketDisconnect:
        log.info("WebSocket client disconnected normally")
    except Exception as e:
        log.error(f"WebSocket error: {e}", exc_info=True)
        try:
            await websocket.send_json({
                "type": "error",
                "content": "Connection error. Please refresh and try again."
            })
        except Exception:
            pass  # Connection already closed


async def _authenticate_websocket(websocket: WebSocket, token: str) -> Optional[str]:
    """Authenticate WebSocket connection."""
    try:
        from app.core.auth import decode_token
        payload = decode_token(token)
        return payload.get("sub")
    except Exception as e:
        log.warning(f"WebSocket authentication failed: {e}")
        try:
            await websocket.close(code=1008, reason="Authentication failed")
        except Exception:
            pass
        return None


async def _handle_websocket_message(websocket: WebSocket, user_id: str):
    """Handle a single WebSocket message with timeout and error recovery."""
    try:
        # Receive message with timeout
        raw = await asyncio.wait_for(
            websocket.receive_text(),
            timeout=WEBSOCKET_TIMEOUT_SECONDS
        )
    except asyncio.TimeoutError:
        log.warning(f"WebSocket message timeout for user {user_id}")
        try:
            await websocket.send_json({
                "type": "error",
                "content": "Request timeout. Please try again."
            })
        except Exception:
            pass
        return
    except WebSocketDisconnect:
        raise
    except Exception as e:
        log.error(f"WebSocket receive error: {e}")
        return

    # Enforce maximum WebSocket message size (16 KB) — check BEFORE parsing
    if len(raw) > 16384:
        try:
            await websocket.send_json({
                "type": "error",
                "content": "Message too large. Please shorten your question."
            })
        except Exception:
            pass
        return

    # Parse message
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        try:
            await websocket.send_json({
                "type": "error",
                "content": "Invalid message format"
            })
        except Exception:
            pass
        return

    # Validate inputs
    message = _safe_question_text(_rewrite_language_switch_message(data.get("message", "")))
    if not message:
        try:
            await websocket.send_json({
                "type": "error",
                "content": "Message cannot be empty"
            })
        except Exception:
            pass
        return

    session_id = str(data.get("session_id", ""))
    agent_mode = str(data.get("agent_mode", "chat")).lower()
    client_context = _safe_context_text((data.get("client_context") or "").strip())
    language = str(data.get("language", "en")).lower()  # NEW: Get language from websocket data

    # Validate agent mode
    valid_modes = [
        "general", "dashboard", "symptoms", "skin",
        "dengue", "lab", "prescription", "timeline", "chat"
    ]
    if agent_mode not in valid_modes:
        agent_mode = "chat"

    # Get medical context
    try:
        context, sources, has_external_evidence = await asyncio.wait_for(
            _get_medical_context(
                message,
                ObjectId(user_id),
                agent_mode=agent_mode,
            ),
            timeout=15  # Medical context retrieval timeout
        )
        safe_context = _safe_context_text(context)
    except asyncio.TimeoutError:
        log.warning(f"Medical context retrieval timeout for user {user_id}")
        safe_context = ""
        sources = []
        has_external_evidence = False
    except Exception as e:
        log.error(f"Medical context retrieval error: {e}")
        safe_context = ""
        sources = []
        has_external_evidence = False

    # Build prompts
    is_conversational = _is_conversational_only(message)  # NEW: Detect if conversational
    page_instruction = _agent_instruction(agent_mode)
    
    # Only include format instruction for health queries, not conversational ones
    if is_conversational:
        format_instruction = _conversational_brief_instruction()
    else:
        format_instruction = _response_format_instruction()
    
    lang_instruction = _language_instruction(message, language)  # UPDATED: Pass language preference
    grounding_instruction = _grounding_instruction(has_external_evidence)

    messages = [
        {"role": "system", "content": MEDICAL_SYSTEM_PROMPT},
        {"role": "user", "content": f"""Medical Context:
{safe_context}

Immediate Page Context (latest analysis):
{client_context or "None provided"}

Patient Question: {message}

Assistant Focus: {page_instruction}

{format_instruction}

Language Rule: {lang_instruction}

{grounding_instruction}"""}
    ]

    # Stream response with timeout and error handling
    full_response = ""
    try:
        await websocket.send_json({"type": "start"})
    except Exception as e:
        log.error(f"Failed to send start message: {e}")
        return

    try:
        # Wrap the whole generation loop with a timeout (Python 3.11+) or rely on LLM client timeouts.
        # We must not pass an async generator to wait_for.
        async for token_text in stream_llm_response(messages):
            full_response += token_text
            try:
                await websocket.send_json({
                    "type": "token",
                    "content": token_text
                })
            except WebSocketDisconnect:
                raise
            except Exception as e:
                log.warning(f"Failed to send token: {e}")
                break

    except asyncio.TimeoutError:
        log.warning(f"LLM response timeout for user {user_id}")
        timeout_msg = " [Response generation timed out. Please try again.]"
        try:
            await websocket.send_json({
                "type": "token",
                "content": timeout_msg
            })
        except Exception:
            pass
        full_response += timeout_msg

    except Exception as e:
        log.error(f"Streaming error: {e}", exc_info=True)
        # Send safe fallback message
        fallback = (
            "I'm temporarily unable to process your request. "
            "Please try again in a moment, or consult a healthcare provider for urgent concerns."
        )
        try:
            await websocket.send_json({
                "type": "token",
                "content": fallback
            })
        except Exception:
            pass
        full_response = fallback

    # Send completion
    try:
        await websocket.send_json({"type": "end"})
    except Exception as e:
        log.warning(f"Failed to send end message: {e}")

    # Save to history (async, don't block connection)
    try:
        if full_response and session_id:
            await chat_sessions().insert_one({
                "user_id": ObjectId(user_id),
                "session_id": session_id,
                "message": message,
                "response": full_response,
                "sources": sources,
                "agent_mode": agent_mode,
                "created_at": datetime.now(timezone.utc),
            })
    except Exception as e:
        log.warning(f"Failed to save chat history: {e}")

    # Save to MongoDB
    is_conversational = _is_conversational_only(message)  # NEW: Detect conversational query
    if is_conversational:
        # For conversational queries, don't force structure - just enforce language
        formatted_response = await _enforce_output_language(full_response, lang_instruction)
    else:
        # For health queries, apply full structure and language enforcement
        formatted_response = _ensure_structured_response(
            await _enforce_output_language(full_response, lang_instruction)
        )
    new_session_id = await _save_message(
        user_id=ObjectId(user_id),
        user_message=message,
        ai_response=formatted_response,
        session_id=session_id,
        agent_mode=agent_mode
    )

    # Signal completion
    await websocket.send_json({
        "type": "done",
        "session_id": new_session_id,
        "sources": sources,
        "formatted_response": formatted_response,
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


def _mode_scoped_filters(agent_mode: str) -> tuple[dict, dict, bool]:
    """
    Return (vision_filter, symptom_filter, allow_pooling) for mode-aware context retrieval.
    
    CRITICAL: Specialized pages (skin, lab, dengue, symptoms, prescription) MUST NEVER
    share context with other pages. Only overview pages (dashboard, chat, timeline) can pool.
    """
    mode = (agent_mode or "general").strip().lower()
    vision_filter = {}
    symptom_filter = {}
    allow_pooling = False  # STRICT DEFAULT: no pooling for specialized pages

    # SPECIALIZED pages: ONLY their own data, NEVER pooled
    if mode == "skin":
        vision_filter["analysis_type"] = "skin"
    elif mode == "lab":
        vision_filter["analysis_type"] = "lab"
    elif mode == "prescription":
        vision_filter["analysis_type"] = "prescription"
    elif mode == "dengue":
        symptom_filter["analysis_mode"] = "dengue_only"
    elif mode == "symptoms":
        symptom_filter["analysis_mode"] = {"$in": ["log", "predict"]}
    # OVERVIEW modes: CAN pool context from multiple sources
    elif mode in {"dashboard", "timeline", "chat", "general"}:
        allow_pooling = True

    return vision_filter, symptom_filter, allow_pooling


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
) -> tuple[str, list[str], bool]:
    """
    Search MongoDB knowledge base for relevant medical information.
    Falls back to a generic message if nothing found.
    """
    try:
        mode = (agent_mode or "general").strip().lower()
        log.info(f"[Context Retrieval] mode={mode} user={user_id} query={query[:50]}...")
        
        chunks = []
        sources = []
        has_external_evidence = False

        kb_docs, has_external_evidence = await retrieve_knowledge(
            query,
            top_k=max(1, int(settings.RAG_TOP_K)),
            candidate_limit=max(10, int(settings.RAG_CANDIDATE_LIMIT)),
        )
        if kb_docs:
            chunks.append(
                "Retrieved Bangladesh medical references:\n"
                + build_knowledge_context(kb_docs, max_chars=max(800, int(settings.RAG_KB_MAX_CHARS)))
            )
            for doc in kb_docs:
                src = doc.get("source") or "Medical Reference"
                if src not in sources:
                    sources.append(src)

        if user_id:
            user_insights = []
            mode = (agent_mode or "general").strip().lower()
            vision_scope, symptom_scope, _allow_pooling = _mode_scoped_filters(mode)
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

        return context, sources, has_external_evidence

    except Exception as e:
        log.warning(f"Knowledge search failed: {e}")
        return "Please provide general health guidance.", [], False


async def _save_message(
    user_id,
    user_message: str,
    ai_response: str,
    session_id: Optional[str] = None,
    agent_mode: str = "general",
) -> str:
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
                        "$set": {
                            "updated_at": datetime.now(timezone.utc),
                            "agent_mode": (agent_mode or "general").strip().lower(),
                        }
                    }
                )
                if update_result.matched_count > 0:
                    return session_id
                log.warning(f"Session {session_id} not found for user; creating a new session.")
            except (InvalidId, TypeError):
                log.warning(f"Invalid session_id provided: {session_id}; creating a new session.")

        result = await chat_sessions().insert_one({
            "user_id": user_obj_id,
            "agent_mode": (agent_mode or "general").strip().lower(),
            "messages": new_messages,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        })
        return str(result.inserted_id)

    except Exception as e:
        log.warning(f"Could not save chat session: {e}")
        return "unsaved"
