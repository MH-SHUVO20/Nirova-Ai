# Skin disease analysis using Gemini Vision API

import json
import logging

log = logging.getLogger(__name__)


def load_skin_model():
    pass


async def analyze_skin_image(image_bytes: bytes) -> dict:
    """Analyze skin condition from image using Gemini Vision"""
    return await _gemini_vision(image_bytes)


async def _gemini_vision(image_bytes: bytes) -> dict:
    """Analyze skin condition using Gemini Vision API"""
    import google.generativeai as genai
    import base64
    from app.core.config import settings

    try:
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
        for model_name in model_candidates:
            try:
                model = genai.GenerativeModel(model_name)
                response = model.generate_content([
                    {"mime_type": "image/jpeg", "data": img_b64},
                    prompt
                ])
                model_used = model_name
                break
            except Exception as e:
                import logging
                logging.getLogger(__name__).warning(f"Skin model analysis failed: {e}")
                last_error = e

        if response is None:
            raise RuntimeError(f"All Gemini model candidates failed: {last_error}")

        text = response.text.strip()
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0]
        elif "```" in text:
            text = text.split("```")[1].split("```")[0]

        result = json.loads(text.strip())
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

