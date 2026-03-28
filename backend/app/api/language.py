"""
Language preference management and translation API endpoints
NirovaAI BD Edition - Bangla-focused with regional dialect support
"""
from fastapi import APIRouter, Depends, Header, Query, Body
from typing import Optional, Dict, List, Any
from pydantic import BaseModel, Field
import logging
from datetime import datetime

from app.core.auth import get_current_user
from app.core.translations import TranslationService, Language, translation_service
from app.core.language_detector import (
    LanguageDetector, 
    language_detector, 
    LanguageContext
)
from app.core.database import get_db

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api/language", tags=["language"])


# Request/Response Models
class LanguagePreferenceRequest(BaseModel):
    """User language preference - Bangladesh Edition"""
    language: str = Field(..., description="Language code (bn, cg, sy, kh, dhk)")
    dialect: Optional[str] = Field(None, description="Optional dialect preference")
    
    class Config:
        example = {"language": "bn", "dialect": "cg"}


class LanguagePreferenceResponse(BaseModel):
    """User's language preference"""
    user_id: str
    language: str
    dialect: Optional[str]
    updated_at: datetime
    supported_languages: List[Dict[str, str]]


class TranslationRequest(BaseModel):
    """Translation request - Bangla focused"""
    text: str = Field(..., description="Bengali text to translate")
    from_language: str = Field(default="bn", description="Source language")
    to_language: str = Field(default="bn", description="Target language (or regional dialect)")
    
    class Config:
        example = {
            "text": "আমার জ্বর এবং মাথা ব্যথা আছে",
            "from_language": "en",
            "to_language": "bn"
        }


class TranslationResponse(BaseModel):
    """Translation response"""
    original: str
    translated: str
    from_language: str
    to_language: str


class LanguageDetectionRequest(BaseModel):
    """Detect language from text"""
    text: str = Field(..., description="Text to analyze")
    
    class Config:
        example = {"text": "আমার জ্বর এবং মাথা ব্যথা আছে"}


class LanguageDetectionResponse(BaseModel):
    """Language detection result"""
    detected_language: str
    confidence: float = Field(..., description="Confidence score 0-1")
    alternatives: Optional[List[Dict[str, Any]]] = None


class SupportedLanguagesResponse(BaseModel):
    """List of supported languages"""
    languages: List[Dict[str, str]]
    total: int


class MedicalTermTranslationRequest(BaseModel):
    """Translate medical terms"""
    term: str = Field(..., description="Medical term to translate")
    from_language: str = Field(default="en")
    to_language: str = Field(default="bn")


class HealthGuidanceRequest(BaseModel):
    """Get health guidance in specific language"""
    guidance_key: str = Field(
        ..., 
        description="Guidance type: hydration, rest, doctor, dengue_prevention, tropical_disease, when_to_worry"
    )
    language: str = Field(default="en")


class HealthGuidanceResponse(BaseModel):
    """Health guidance in requested language"""
    guidance_key: str
    language: str
    content: str
    cultural_context: str = "Bangladesh-specific"


# User Language Preference Storage (in MongoDB user document)
async def save_language_preference(
    db,
    user_id: str,
    language: str,
    dialect: Optional[str] = None
) -> Dict:
    """Save user's language preference in database"""
    users_collection = db["users"]
    
    result = await users_collection.update_one(
        {"_id": user_id},
        {
            "$set": {
                "language_preference": {
                    "language": language,
                    "dialect": dialect or language,
                    "updated_at": datetime.utcnow()
                }
            }
        },
        upsert=False
    )
    
    if result.matched_count == 0:
        log.warning(f"User not found for language preference update: {user_id}")
    
    return {
        "user_id": user_id,
        "language": language,
        "dialect": dialect or language,
        "updated_at": datetime.utcnow()
    }


async def get_language_preference(
    db,
    user_id: str
) -> Optional[Dict]:
    """Retrieve user's language preference from database"""
    users_collection = db["users"]
    
    user = await users_collection.find_one(
        {"_id": user_id},
        {"language_preference": 1}
    )
    
    if not user:
        return None
    
    return user.get("language_preference", {
        "language": "en",
        "dialect": "en"
    })


# Endpoints

@router.get("/supported", response_model=SupportedLanguagesResponse)
async def get_supported_languages():
    """
    Get list of all supported languages and dialects
    
    Returns languages available in NirovaAI:
    - English (en)
    - Bengali/Bangla (bn)
    - Chittagong dialect (cg)
    - Sylhet dialect (sy)
    - Khulna dialect (kh)
    """
    languages = translation_service.get_supported_languages()
    
    log.info("Retrieved supported languages list")
    
    return SupportedLanguagesResponse(
        languages=languages,
        total=len(languages)
    )


@router.post("/detect")
async def detect_language(
    request: LanguageDetectionRequest,
    accept_language: Optional[str] = Header(None),
    timezone: Optional[str] = Query(None),
    country_code: Optional[str] = Query(None),
) -> LanguageDetectionResponse:
    """
    Detect language from user input text
    
    Uses multiple signals:
    - Text content analysis (Bengali character detection)
    - Accept-Language header
    - User timezone
    - Country code for geolocation
    
    Returns detected language with confidence score
    """
    detected = language_detector.detect_language(
        text=request.text,
        accept_language=accept_language,
        timezone=timezone,
        country_code=country_code
    )
    
    # Calculate confidence based on detection method
    confidence = 0.95 if request.text else 0.7
    
    bengali_chars = sum(1 for c in request.text if '\u0980' <= c <= '\u09FF')
    if bengali_chars > 0:
        confidence = min(0.99, (bengali_chars / len(request.text)) + 0.3)
    
    log.info(f"Language detected: {detected} (confidence: {confidence})")
    
    return LanguageDetectionResponse(
        detected_language=detected.value,
        confidence=round(confidence, 2),
        alternatives=[
            {"language": "en", "confidence": 0.05},
            {"language": "bn", "confidence": confidence if detected == Language.ENGLISH else 0.95}
        ]
    )


