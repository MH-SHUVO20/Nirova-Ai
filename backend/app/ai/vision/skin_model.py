# Skin disease analysis using Gemini Vision API

import json
import logging
import re

log = logging.getLogger(__name__)


def load_skin_model():
    pass


async def analyze_skin_image(image_bytes: bytes, mime_type: str | None = None) -> dict:
    """Analyze skin condition from image using Gemini Vision"""
    return await _gemini_vision(image_bytes, mime_type or "image/jpeg")


def _normalize_image_mime_type(mime_type: str | None) -> str:
    if not mime_type:
        return "image/jpeg"
    lowered = mime_type.strip().lower()
    if lowered == "image/jpg":
        return "image/jpeg"
    if lowered.startswith("image/"):
        return lowered
    return "image/jpeg"


def _extract_json_payload(text: str) -> dict:
    cleaned = (text or "").strip()
    if "```json" in cleaned:
        cleaned = cleaned.split("```json", 1)[1].split("```", 1)[0]
    elif "```" in cleaned:
        cleaned = cleaned.split("```", 1)[1].split("```", 1)[0]

    try:
        return json.loads(cleaned.strip())
    except Exception:
        # Fallback: extract the first JSON object from mixed model text.
        match = re.search(r"\{[\s\S]*\}", cleaned)
        if not match:
            raise
        return json.loads(match.group(0))


async def _gemini_vision(image_bytes: bytes, mime_type: str = "image/jpeg") -> dict:
    """Analyze skin condition using Gemini Vision API"""
    import google.generativeai as genai
    import base64
    from app.core.config import settings

    try:
        if not settings.GEMINI_API_KEY:
            raise RuntimeError("GEMINI_API_KEY is not configured")

        genai.configure(api_key=settings.GEMINI_API_KEY)
        model_candidates = [
            "gemini-flash-latest",
            "gemini-flash-lite-latest",
            "gemini-2.0-flash",
            "gemini-2.0-flash-lite",
            "gemini-1.5-flash-latest",
            "gemini-1.5-flash",
        ]

        img_b64 = base64.b64encode(image_bytes).decode()

        prompt = """You are a medical AI assistant helping patients in Bangladesh identify skin conditions.

Analyze this skin image and respond with ONLY a JSON object (no other text):
{
  "condition": "name of most likely skin condition",
  "confidence": "high/medium/low",
  "severity": "mild/moderate/severe",
  "description": "brief description in simple English",
  "common_in_bangladesh": true/false,
  "home_care": "simple home care advice if mild",
  "recommended_action": "see_doctor/urgent_care/home_care",
  "disclaimer": "This is AI analysis only — please consult a doctor for proper diagnosis"
}

Common skin conditions in Bangladesh include: ringworm, eczema, psoriasis, acne,
skin infections, dengue rash, chickenpox, and fungal infections."""

        last_error = None
        response = None
        model_used = None
        safe_mime_type = _normalize_image_mime_type(mime_type)
        for model_name in model_candidates:
            try:
                model = genai.GenerativeModel(model_name)
                response = model.generate_content([
                    {"mime_type": safe_mime_type, "data": img_b64},
                    prompt
                ], request_options={"timeout": 30})
                if not response or not getattr(response, "text", None):
                    raise RuntimeError("Empty model response")
                model_used = model_name
                break
            except Exception as e:
                log.warning(f"Skin model analysis failed ({model_name}): {e}")
                last_error = e

        if response is None:
            raise RuntimeError(f"All Gemini model candidates failed: {last_error}")

        result = _extract_json_payload(response.text)
        result["analyzer"] = f"Gemini Vision ({model_used})"
        return result

    except Exception as e:
        log.error(f"Gemini Vision analysis failed: {e}")
        return {
            "condition": "Unable to analyze",
            "confidence": "low",
            "severity": "unknown",
            "description": "Image analysis is temporarily unavailable",
            "recommended_action": "see_doctor",
            "analyzer": "unavailable",
            "error": str(e),
            "disclaimer": "Please consult a doctor for proper diagnosis — "
                         "এই সেবা কেবল তথ্যগত সহায়তা দেয়; এটি নিবন্ধিত চিকিৎসকের পরামর্শ, রোগ নির্ণয় বা চিকিৎসার বিকল্প নয়।"
        }



def _estimate_severity(condition: str) -> str:
    """Best-effort severity guidance without calling external APIs."""
    c = (condition or "").strip().lower()

    urgent_keywords = ["melanoma", "necrosis", "severe", "ulcer", "bleeding", "spreading", "cellulitis"]
    if any(k in c for k in urgent_keywords):
        return "severe — seek urgent in-person medical care"

    moderate_keywords = ["psoriasis", "eczema", "dermatitis", "shingles", "chickenpox"]
    if any(k in c for k in moderate_keywords):
        return "moderate — see a doctor soon (same week)"

    mild_keywords = ["acne", "ringworm", "tinea", "fungal", "heat rash"]
    if any(k in c for k in mild_keywords):
        return "mild — home care may help; see a doctor if not improving"

    return "unknown — if painful, spreading, or with fever, seek medical care"

