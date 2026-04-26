"""
NirovaAI Error Monitoring and Health Checks
============================================
Production-ready error tracking, health monitoring, and safe defaults.
"""

from datetime import datetime, timedelta
from typing import Dict, Any
import logging
import json
from collections import defaultdict

log = logging.getLogger(__name__)

# Error tracking
_error_counters = defaultdict(int)
_error_timestamps = defaultdict(list)
MAX_ERRORS_TRACKED_PER_TYPE = 100


class ErrorMonitor:
    """Tracks errors and generates health reports."""
    
    @staticmethod
    def record_error(error_code: str, error_message: str, severity: str = "warning"):
        """
        Record an error for monitoring.
        
        Args:
            error_code: Machine-readable error identifier (e.g., "DB_ERROR", "LLM_TIMEOUT")
            error_message: Human-readable error description
            severity: "info", "warning", "error", or "critical"
        """
        timestamp = datetime.utcnow()
        _error_counters[error_code] += 1
        
        # Keep last N timestamps for rate tracking
        _error_timestamps[error_code].append(timestamp)
        if len(_error_timestamps[error_code]) > MAX_ERRORS_TRACKED_PER_TYPE:
            _error_timestamps[error_code] = _error_timestamps[error_code][-MAX_ERRORS_TRACKED_PER_TYPE:]
        
        logger = log
        getattr(logger, {
            "info": "info",
            "warning": "warning",
            "error": "error",
            "critical": "critical"
        }.get(severity, "warning"))(
            json.dumps({
                "event": "error_recorded",
                "error_code": error_code,
                "severity": severity,
                "timestamp": timestamp.isoformat(),
                "count": _error_counters[error_code],
            })
        )
    
    @staticmethod
    def get_error_stats() -> Dict[str, Any]:
        """Get error statistics for health dashboard."""
        stats = {}
        now = datetime.utcnow()
        
        for error_code, timestamps in _error_timestamps.items():
            # Filter recent errors (last 1 hour)
            recent = [ts for ts in timestamps if (now - ts) < timedelta(hours=1)]
            
            stats[error_code] = {
                "total_count": _error_counters[error_code],
                "recent_count": len(recent),
                "error_rate_per_hour": len(recent),
                "last_error": max(timestamps).isoformat() if timestamps else None,
            }
        
        return stats
    
    @staticmethod
    def is_service_degraded(threshold: int = 5) -> bool:
        """
        Check if services are degraded based on error rates.
        
        Args:
            threshold: Errors per hour threshold to consider degraded
        
        Returns: True if any service is experiencing high error rate
        """
        stats = ErrorMonitor.get_error_stats()
        for error_code, data in stats.items():
            if data["error_rate_per_hour"] > threshold:
                log.warning(f"Service degradation detected: {error_code} ({data['error_rate_per_hour']} errors/hour)")
                return True
        return False
    
    @staticmethod
    def reset_counters():
        """Reset error counters (use sparingly)."""
        global _error_counters, _error_timestamps
        _error_counters.clear()
        _error_timestamps.clear()
        log.info("Error counters reset")


