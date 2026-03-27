"""
NirovaAI — Configuration
========================
All settings come from the .env file.
Never hardcode secrets in code — always use environment variables.

Use the root .env file and fill in your values before running.
"""


from dotenv import load_dotenv
from pathlib import Path
from pydantic_settings import BaseSettings
from pydantic import field_validator
from functools import lru_cache
from typing import List

# Always load .env from the repository root, regardless of working directory
env_path = Path(__file__).resolve().parent.parent.parent.parent / ".env"
load_dotenv(dotenv_path=env_path)


class Settings(BaseSettings):
    # App basics
    APP_NAME: str = "NirovaAI"
    DEBUG: bool = False
    ALLOWED_ORIGINS: str = "http://localhost:3000,http://localhost:5173"
    CORS_ORIGIN_REGEX: str = r"https?://(localhost|127\.0\.0\.1)(:\d+)?$"
    FRONTEND_URL: str = "http://localhost:5173"
    VITE_API_URL: str = ""

    # MongoDB Atlas connection
    # Get from: atlas.mongodb.com → Connect → Drivers
    # Optional for local bring-up (API will run in degraded mode without DB)
    MONGODB_URI: str = ""
    MONGODB_DB_NAME: str = "nirovaai"
    MONGO_INSECURE_TLS: bool = False

    # JWT authentication
    # Generate with: python -c "import secrets; print(secrets.token_hex(32))"
    # NOTE: default is for local dev only — set SECRET_KEY in production.
    SECRET_KEY: str = "dev-secret-change-me"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 10080  # 7 days
    AUTH_COOKIE_NAME: str = "access_token"
    COOKIE_SECURE: bool = False
    COOKIE_SAMESITE: str = "lax"
    PASSWORD_RESET_EXPIRE_MINUTES: int = 20
    PASSWORD_RESET_PATH: str = "/reset-password"
    ENABLE_RESET_TOKEN_PREVIEW: bool = False
    FORGOT_PASSWORD_EMAIL_LIMIT_PER_HOUR: int = 5
    FORGOT_PASSWORD_IP_LIMIT_PER_HOUR: int = 20
    RESET_PASSWORD_IP_LIMIT_PER_HOUR: int = 30
    RESET_PASSWORD_TOKEN_LIMIT_PER_HOUR: int = 10

    # AI APIs (optional — chat has a rule-based fallback)
    GROQ_API_KEY: str = ""        # from console.groq.com (free)
    GEMINI_API_KEY: str = ""      # from aistudio.google.com (free)
    OPENAI_API_KEY: str = ""      # optional, for Whisper voice
    OLLAMA_BASE_URL: str = "http://127.0.0.1:11434"
    OLLAMA_MODEL: str = "mistral"
    OLLAMA_TIMEOUT_SECONDS: int = 45
    HF_API_KEY: str = ""
    HF_MODEL: str = "Qwen/Qwen2.5-32B-Instruct"
    HF_TIMEOUT_SECONDS: int = 45
    LLM_ROUTING_MODE: str = "auto"  # auto|cloud_first|local_first|local_only
    LLM_PROVIDER_COOLDOWN_SECONDS: int = 600

    # Startup behavior
    # Preloading embeddings can download large model files on first run.
    PRELOAD_EMBEDDER: bool = False

    # Redis cache (optional — app works without it)
    # Get from: upstash.com (free tier)
    UPSTASH_REDIS_URL: str = ""
    UPSTASH_REDIS_TOKEN: str = ""
    REDIS_URL: str = "redis://localhost:6379/0"

    # Cloudinary file storage (optional)
    # Get from: cloudinary.com (free 25GB)
    CLOUDINARY_CLOUD_NAME: str = ""
    CLOUDINARY_API_KEY: str = ""
    CLOUDINARY_API_SECRET: str = ""

    # SMTP email (optional)
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_EMAIL: str = ""
    SMTP_USE_TLS: bool = True

    @field_validator("DEBUG", mode="before")
    @classmethod
    def parse_debug_flag(cls, value):
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"1", "true", "yes", "on", "debug"}:
                return True
            if normalized in {"0", "false", "no", "off", "release", "prod", "production"}:
                return False
        return value

    class Config:
        env_file = ".env"
        case_sensitive = True

    @field_validator("GROQ_API_KEY", "GEMINI_API_KEY", "OPENAI_API_KEY", mode="before")
    @classmethod
    def normalize_placeholder_keys(cls, value):
        if isinstance(value, str) and value.strip().upper().startswith("CHANGE_ME_"):
            return ""
        return value

    @field_validator("COOKIE_SAMESITE", mode="before")
    @classmethod
    def normalize_cookie_samesite(cls, value):
        if not isinstance(value, str):
            return "lax"
        normalized = value.strip().lower()
        return normalized if normalized in {"lax", "strict", "none"} else "lax"

    @property
    def allowed_origins_list(self) -> List[str]:
        """Parse comma-separated origins into a list"""
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",")]


@lru_cache()
def get_settings() -> Settings:
    """
    Cache settings so we only read .env file once.
    Using lru_cache means the same Settings object is returned every call.
    """
    return Settings()


# This is the settings object used everywhere in the app
settings = get_settings()
