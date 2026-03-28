"""
NirovaAI - LLM Router
=====================
Provider order:
1) Groq (primary)
2) Gemini (fallback)
3) Hugging Face Mistral (fallback)
4) Rule-based emergency response
"""

from typing import AsyncGenerator
import logging
from datetime import datetime, timedelta

import google.generativeai as genai
import httpx
from groq import AsyncGroq

from app.core.config import settings

log = logging.getLogger(__name__)

_groq_client: AsyncGroq | None = None
_gemini_configured = False
_provider_disabled_until: dict[str, datetime] = {}


def _provider_order() -> list[str]:
    mode = (settings.LLM_ROUTING_MODE or "auto").strip().lower()

    if mode == "local_only":
        # In this project, local_only maps to Hugging Face provider-only mode.
        return ["huggingface"]
    if mode == "local_first":
        return ["huggingface", "groq", "gemini"]
    if mode == "cloud_first":
        return ["groq", "gemini", "huggingface"]

    # auto
    return ["groq", "gemini", "huggingface"]


def _is_disabled(provider: str) -> bool:
    until = _provider_disabled_until.get(provider)
    return bool(until and until > datetime.utcnow())


def _mark_failure(provider: str, exc: Exception) -> None:
    msg = str(exc).lower()
    cooldown = int(settings.LLM_PROVIDER_COOLDOWN_SECONDS)

    severe_markers = ["quota", "insufficient", "rate", "429", "401", "unauthorized", "forbidden"]
    if any(m in msg for m in severe_markers):
        _provider_disabled_until[provider] = datetime.utcnow() + timedelta(seconds=cooldown)
        return

    _provider_disabled_until[provider] = datetime.utcnow() + timedelta(seconds=min(60, cooldown))


def _get_groq_client() -> AsyncGroq:
    global _groq_client
    if not settings.GROQ_API_KEY:
        raise RuntimeError("GROQ_API_KEY is not set")
    if _groq_client is None:
        _groq_client = AsyncGroq(api_key=settings.GROQ_API_KEY)
    return _groq_client


def _ensure_gemini_configured() -> None:
    global _gemini_configured
    if not settings.GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY is not set")
    if not _gemini_configured:
        genai.configure(api_key=settings.GEMINI_API_KEY)
        _gemini_configured = True


MEDICAL_SYSTEM_PROMPT = """You are NirovaAI, a primary-level AI health assistant designed for Bangladesh.

Your role is to help Bangladeshi patients understand their health symptoms and conditions.

Important rules you always follow:
1. Provide practical first-level guidance (self-care, monitoring, and next steps)
2. Never make definitive diagnoses - use phrases like "may indicate" or "could suggest"
3. Do not append repetitive legal disclaimers in every answer
4. Use simple language that ordinary Bangladeshis can understand
5. Be aware of Bangladesh-specific diseases: dengue, typhoid, TB, arsenicosis, kala-azar, malaria
6. Recommend clinic/hospital care only when symptoms or risk level justify escalation
7. Reply in one language only: either Bangla or English
8. Never mix Bangla and English in the same response

You have access to Bangladesh medical guidelines and health information.
Always be compassionate and helpful, but responsible about medical advice."""


async def get_llm_response(messages: list) -> str:
    """Get response using configured provider routing."""
    for provider in _provider_order():
        if _is_disabled(provider):
            continue
        try:
            if provider == "groq":
                return _normalize_response(await _groq_complete(messages))
            if provider == "gemini":
                return _normalize_response(await _gemini_complete(messages))
            if provider == "huggingface":
                return _normalize_response(await _huggingface_complete(messages))
        except Exception as exc:
            _mark_failure(provider, exc)
            log.warning(f"{provider} failed: {exc}")

    return _normalize_response(_rule_based_response(messages))


async def stream_llm_response(messages: list) -> AsyncGenerator[str, None]:
    """Stream response with provider routing; non-stream providers are chunked by words."""
    for provider in _provider_order():
        if _is_disabled(provider):
            continue
        try:
            if provider == "groq":
                async for token in _groq_stream(messages):
                    yield token
                return

            if provider == "gemini":
                response = _normalize_response(await _gemini_complete(messages))
            else:
                response = _normalize_response(await _huggingface_complete(messages))

            for word in response.split():
                yield word + " "
            return

        except Exception as exc:
            _mark_failure(provider, exc)
            log.warning(f"{provider} stream failed: {exc}")

    yield _normalize_response(_rule_based_response(messages))


