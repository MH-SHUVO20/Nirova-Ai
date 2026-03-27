"""Vision API - image analysis endpoints"""

from datetime import datetime
import base64
import json
import logging

import fitz
import google.generativeai as genai
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from app.ai.vision.skin_model import analyze_skin_image
from app.core.auth import get_current_user
from app.core.config import settings
from app.core.database import vision_analyses

router = APIRouter(prefix="/vision", tags=["Vision AI"])
log = logging.getLogger(__name__)

MAX_FILE_SIZE = 10 * 1024 * 1024


async def _store_analysis(
    *,
    current_user: dict,
    analysis_type: str,
    file: UploadFile,
    file_size: int,
    analysis: dict,
    source_type: str,
) -> tuple[bool, str | None]:
    """Persist analysis output for user history and downstream chat context."""
    try:
        result = await vision_analyses().insert_one(
            {
                "user_id": current_user["_id"],
                "analysis_type": analysis_type,
                "filename": file.filename,
                "content_type": file.content_type,
                "source_type": source_type,
                "file_size": file_size,
                "analysis": analysis,
                "created_at": datetime.utcnow(),
            }
        )
        return True, str(result.inserted_id)
    except Exception as exc:
        # Do not fail primary API response on persistence issues.
        log.warning(f"Could not save {analysis_type} analysis to MongoDB: {exc}")
        return False, None


def _prepare_gemini_input(file_bytes: bytes, content_type: str) -> tuple[str, str]:
    """Convert file to Gemini-compatible format (PDF page rendered as JPEG)."""
    if content_type == "application/pdf":
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        if len(doc) == 0:
            raise ValueError("PDF has no pages")

        page = doc.load_page(0)
        pix = page.get_pixmap(dpi=220)
        image_bytes = pix.tobytes("jpeg")
        return "image/jpeg", base64.b64encode(image_bytes).decode()

    if content_type.startswith("image/"):
        return content_type, base64.b64encode(file_bytes).decode()

    raise ValueError("Unsupported file type")


def _extract_json_block(text: str) -> dict:
    """Extract JSON from potentially wrapped fenced response."""
    cleaned = text.strip()
    if "```json" in cleaned:
        cleaned = cleaned.split("```json", 1)[1].split("```", 1)[0]
    elif "```" in cleaned:
        cleaned = cleaned.split("```", 1)[1].split("```", 1)[0]
    return json.loads(cleaned.strip())


@router.post("/analyze-skin")
async def analyze_skin(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
):
    """Analyze a skin condition from an uploaded image."""
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(400, "Please upload an image file (JPG, PNG, etc.)")

    image_bytes = await file.read()
    if len(image_bytes) > MAX_FILE_SIZE:
        raise HTTPException(400, "Image is too large. Maximum size is 10MB.")

    result = await analyze_skin_image(image_bytes)
    context_saved, context_record_id = await _store_analysis(
        current_user=current_user,
        analysis_type="skin",
        file=file,
        file_size=len(image_bytes),
        analysis=result,
        source_type="image",
    )

    return {
        "success": True,
        "filename": file.filename,
        "analysis": result,
        "context_saved": context_saved,
        "context_record_id": context_record_id,
        "disclaimer": "AI-supported analysis only. Please consult a qualified doctor.",
    }


