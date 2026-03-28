"""Vision API - image analysis endpoints

This module handles AI analysis of medical images:
- Skin conditions (dermatology analysis)
- Lab reports (test result interpretation)
- Prescriptions (medicine extraction and safety)

All endpoints use Gemini Vision for multimodal analysis with
medical safety considerations and fallback error handling.
"""

from datetime import datetime
import base64
import json
import logging
from typing import Optional

import fitz
import google.generativeai as genai
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from app.ai.vision.skin_model import analyze_skin_image
from app.core.auth import get_current_user
from app.core.config import settings

# Debug: Print the loaded GEMINI_API_KEY to verify config loading
print("DEBUG: Loaded GEMINI_API_KEY from config:", repr(settings.GEMINI_API_KEY))
from app.core.database import vision_analyses
from app.core.errors import ValidationError, AIProviderError, DatabaseError

router = APIRouter(prefix="/vision", tags=["Vision - AI Image Analysis"])
log = logging.getLogger(__name__)

MAX_FILE_SIZE = 10 * 1024 * 1024
MAX_FILENAME_LENGTH = 255


async def _store_analysis(
    *,
    current_user: dict,
    analysis_type: str,
    file: UploadFile,
    file_size: int,
    analysis: dict,
    source_type: str,
) -> tuple[bool, Optional[str]]:
    """
    Persist analysis output for user history and downstream chat context.
    Logs errors but doesn't fail the primary response.
    """
    try:
        if not file.filename:
            raise ValueError("Missing filename")
        
        result = await vision_analyses().insert_one(
            {
                "user_id": current_user["_id"],
                "analysis_type": analysis_type,
                "filename": file.filename[:MAX_FILENAME_LENGTH],
                "content_type": file.content_type,
                "source_type": source_type,
                "file_size": file_size,
                "analysis": analysis,
                "created_at": datetime.utcnow(),
            }
        )
        log.info(f"Saved {analysis_type} analysis for user {current_user['_id']}: {result.inserted_id}")
        return True, str(result.inserted_id)
    except Exception as exc:
        # Do not fail primary API response on persistence issues
        log.warning(f"Could not save {analysis_type} analysis: {exc}", exc_info=True)
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


@router.post("/skin")
async def analyze_skin(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
):
    """
    Analyze a skin condition from an uploaded image using Gemini Vision.
    
    Returns: Skin condition analysis with severity, possible causes, and care recommendations.
    """
    # Validate file
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please upload an image file (JPG, PNG, WebP, etc.)"
        )
    
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must have a name"
        )

    try:
        image_bytes = await file.read()
    except Exception as e:
        log.error(f"Failed to read uploaded file: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to read file"
        )

    if len(image_bytes) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Image is too large. Maximum size is 10MB."
        )
    
    if len(image_bytes) < 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Image is too small or corrupted"
        )

    try:
        result = await analyze_skin_image(image_bytes, file.content_type)

        if result.get("analyzer") == "unavailable":
            raise RuntimeError(result.get("error") or "Skin analyzer unavailable")
        
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
            "analysis_type": "skin",
            "filename": file.filename,
            "analysis": result,
            "context_saved": context_saved,
            "context_record_id": context_record_id,
            "safety_notice": "AI-supported analysis only. For accurate diagnosis, please consult a qualified dermatologist.",
        }
    except Exception as e:
        log.error(f"Skin analysis error: {e}", exc_info=True)
        error_text = str(e).lower()
        detail = "Skin analysis service temporarily unavailable. Please try again later."
        if "api key" in error_text or "permission" in error_text or "quota" in error_text:
            detail = "Skin analysis service is unavailable due to AI provider configuration or quota limits. Please contact support."
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=detail
        )


