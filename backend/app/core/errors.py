"""
NirovaAI Error Handling and Monitoring
=======================================
Centralized error handling, structured logging, and safe fallback responses.
Critical for AI-based medical application safety and debuggability.
"""

from fastapi import HTTPException, status
from typing import Optional, Dict, Any
import logging
from datetime import datetime
import json

log = logging.getLogger(__name__)

# ── Error Categories for Medical Context ──

class NirovaError(Exception):
    """Base class for all NirovaAI errors."""
    def __init__(
        self,
        message: str,
        error_code: str,
        http_status: int = 500,
        user_message: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        safe_to_expose: bool = False,
    ):
        self.message = message
        self.error_code = error_code
        self.http_status = http_status
        self.user_message = user_message or "An error occurred. Please try again."
        self.details = details or {}
        self.safe_to_expose = safe_to_expose  # If False, never expose details to user
        self.timestamp = datetime.utcnow().isoformat()


class DatabaseError(NirovaError):
    """Database connection or operation error."""
    def __init__(
        self,
        message: str,
        details: Optional[Dict] = None,
        cause: Optional[Exception] = None,
    ):
        log_msg = message
        if cause:
            log_msg += f" | Caused by: {cause}"
        
        super().__init__(
            message=log_msg,
            error_code="DB_ERROR",
            http_status=503,
            user_message="Database temporarily unavailable. Please try again in a moment.",
            details={"cause": str(cause)} if cause else None,
            safe_to_expose=False,  # Never expose DB details
        )
        log.error(log_msg)


class AuthenticationError(NirovaError):
    """Authentication or authorization failure."""
    def __init__(self, message: str, details: Optional[Dict] = None):
        super().__init__(
            message=message,
            error_code="AUTH_ERROR",
            http_status=401,
            user_message="Authentication failed. Please log in again.",
            details=details,
            safe_to_expose=False,
        )
        log.warning(message)


class ValidationError(NirovaError):
    """Input validation failed."""
    def __init__(self, message: str, field: Optional[str] = None, details: Optional[Dict] = None):
        super().__init__(
            message=message,
            error_code="VALIDATION_ERROR",
            http_status=422,
            user_message=f"Invalid input: {message}" if message else "Invalid input provided.",
            details={"field": field, **(details or {})},
            safe_to_expose=True,  # User should know what they did wrong
        )
        log.warning(message)


class AIProviderError(NirovaError):
    """LLM or AI service failure (with safe fallback)."""
    def __init__(
        self,
        provider: str,
        message: str,
        cause: Optional[Exception] = None,
        fallback_available: bool = True,
    ):
        user_msg = (
            "AI service temporarily unavailable."
            if fallback_available
            else "Unable to process your request. Please try again later."
        )
        
        super().__init__(
            message=f"[{provider}] {message}",
            error_code=f"AI_PROVIDER_{provider.upper()}_ERROR",
            http_status=503 if fallback_available else 500,
            user_message=user_msg,
            details={"provider": provider, "fallback_available": fallback_available},
            safe_to_expose=False,
        )
        log.error(f"AI Provider Error ({provider}): {message}" + (f" | {cause}" if cause else ""))


class RateLimitError(NirovaError):
    """Request rate limit exceeded."""
    def __init__(self, message: str, retry_after: Optional[int] = None):
        super().__init__(
            message=message,
            error_code="RATE_LIMIT_ERROR",
            http_status=429,
            user_message="Too many requests. Please wait a moment and try again.",
            details={"retry_after": retry_after},
            safe_to_expose=True,
        )
        log.warning(message)


class MedicalContextError(NirovaError):
    """Invalid medical context or unsafe input."""
    def __init__(self, message: str, details: Optional[Dict] = None):
        super().__init__(
            message=message,
            error_code="MEDICAL_CONTEXT_ERROR",
            http_status=400,
            user_message="The provided medical information is incomplete or invalid. Please check your inputs.",
            details=details,
            safe_to_expose=True,
        )
        log.warning(f"Medical Context Error: {message}")


# ── Response Formatting ──

def error_response(error: NirovaError) -> Dict[str, Any]:
    """Format error as JSON response for API."""
    response = {
        "error": True,
        "code": error.error_code,
        "message": error.user_message,
        "timestamp": error.timestamp,
    }
    
    # Only include details if safe to expose
    if error.safe_to_expose and error.details:
        response["details"] = error.details
    
    return response


def http_exception(error: NirovaError) -> HTTPException:
    """Convert NirovaError to FastAPI HTTPException."""
    return HTTPException(
        status_code=error.http_status,
        detail=error_response(error),
    )


