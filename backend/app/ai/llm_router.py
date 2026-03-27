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
    if isinstance(text, str) and text.strip():
        return text.strip()
    return _rule_based_response([])


def _rule_based_response(messages: list) -> str:
    last_message = ""
    for msg in reversed(messages):
        if msg.get("role") == "user":
            last_message = str(msg.get("content", "")).lower()
            break

    if any(word in last_message for word in ["dengue", "fever", "bone pain", "jor"]):
        return (
            "1) Summary\n"
            "- Your symptoms may be consistent with dengue or another viral illness.\n"
            "2) What To Do Now\n"
            "- Rest, hydrate with ORS/water, and use paracetamol if needed.\n"
            "3) Red Flags\n"
            "- Go urgently if bleeding, severe abdominal pain, vomiting, or breathing difficulty occurs.\n"
            "4) Follow-Up\n"
            "- Arrange NS1/CBC testing and in-person review as soon as possible."
        )

    return (
        "1) Summary\n"
        "- I can provide first-level guidance from the information shared.\n"
        "2) What To Do Now\n"
        "- Monitor symptoms, rest, and maintain hydration.\n"
        "3) Red Flags\n"
        "- Seek urgent care for breathing trouble, severe pain, confusion, or bleeding.\n"
        "4) Follow-Up\n"
        "- If symptoms persist or worsen over 24-48 hours, consult a clinician."
    )