class HealthCheck:
    """System health monitoring."""
    
    @staticmethod
    async def check_mongodb(db_client) -> Dict[str, Any]:
        """Check MongoDB connectivity."""
        try:
            # Ping the database
            await db_client.admin.command('ping')
            return {
                "status": "healthy",
                "service": "MongoDB",
                "timestamp": datetime.utcnow().isoformat()
            }
        except Exception as e:
            ErrorMonitor.record_error("DB_PING_FAILED", str(e), "error")
            return {
                "status": "unhealthy",
                "service": "MongoDB",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    @staticmethod
    async def check_redis(redis_client) -> Dict[str, Any]:
        """Check Redis connectivity."""
        try:
            await redis_client.ping()
            return {
                "status": "healthy",
                "service": "Redis",
                "timestamp": datetime.utcnow().isoformat()
            }
        except Exception as e:
            ErrorMonitor.record_error("REDIS_PING_FAILED", str(e), "warning")
            return {
                "status": "degraded",  # Redis is optional
                "service": "Redis",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    @staticmethod
    def check_configuration(settings) -> Dict[str, Any]:
        """Check critical configuration."""
        issues = []
        
        # Check SECRET_KEY
        if settings.SECRET_KEY == "dev-secret-change-me":
            issues.append("SECRET_KEY is using default development value")
        elif len(settings.SECRET_KEY) < 32:
            issues.append("SECRET_KEY is less than 32 characters")
        
        # Check MONGODB_URI
        if not settings.MONGODB_URI:
            issues.append("MONGODB_URI is not set")
        
        # Check LLM API keys
        if not any([settings.GROQ_API_KEY, settings.GEMINI_API_KEY, settings.HF_API_KEY]):
            issues.append("No LLM API keys configured (at least one recommended)")
        
        # Check CORS
        if not settings.allowed_origins_list and not settings.CORS_ORIGIN_REGEX:
            issues.append("CORS origins not properly configured")
        
        return {
            "status": "healthy" if not issues else "warning",
            "issues": issues,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    @staticmethod
    async def full_health_check(app) -> Dict[str, Any]:
        """Comprehensive health check."""
        checks = {
            "timestamp": datetime.utcnow().isoformat(),
            "configuration": HealthCheck.check_configuration(app.state.settings if hasattr(app.state, 'settings') else {}),
            "error_stats": ErrorMonitor.get_error_stats(),
            "services": {}
        }
        
        # Add service-specific checks if available
        if hasattr(app.state, 'mongo_connected'):
            checks["services"]["mongodb"] = {
                "connected": app.state.mongo_connected
            }
        
        # Determine overall status
        if any(issue in checks["configuration"]["issues"] for issue in [
            "SECRET_KEY is using default",
            "MONGODB_URI is not set",
            "No LLM API keys"
        ]):
            checks["overall_status"] = "degraded"
        elif ErrorMonitor.is_service_degraded():
            checks["overall_status"] = "degraded"
        else:
            checks["overall_status"] = "healthy"
        
        return checks


class SafeDefaults:
    """Safe fallback values for service failures."""
    
    # Medical triage defaults
    DEFAULT_TRIAGE_COLOR = "yellow"  # Conservative default
    DEFAULT_CONFIDENCE = 0.3  # Conservative confidence
    
    # Response defaults
    DEFAULT_AI_RESPONSE = (
        "I'm temporarily unable to provide personalized guidance. "
        "Please:\n\n"
        "• Rest and stay hydrated\n"
        "• Monitor your symptoms\n"
        "• Seek medical care if symptoms worsen or persist\n\n"
        "For urgent concerns, contact a healthcare provider immediately."
    )
    
    DEFAULT_DIAGNOSIS = "Unable to determine at this time"
    DEFAULT_RISK_LEVEL = "unknown"
    
    @staticmethod
    def get_safe_prediction() -> Dict[str, Any]:
        """Get safe default prediction when models are unavailable."""
        return {
            "predicted_disease": SafeDefaults.DEFAULT_DIAGNOSIS,
            "confidence": SafeDefaults.DEFAULT_CONFIDENCE,
            "triage_color": SafeDefaults.DEFAULT_TRIAGE_COLOR,
            "recommended_action": "Consult a healthcare provider",
            "note": "Could not process symptoms at this time. Professional medical evaluation recommended."
        }
    
    @staticmethod
    def get_safe_ai_response(context: str = "general") -> str:
        """Get safe AI response when LLM is unavailable."""
        responses = {
            "symptom_inquiry": (
                "I'm temporarily unavailable. Please:\n"
                "• Monitor your symptoms closely\n"
                "• Seek medical care if symptoms worsen\n"
                "• Try again shortly"
            ),
            "prescription": (
                "I'm temporarily unable to help with prescription analysis. "
                "Please consult your pharmacist or doctor."
            ),
            "lab_report": (
                "I'm temporarily unable to help with lab result interpretation. "
                "Please discuss your results with your doctor."
            ),
        }
        return responses.get(context, SafeDefaults.DEFAULT_AI_RESPONSE)


# Production monitoring utilities
_startup_time = datetime.utcnow()

def get_uptime_seconds() -> int:
    """Get service uptime in seconds."""
    return int((datetime.utcnow() - _startup_time).total_seconds())


def format_uptime(seconds: int) -> str:
    """Format uptime as human-readable string."""
    days = seconds // 86400
    hours = (seconds % 86400) // 3600
    minutes = (seconds % 3600) // 60
    
    parts = []
    if days > 0:
        parts.append(f"{days}d")
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0:
        parts.append(f"{minutes}m")
    
    return " ".join(parts) if parts else "< 1m"