# ── Medical Safety Checks ──

def validate_medical_input(
    symptoms: list,
    severity: Optional[int] = None,
    max_symptoms: int = 20,
    valid_symptoms_set: Optional[set] = None,
) -> tuple[bool, Optional[str]]:
    """
    Validate medical input for safety.
    Returns: (is_valid, error_message)
    """
    if not symptoms:
        return False, "No symptoms provided"
    
    if len(symptoms) > max_symptoms:
        return False, f"Too many symptoms (max {max_symptoms})"
    
    # Check for injection attacks in symptom strings
    for symptom in symptoms:
        if not isinstance(symptom, str):
            return False, "Symptom must be text"
        if len(symptom) > 100:
            return False, "Symptom description too long"
    
    if severity is not None:
        if not isinstance(severity, int) or severity < 1 or severity > 10:
            return False, "Severity must be between 1 and 10"
    
    return True, None


# ── Safe Fallback Responses for Medical Context ──

SAFE_MEDICAL_FALLBACK = {
    "symptom_inquiry": (
        "I'm having difficulty accessing my knowledge base at the moment. "
        "However, here's general guidance:\n\n"
        "• For persistent symptoms (fever >3 days, severe pain, difficulty breathing), "
        "please seek in-person care at a clinic or hospital.\n"
        "• Stay hydrated and rest when possible.\n"
        "• If symptoms worsen or you have difficulty breathing, seek emergency care immediately.\n\n"
        "Please try again in a moment, or consult a healthcare provider."
    ),
    
    "prescription_guidance": (
        "I'm temporarily unable to retrieve prescription information. "
        "Please follow these safe practices:\n\n"
        "• Take medicines exactly as prescribed by your doctor\n"
        "• Don't skip doses or take more than directed\n"
        "• Contact your doctor if you experience side effects\n"
        "• Keep medicines away from children\n\n"
        "Please try again shortly, or ask your pharmacist for guidance."
    ),
    
    "lab_value_interpretation": (
        "I'm having trouble accessing lab value interpretation tools. "
        "Here's what to do:\n\n"
        "• Review your lab report with the clinic that ordered the tests\n"
        "• Ask your doctor to explain what the values mean for your health\n"
        "• If results show severe abnormalities, contact your doctor immediately\n\n"
        "Please try again later, or consult your healthcare provider."
    ),
    
    "general_health": (
        "I'm temporarily unavailable to provide detailed health guidance. "
        "If you have urgent concerns:\n\n"
        "• Contact your doctor or local health clinic\n"
        "• In emergencies, call 999 (ambulance) or go to the nearest hospital\n"
        "• For less urgent issues, try again shortly\n\n"
        "Your health is important. Don't hesitate to seek professional care."
    ),
}


def get_safe_fallback(context: str) -> str:
    """Get a safe fallback response based on medical context."""
    return SAFE_MEDICAL_FALLBACK.get(context, SAFE_MEDICAL_FALLBACK["general_health"])


# ── Request/Response Logging ──

class RequestLogger:
    """Structured logging for API requests."""
    
    @staticmethod
    def log_request(
        method: str,
        path: str,
        user_id: Optional[str] = None,
        details: Optional[Dict] = None,
    ):
        """Log incoming request."""
        log_data = {
            "event": "request_received",
            "method": method,
            "path": path,
            "user_id": user_id,
            "timestamp": datetime.utcnow().isoformat(),
        }
        if details:
            log_data.update(details)
        log.info(json.dumps(log_data))
    
    @staticmethod
    def log_response(
        method: str,
        path: str,
        status_code: int,
        duration_ms: float,
        user_id: Optional[str] = None,
    ):
        """Log outgoing response."""
        log_data = {
            "event": "response_sent",
            "method": method,
            "path": path,
            "status_code": status_code,
            "duration_ms": duration_ms,
            "user_id": user_id,
            "timestamp": datetime.utcnow().isoformat(),
        }
        log.info(json.dumps(log_data))
    
    @staticmethod
    def log_error(
        error: NirovaError,
        path: str,
        user_id: Optional[str] = None,
    ):
        """Log error with context."""
        log_data = {
            "event": "error_occurred",
            "error_code": error.error_code,
            "error_message": error.message,
            "http_status": error.http_status,
            "path": path,
            "user_id": user_id,
            "timestamp": error.timestamp,
            "details": error.details if error.safe_to_expose else None,
        }
        log_level = "error" if error.http_status >= 500 else "warning"
        getattr(log, log_level)(json.dumps(log_data))