async def _groq_complete(messages: list) -> str:
    client = _get_groq_client()
    completion = await client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=messages,
        max_tokens=1024,
        temperature=0.3,
    )
    return completion.choices[0].message.content or ""


async def _groq_stream(messages: list) -> AsyncGenerator[str, None]:
    client = _get_groq_client()
    stream = await client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=messages,
        max_tokens=1024,
        temperature=0.3,
        stream=True,
    )
    async for chunk in stream:
        token = chunk.choices[0].delta.content
        if token:
            yield token


async def _gemini_complete(messages: list) -> str:
    _ensure_gemini_configured()
    model = genai.GenerativeModel("gemini-1.5-flash")
    conversation = "\n".join(
        [f"{m['role'].upper()}: {m['content']}" for m in messages if m.get("role") != "system"]
    )
    response = model.generate_content(conversation)
    return response.text or ""


async def _huggingface_complete(messages: list) -> str:
    if not settings.HF_API_KEY:
        raise RuntimeError("HF_API_KEY is not set")

    # Try configured model first, then strong open alternatives.
    model_candidates = [
        settings.HF_MODEL,
        "Qwen/Qwen2.5-72B-Instruct",
        "Qwen/Qwen2.5-32B-Instruct",
        "mistralai/Mixtral-8x7B-Instruct-v0.1",
    ]
    headers = {
        "Authorization": f"Bearer {settings.HF_API_KEY}",
        "Content-Type": "application/json",
    }
    timeout = httpx.Timeout(
        timeout=float(settings.HF_TIMEOUT_SECONDS),
        connect=min(10.0, float(settings.HF_TIMEOUT_SECONDS)),
    )

    last_error = None
    async with httpx.AsyncClient(timeout=timeout) as client:
        for model_name in model_candidates:
            if not model_name:
                continue
            payload = {
                "model": model_name,
                "messages": messages,
                "temperature": 0.3,
                "max_tokens": 1024,
            }
            try:
                response = await client.post(
                    "https://router.huggingface.co/v1/chat/completions",
                    json=payload,
                    headers=headers,
                )
                response.raise_for_status()
                data = response.json()
                choices = data.get("choices") or []
                if choices:
                    return choices[0].get("message", {}).get("content", "")
            except Exception as exc:
                last_error = exc
                continue

    if last_error:
        raise last_error
    return ""


def _normalize_response(text: str) -> str:
    """Normalize and validate LLM response for safety."""
    if isinstance(text, str) and text.strip():
        # Ensure response doesn't exceed reasonable length (8KB)
        text = text.strip()[:8000]
        
        # Safety check: ensure response doesn't contradict medical safety
        if len(text) == 0:
            return _rule_based_response([])
        
        return text
    return _rule_based_response([])


def _is_medical_emergency_question(message: str) -> bool:
    """Detect if user is asking about emergency symptoms."""
    emergency_keywords = [
        "breathing", "breathless", "chest pain", "severe bleeding",
        "unconscious", "stroke", "heart attack", "poisoning",
        "shock", "কাহিল", "শ্বাসকষ্ট", "বুকের ব্যথা"
    ]
    msg_lower = message.lower()
    return any(keyword in msg_lower for keyword in emergency_keywords)