@router.post("/lab-report")
async def analyze_lab_report(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
):
    """
    Analyze a lab report (image or PDF) for AI-assisted interpretation.
    
    Returns: Test results with values, ranges, status, and simple explanations.
    
    Safety Note: AI analysis is supplementary only. Always consult your doctor for medical advice.
    """
    valid_types = ["image/jpeg", "image/png", "image/jpg", "application/pdf"]
    if not file.content_type or file.content_type not in valid_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please upload an image or PDF of your lab report (JPEG, PNG, or PDF)"
        )

    try:
        file_bytes = await file.read()
    except Exception as e:
        log.error(f"Failed to read lab report file: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to read file"
        )

    if len(file_bytes) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File is too large. Maximum size is 10MB."
        )
    
    if len(file_bytes) < 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File is too small or corrupted"
        )

    try:
        if not settings.GEMINI_API_KEY:
            log.error("GEMINI_API_KEY not configured")
            raise AIProviderError(
                provider="Gemini",
                message="API key not configured",
                fallback_available=True
            )

        genai.configure(api_key=settings.GEMINI_API_KEY)
        # Use a supported vision-capable model from the available list
        model_candidates = [
              "models/gemini-2.5-flash-image",      # Vision-capable model
              "models/gemini-2.5-flash",            # Fallback if above fails
              "models/gemini-2.0-flash",            # Additional fallback, lighter model
              "models/gemini-3-flash-preview",      # Gemini 3 Flash (if quota available)
              "models/gemini-flash-latest",         # Latest flash model
              "models/gemini-2.5-flash-lite",       # Lite version
              "models/gemini-2.0-flash-lite-001",   # Older lite version
              "models/gemini-3.1-flash-lite-preview" # 3.1 flash lite preview
        ]

        mime_type, file_b64 = _prepare_gemini_input(file_bytes, file.content_type)

        prompt = """Analyze this medical lab report image and respond ONLY with a valid JSON object (no additional text):
{
  "tests": [
    {
      "name": "test name",
      "value": "numeric result or value",
      "unit": "measurement unit",
      "normal_range": "reference/normal range",
      "status": "normal/high/low/abnormal",
      "interpretation": "simple patient-friendly explanation"
    }
  ],
  "overall_assessment": "brief summary of results",
  "concerning_findings": "any critical values or abnormal results",
  "recommended_action": "normal/monitor/consult_doctor/urgent",
  "notes": "important patient guidance"
}

Rules:
- ONLY output valid JSON
- Use clear, patient-friendly language
- Flag any abnormal or critical values
- If unable to read clearly, note it in 'notes' field"""

        response = None
        last_error = None
        
        for model_name in model_candidates:
            try:
                model = genai.GenerativeModel(model_name)
                response = model.generate_content([
                    {"mime_type": mime_type, "data": file_b64},
                    prompt,
                ], request_options={"timeout": 30})
                if response and response.text:
                    break
            except Exception as exc:
                log.warning(f"Model {model_name} failed: {exc}")
                last_error = exc
                continue

        if not response or not response.text:
            # Hugging Face OCR fallback
            try:
                from transformers import pipeline
                import io
                from PIL import Image
                # Use trocr-base-printed for OCR
                ocr = pipeline("image-to-text", model="microsoft/trocr-base-printed", tokenizer="microsoft/trocr-base-printed")
                if file.content_type == "application/pdf":
                    import fitz
                    doc = fitz.open(stream=file_bytes, filetype="pdf")
                    if doc.page_count == 0:
                        raise ValueError("PDF has no pages")
                    page = doc.load_page(0)
                    pix = page.get_pixmap()
                    image_bytes = pix.tobytes("png")
                    image = Image.open(io.BytesIO(image_bytes))
                else:
                    image = Image.open(io.BytesIO(file_bytes))
                ocr_text = ocr(image)[0]['generated_text']
                result = {
                    "error": None,
                    "ocr_text": ocr_text,
                    "notes": "Gemini models unavailable. Used Hugging Face OCR fallback.",
                    "recommended_action": "consult_doctor",
                }
            except Exception as hf_exc:
                log.error(f"Hugging Face OCR fallback failed: {hf_exc}", exc_info=True)
                raise RuntimeError(f"No response from any Gemini model, and Hugging Face OCR fallback failed: {hf_exc}")
        else:
            result = _extract_json_block(response.text)

    except json.JSONDecodeError as e:
        log.error(f"Failed to parse lab report analysis JSON: {e}")
        result = {
            "error": "Could not parse lab report format",
            "notes": "Please make sure the lab report is clear and complete",
            "recommended_action": "consult_doctor",
        }
    except Exception as exc:
        log.error(f"Lab report analysis error: {exc}", exc_info=True)
        result = {
            "error": "Could not analyze lab report at this time",
            "notes": "Please try again or consult your doctor with the original report",
            "recommended_action": "consult_doctor",
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
        "success": result.get("error") is None,
        "analysis_type": "lab_report",
        "filename": file.filename,
        "analysis": result,
        "source_type": "pdf" if file.content_type == "application/pdf" else "image",
        "context_saved": context_saved,
        "context_record_id": context_record_id,
        "safety_notice": "AI-assisted interpretation only. Always discuss lab results with your healthcare provider for accurate diagnosis and treatment recommendations.",
    }