@router.post("/analyze-lab")
async def analyze_lab_report(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
):
    """Upload a lab report (image or PDF) for AI analysis."""
    valid_types = ["image/jpeg", "image/png", "image/jpg", "application/pdf"]
    if not file.content_type or file.content_type not in valid_types:
        raise HTTPException(400, "Please upload an image or PDF of your lab report")

    file_bytes = await file.read()
    if len(file_bytes) > MAX_FILE_SIZE:
        raise HTTPException(400, "File is too large. Maximum size is 10MB.")

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

        mime_type, file_b64 = _prepare_gemini_input(file_bytes, file.content_type)

        prompt = """Analyze this medical lab report and respond with ONLY a JSON object:
{
  "tests": [
    {
      "name": "test name",
      "value": "result value",
      "unit": "unit of measurement",
      "normal_range": "normal range",
      "status": "normal/high/low/abnormal",
      "simple_explanation": "what this means in simple English"
    }
  ],
  "overall_summary": "brief overall health summary",
  "action_needed": "normal/monitor/see_doctor/urgent",
  "key_findings": "most important things the patient should know"
}"""

        last_error = None
        response = None
        for model_name in model_candidates:
            try:
                model = genai.GenerativeModel(model_name)
                response = model.generate_content([
                    {"mime_type": mime_type, "data": file_b64},
                    prompt,
                ])
                break
            except Exception as exc:
                last_error = exc

        if response is None:
            raise RuntimeError(f"All Gemini model candidates failed: {last_error}")

        result = _extract_json_block(response.text)

    except Exception as exc:
        log.error(f"Lab report analysis error: {exc}")
        result = {
            "error": "Could not read this lab report",
            "suggestion": "Please make sure the image is clear and well-lit",
            "action_needed": "see_doctor",
        }

    context_saved, context_record_id = await _store_analysis(
        current_user=current_user,
        analysis_type="lab",
        file=file,
        file_size=len(file_bytes),
        analysis=result,
        source_type="pdf" if file.content_type == "application/pdf" else "image",
    )

    return {
        "success": True,
        "filename": file.filename,
        "analysis": result,
        "source_type": "pdf" if file.content_type == "application/pdf" else "image",
        "context_saved": context_saved,
        "context_record_id": context_record_id,
        "disclaimer": "AI-supported interpretation only. Always discuss lab results with your doctor.",
    }


@router.post("/analyze-prescription")
async def analyze_prescription(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
):
    """Upload a prescription (image or PDF) for AI analysis."""
    valid_types = ["image/jpeg", "image/png", "image/jpg", "application/pdf"]
    if not file.content_type or file.content_type not in valid_types:
        raise HTTPException(400, "Please upload an image or PDF of your prescription")

    file_bytes = await file.read()
    if len(file_bytes) > MAX_FILE_SIZE:
        raise HTTPException(400, "File is too large. Maximum size is 10MB.")

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

        mime_type, file_b64 = _prepare_gemini_input(file_bytes, file.content_type)

        prompt = """Analyze this medical prescription and respond with ONLY a JSON object:
{
  "medications": [
    {
      "name": "medicine name",
      "strength": "e.g., 500mg or unknown",
      "dose_instruction": "e.g., 1 tablet after meals",
      "frequency": "e.g., twice daily or unknown",
      "duration": "e.g., 5 days or unknown",
      "purpose": "likely purpose in simple words"
    }
  ],
  "daily_schedule": [
    {"time": "morning/noon/night", "medicines": ["name"]}
  ],
  "safety_flags": ["important warning if any"],
  "follow_up_advice": "short actionable advice",
  "clarity_score": "high/medium/low"
}

Rules:
- If handwriting or name is unclear, use "unclear" and mention in safety_flags.
- Do not invent dangerous instructions.
- Keep language simple and patient friendly."""

        last_error = None
        response = None
        for model_name in model_candidates:
            try:
                model = genai.GenerativeModel(model_name)
                response = model.generate_content([
                    {"mime_type": mime_type, "data": file_b64},
                    prompt,
                ])
                break
            except Exception as exc:
                last_error = exc

        if response is None:
            raise RuntimeError(f"All Gemini model candidates failed: {last_error}")

        result = _extract_json_block(response.text)

    except Exception as exc:
        log.error(f"Prescription analysis error: {exc}")
        result = {
            "error": "Could not read this prescription clearly",
            "medications": [],
            "daily_schedule": [],
            "safety_flags": ["Please confirm medicine names and doses with your pharmacist or doctor."],
            "follow_up_advice": "Bring the original prescription to a nearby doctor or pharmacy for confirmation.",
            "clarity_score": "low",
        }

    context_saved, context_record_id = await _store_analysis(
        current_user=current_user,
        analysis_type="prescription",
        file=file,
        file_size=len(file_bytes),
        analysis=result,
        source_type="pdf" if file.content_type == "application/pdf" else "image",
    )

    return {
        "success": True,
        "filename": file.filename,
        "analysis": result,
        "source_type": "pdf" if file.content_type == "application/pdf" else "image",
        "context_saved": context_saved,
        "context_record_id": context_record_id,
        "disclaimer": "AI-supported interpretation only. Always confirm medicines with your doctor or pharmacist.",
    }