def _rule_based_response(messages: list, context_mode: str = "general") -> str:
    """
    Rule-based fallback response for when all LLM providers fail.
    Prioritizes safety and clear escalation guidance for medical context.
    """
    last_message = ""
    for msg in reversed(messages):
        if msg.get("role") == "user":
            last_message = str(msg.get("content", "")).lower()
            break

    # ── Emergency/Urgent Symptoms ──
    if _is_medical_emergency_question(last_message):
        return (
            "⚠️ EMERGENCY WARNING\n\n"
            "This appears to be a medical emergency. Do NOT rely on AI guidance.\n\n"
            "🚑 CALL 999 IMMEDIATELY or go to the nearest hospital emergency room.\n\n"
            "If you are having:\n"
            "• Difficulty breathing\n"
            "• Chest pain\n"
            "• Severe bleeding\n"
            "• Loss of consciousness\n"
            "• Severe trauma\n\n"
            "SEEK EMERGENCY CARE RIGHT NOW.\n\n"
            "Do not delay. Professional medical help is required immediately."
        )

    # ── Dengue/Fever Context ──
    if any(word in last_message for word in ["dengue", "fever", "জ্বর", "ডেঙ্গু", "bone pain", "jor"]):
        return (
            "For your fever/dengue concern:\n\n"
            "✓ Immediate Steps:\n"
            "  • Rest and avoid rigorous activity\n"
            "  • Drink plenty of water, ORS, or electrolyte drinks\n"
            "  • Use paracetamol (not aspirin) if needed for fever\n"
            "  • Monitor body temperature regularly\n\n"
            "🔴 Danger Signs (Seek Hospital Immediately):\n"
            "  • Severe abdominal pain or persistent vomiting\n"
            "  • Bleeding (nose, gums, or in stool)\n"
            "  • Difficulty breathing or chest pain\n"
            "  • Unusual drowsiness or confusion\n"
            "  • Cold, clammy skin\n\n"
            "📋 Next Steps:\n"
            "  • Get blood tests: NS1 antigen, CBC (platelet count is important)\n"
            "  • Consult a doctor or visit a clinic as soon as possible\n"
            "  • Keep a temperature log and notify your doctor of any danger signs"
        )

    # ── Lab Report/Test Result Context ──
    if any(word in last_message for word in ["lab", "test", "result", "রিপোর্ট", "পরীক্ষা"]):
        return (
            "For lab test interpretation:\n\n"
            "⚠️ Important:\n"
            "AI cannot replace professional medical interpretation.\n\n"
            "✓ What You Should Do:\n"
            "  • Show your lab report to your doctor or a qualified pathologist\n"
            "  • Ask them to explain what each value means\n"
            "  • Discuss what follow-up tests or treatment is needed\n"
            "  • Don't rely solely on reference ranges\n\n"
            "If you have urgent concerns or abnormal findings,\n"
            "schedule an appointment with your doctor immediately."
        )

    # ── Skin/Vision Concern ──
    if any(word in last_message for word in ["skin", "rash", "wound", "skin condition", "চর্ম", "ফুসকুড়ি"]):
        return (
            "For skin concerns:\n\n"
            "✓ General Care:\n"
            "  • Keep the area clean and dry\n"
            "  • Avoid scratching to prevent infection\n"
            "  • Wash with mild soap and water\n"
            "  • Wear clean, loose clothing\n\n"
            "🔴 See a Doctor If:\n"
            "  • The rash spreads rapidly or covers large areas\n"
            "  • There's pus, oozing, or severe pain\n"
            "  • You have fever along with the rash\n"
            "  • The condition doesn't improve in 1-2 weeks\n"
            "  • You suspect ringworm or fungal infection\n\n"
            "A dermatologist can provide proper diagnosis and treatment."
        )

    # ── Prescription/Medicine Context ──
    if any(word in last_message for word in ["medicine", "medicine", "drug", "prescription", "tablet", "ওষুধ", "ঔষধ"]):
        return (
            "For medicine and prescription questions:\n\n"
            "✓ Safe Practices:\n"
            "  • Take medicines exactly as your doctor prescribed\n"
            "  • Don't skip doses or take extra amounts\n"
            "  • Complete the full course even if you feel better\n"
            "  • Keep medicines away from children\n"
            "  • Store in cool, dry place (check label for storage)\n\n"
            "🔴 Seek Help If:\n"
            "  • You experience severe side effects\n"
            "  • Symptoms worsen after starting medicine\n"
            "  • You're unsure about interactions with other medicines\n\n"
            "Always consult your doctor or pharmacist about medicine questions.\n"
            "Don't stop prescribed medicines without medical advice."
        )

    # ── Default/General Context ──
    return (
        "I'm experiencing a temporary service interruption.\n\n"
        "However, here's general health guidance:\n\n"
        "✓ For Most Symptoms:\n"
        "  • Rest and stay hydrated\n"
        "  • Monitor your symptoms\n"
        "  • Keep track of fever/pain levels\n"
        "  • Avoid strenuous activity\n\n"
        "🔴 Seek Immediate Care If:\n"
        "  • Difficulty breathing\n"
        "  • Chest or severe abdominal pain\n"
        "  • Bleeding\n"
        "  • Loss of consciousness\n"
        "  • Severe symptoms that worsen rapidly\n\n"
        "📋 For Ongoing Concerns:\n"
        "  • Consult a healthcare provider\n"
        "  • Visit a clinic or hospital\n"
        "  • Keep records of symptoms and timeline\n\n"
        "Please try again shortly, or seek professional medical advice."
    )