@router.post("/prescription")
async def analyze_prescription(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
):
    """
    Analyze a prescription (image or PDF) for medicine extraction and safety information.
    
    Returns: Medication list, schedule, dosage instructions, and safety warnings.
    
    Safety Note: Always confirm medicines with your pharmacist or doctor before taking.
    """
    valid_types = ["image/jpeg", "image/png", "image/jpg", "application/pdf"]
    if not file.content_type or file.content_type not in valid_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please upload an image or PDF of your prescription (JPEG, PNG, or PDF)"
        )

    try:
        file_bytes = await file.read()
    except Exception as e:
        log.error(f"Failed to read prescription file: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to read file"
        )

    if len(file_bytes) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File is too large. Maximum size is 10MB."
        )
    
    if len(file_bytes) < 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File is too small or corrupted"
        )

    try:
        if not settings.GEMINI_API_KEY:
            log.error("GEMINI_API_KEY not configured")
            raise AIProviderError(
                provider="Gemini",
                message="API key not configured",
                fallback_available=True
            )

        genai.configure(api_key=settings.GEMINI_API_KEY)
        model_candidates = [
            "models/gemini-2.5-flash-image",
            "models/gemini-2.5-flash",
            "models/gemini-2.0-flash",
            "models/gemini-3-flash-preview",
            "models/gemini-flash-latest",
            "models/gemini-2.5-flash-lite",
            "models/gemini-2.0-flash-lite-001",
            "models/gemini-3.1-flash-lite-preview"
        ]

        mime_type, file_b64 = _prepare_gemini_input(file_bytes, file.content_type)

        prompt = (
            """Analyze this medical prescription image and respond ONLY with a valid JSON object (no additional text):\n"
            "{ \n"
            "    \"medications\": [\n"
            "        {\n"
            "            \"name\": \"medicine name\",\n"
            "            \"strength\": \"dosage strength (e.g., 500mg)\",\n"
            "            \"dose_instruction\": \"dose per use (e.g., 1 tablet)\",\n"
            "            \"frequency\": \"how often (e.g., twice daily, three times daily)\",\n"
            "            \"duration\": \"treatment duration (e.g., 5 days, 2 weeks)\",\n"
            "            \"with_food\": \"yes/no/unknown\",\n"
            "            \"purpose\": \"why this medicine (if visible)\"\n"
            "        }\n"
            "    ],\n"
            "    \"medication_schedule\": [\n"
            "        {\"time\": \"morning/noon/evening/night\", \"medicines\": [\"medicine names\"]}\n"
            "    ],\n"
            "    \"special_instructions\": [\"specific patient instructions if any\"],\n"
            "    \"safety_warnings\": [\"important warnings or contradictions\"],\n"
            "    \"doctor_name\": \"doctor name if visible\",\n"
            "    \"patient_name\": \"patient name if visible\",\n"
            "    \"prescription_date\": \"date if visible\",\n"
            "    \"clarity\": \"high/medium/low\"\n"
            "}"""
        )

        response = None
        last_error = None
        for model_name in model_candidates:
            try:
                model = genai.GenerativeModel(model_name)
                response = model.generate_content([
                    {"mime_type": mime_type, "data": file_b64},
                    prompt,
                ], request_options={"timeout": 30})
                if response and response.text:
                    break
            except Exception as exc:
                log.warning(f"Model {model_name} failed: {exc}")
                last_error = exc
                continue

        if not response or not response.text:
            # Hugging Face OCR fallback
            try:
                from transformers import pipeline
                import io
                from PIL import Image
                ocr = pipeline("image-to-text", model="microsoft/trocr-base-printed", tokenizer="microsoft/trocr-base-printed")
                if file.content_type == "application/pdf":
                    import fitz
                    doc = fitz.open(stream=file_bytes, filetype="pdf")
                    if doc.page_count == 0:
                        raise ValueError("PDF has no pages")
                    page = doc.load_page(0)
                    pix = page.get_pixmap()
                    image_bytes = pix.tobytes("png")
                    image = Image.open(io.BytesIO(image_bytes))
                else:
                    image = Image.open(io.BytesIO(file_bytes))
                ocr_text = ocr(image)[0]['generated_text']
                result = {
                    "error": None,
                    "ocr_text": ocr_text,
                    "notes": "Gemini models unavailable. Used Hugging Face OCR fallback.",
                    "safety_warnings": ["Gemini models unavailable. Used Hugging Face OCR fallback. Please confirm with your pharmacist."],
                }
            except Exception as hf_exc:
                log.error(f"Hugging Face OCR fallback failed: {hf_exc}", exc_info=True)
                raise RuntimeError(f"No response from any Gemini model, and Hugging Face OCR fallback failed: {hf_exc}")
        else:
            result = _extract_json_block(response.text)

    except json.JSONDecodeError as e:
        log.error(f"Failed to parse prescription analysis JSON: {e}")
        result = {
            "error": "Could not parse prescription format",
            "medications": [],
            "safety_warnings": ["Could not read prescription clearly. Please confirm with your pharmacist."],
        }
    except Exception as exc:
        log.error(f"Prescription analysis error: {exc}", exc_info=True)
        result = {
            "error": "Could not analyze prescription at this time",
            "medications": [],
            "safety_warnings": ["Please try again or confirm medicine details with your pharmacist."],
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
        "success": result.get("error") is None,
        "analysis_type": "prescription",
        "filename": file.filename,
        "analysis": result,
        "source_type": "pdf" if file.content_type == "application/pdf" else "image",
        "context_saved": context_saved,
        "context_record_id": context_record_id,
        "safety_notice": "IMPORTANT: Always confirm medicine names and dosages with your pharmacist or doctor before taking. Do not rely solely on AI analysis.",
    }