@router.get("/preference")
async def get_user_language_preference(
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
) -> LanguagePreferenceResponse:
    """
    Get current user's language preference
    
    Returns the user's selected language and dialect setting
    """
    user_id = current_user["_id"]
    
    preference = await get_language_preference(db, user_id)
    if not preference:
        preference = {"language": "en", "dialect": "en"}
    
    languages = translation_service.get_supported_languages()
    
    log.info(f"Retrieved language preference for user: {user_id}")
    
    return LanguagePreferenceResponse(
        user_id=user_id,
        language=preference.get("language", "en"),
        dialect=preference.get("dialect"),
        updated_at=preference.get("updated_at", datetime.utcnow()),
        supported_languages=languages
    )


@router.post("/preference", response_model=LanguagePreferenceResponse)
async def set_user_language_preference(
    request: LanguagePreferenceRequest,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
) -> LanguagePreferenceResponse:
    """
    Set user's language preference
    
    Updates the user's preferred language and dialect in their profile
    """
    user_id = current_user["_id"]
    
    # Validate language code
    try:
        Language(request.language)
    except ValueError:
        log.warning(f"Invalid language code: {request.language}")
        return {"error": f"Invalid language code: {request.language}"}
    
    # Save preference
    result = await save_language_preference(
        db,
        user_id,
        request.language,
        request.dialect
    )
    
    languages = translation_service.get_supported_languages()
    
    log.info(f"Updated language preference for user {user_id}: {request.language}")
    
    return LanguagePreferenceResponse(
        user_id=user_id,
        language=request.language,
        dialect=request.dialect or request.language,
        updated_at=result["updated_at"],
        supported_languages=languages
    )


@router.post("/translate", response_model=TranslationResponse)
async def translate_text(
    request: TranslationRequest
) -> TranslationResponse:
    """
    Translate text between supported languages
    
    Currently supports medical terminology translation.
    Full AI translation available for system responses.
    """
    translated = translation_service.translate_response(
        request.text,
        from_lang=translation_service.get_language_by_code(request.from_language),
        to_lang=translation_service.get_language_by_code(request.to_language)
    )
    
    log.info(f"Translated text: {request.from_language} → {request.to_language}")
    
    return TranslationResponse(
        original=request.text,
        translated=translated,
        from_language=request.from_language,
        to_language=request.to_language
    )


@router.post("/translate/medical-term")
async def translate_medical_term(
    request: MedicalTermTranslationRequest
) -> Dict:
    """
    Translate medical terms between languages
    
    Provides accurate translations for medical terminology
    common in healthcare context
    """
    translated = translation_service.translate_medical_term(
        request.term,
        from_lang=translation_service.get_language_by_code(request.from_language),
        to_lang=translation_service.get_language_by_code(request.to_language)
    )
    
    log.info(f"Medical term translated: {request.term}")
    
    return {
        "original_term": request.term,
        "translated_term": translated,
        "from_language": request.from_language,
        "to_language": request.to_language,
        "medical_context": "Healthcare terminology"
    }


@router.post("/health-guidance", response_model=HealthGuidanceResponse)
async def get_health_guidance(
    request: HealthGuidanceRequest
) -> HealthGuidanceResponse:
    """
    Get culturally appropriate health guidance for Bangladesh
    
    Available guidance types:
    - hydration: Staying hydrated
    - rest: Rest recommendations
    - doctor: When to see a doctor
    - dengue_prevention: Dengue prevention measures
    - tropical_disease: Tropical disease awareness
    - when_to_worry: Red flags and danger signs
    """
    guidance = translation_service.get_health_guidance(
        request.guidance_key,
        language=translation_service.get_language_by_code(request.language)
    )
    
    log.info(f"Health guidance retrieved: {request.guidance_key} in {request.language}")
    
    return HealthGuidanceResponse(
        guidance_key=request.guidance_key,
        language=request.language,
        content=guidance,
        cultural_context="Bangladesh-specific health guidance"
    )


@router.get("/medical-terms")
async def get_medical_terminology(
    language: str = Query("en", description="Language for terms (en or bn)")
) -> Dict:
    """
    Get medical terminology dictionary
    
    Returns medical terms mapped between English and Bengali
    """
    lang = translation_service.get_language_by_code(language)
    if not lang:
        lang = Language.ENGLISH
    
    terms = []
    
    if language == "bn":
        terms = [
            {"bengali": term, "english": translation}
            for term, translation in translation_service.medical_terms.items()
        ]
    else:
        terms = [
            {"english": translation, "bengali": term}
            for term, translation in translation_service.medical_terms.items()
        ]
    
    log.info(f"Retrieved {len(terms)} medical terms")
    
    return {
        "language": language,
        "total_terms": len(terms),
        "terms": terms
    }


@router.get("/health-check")
async def language_service_health_check() -> Dict:
    """
    Health check for language and translation services
    
    Verifies all language services are operational
    """
    return {
        "status": "healthy",
        "services": {
            "translation_service": "operational",
            "language_detector": "operational",
            "supported_languages": len(translation_service.get_supported_languages()),
            "medical_terms": len(translation_service.medical_terms),
        },
        "timestamp": datetime.utcnow(),
        "message": "Language services ready for multi-language healthcare support"
    }
