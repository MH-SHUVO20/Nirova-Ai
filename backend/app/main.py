# NirovaAI Backend - Main Application Entry Point

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging
import time

from app.core.config import settings
from app.core.database import connect_db, disconnect_db
from app.core.redis_client import connect_redis, disconnect_redis
from app.ai.ml.disease_model import load_disease_model
from app.ai.ml.dengue_model import load_dengue_model
from app.ai.vision.skin_model import load_skin_model
from app.ai.rag.embedder import load_embedder
from app.core.errors import (
    NirovaError,
    RequestLogger,
    http_exception,
    DatabaseError,
    AIProviderError,
)

from app.api import auth, symptoms, chat, health, vision, language, analytics

from app.core.rate_limit import limiter
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)
log = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize database and AI models on startup, cleanup on shutdown
    log.info("=" * 50)
    log.info("NirovaAI starting up...")
    log.info("=" * 50)

    app.state.mongo_connected = False

    if settings.SECRET_KEY == "dev-secret-change-me":
        log.warning("SECRET_KEY is using the default dev value; set SECRET_KEY in .env for production.")
    elif len(settings.SECRET_KEY) < 32:
        log.warning("SECRET_KEY appears weak (length < 32). Use a longer random secret in production.")

    if settings.FRONTEND_URL.lower().startswith("https://") and not settings.COOKIE_SECURE:
        log.warning("FRONTEND_URL is HTTPS but COOKIE_SECURE is false; secure cookies are recommended in production.")

    if not settings.MONGODB_URI:
        log.warning("MONGODB_URI is not set; the API will run in degraded mode (DB-backed features disabled).")

    log.info(
        f"LLM routing mode: {settings.LLM_ROUTING_MODE} | "
        f"Provider order: Groq -> Gemini -> HuggingFace({settings.HF_MODEL})"
    )

    log.info("Connecting to MongoDB...")
    try:
        await connect_db()
        app.state.mongo_connected = True
        log.info("✅ MongoDB connected")
    except Exception as e:
        log.warning(f"MongoDB unavailable: {e} — running in degraded mode")

    log.info("Connecting to Redis...")
    await connect_redis()

    log.info("Loading AI models...")

    try:
        load_disease_model()
        log.info("✅ Disease classifier loaded")
    except Exception as e:
        log.warning(f"Disease model failed: {e}")

    try:
        load_dengue_model()
        log.info("✅ Dengue classifier loaded")
    except Exception as e:
        log.warning(f"Dengue model failed: {e}")

    try:
        load_skin_model()
        log.info("✅ Skin analyzer ready (using Gemini Vision)")
    except Exception as e:
        log.warning(f"Skin model failed: {e}")

    if settings.PRELOAD_EMBEDDER:
        try:
            load_embedder()
            log.info("✅ Embedding model loaded")
        except Exception as e:
            log.warning(f"Embedder not loaded: {e}")
    else:
        log.info("Embedder preload disabled")

    log.info("=" * 50)
    log.info("✅ NirovaAI is ready!")
    log.info("=" * 50)

    yield

    log.info("NirovaAI shutting down...")
    if app.state.mongo_connected:
        await disconnect_db()
    await disconnect_redis()
    log.info("Goodbye!")


# Create the FastAPI app
app = FastAPI(
    title="NirovaAI — নিরোভা",
    description="""
## Early Disease Detection for Bangladesh

NirovaAI helps patients understand their health by tracking symptoms and detecting disease patterns early.

### AI Models
- **Disease Classifier**: 41 diseases, 131 symptoms
- **Dengue Detector**: real BD hospital data
- **Skin Analyzer**: Gemini Vision-based analysis
- **RAG Chat**: LangChain + Groq LLM for medical Q&A

### Disclaimer
This service is for informational support only and does not replace professional medical consultation, diagnosis, or treatment.
    """,
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Requested-With"],
)

# ── Security Headers Middleware ──
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    """Add security headers to all responses."""
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    if settings.COOKIE_SECURE:
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response

# ── Structured Request/Response Logging Middleware ──
@app.middleware("http")
async def add_request_logging_middleware(request: Request, call_next):
    """Log all requests and responses with timing."""
    start_time = time.time()
    user_id = None
    
    # Try to extract user ID from token
    try:
        from app.core.auth import decode_token
        token = request.cookies.get(settings.AUTH_COOKIE_NAME)
        if token:
            payload = decode_token(token)
            user_id = payload.get("sub")
    except Exception:
        pass  # User not authenticated, that's OK
    
    # Log incoming request
    RequestLogger.log_request(
        method=request.method,
        path=request.url.path,
        user_id=user_id,
    )
    
    try:
        response = await call_next(request)
        duration_ms = (time.time() - start_time) * 1000
        
        # Log response
        RequestLogger.log_response(
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=duration_ms,
            user_id=user_id,
        )
        
        return response
    except Exception as exc:
        duration_ms = (time.time() - start_time) * 1000
        log.error(f"Unhandled exception after {duration_ms:.1f}ms: {exc}")
        raise

# Exception handlers for custom errors
@app.exception_handler(NirovaError)
async def nirova_error_handler(request: Request, exc: NirovaError):
    """Handle all NirovaAI custom errors."""
    RequestLogger.log_error(exc, request.url.path)
    return JSONResponse(
        status_code=exc.http_status,
        content={"error": True, "code": exc.error_code, "message": exc.user_message},
    )

app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


# ── Keep these routes BEFORE static files ──
@app.get("/health", tags=["Status"])
async def health_check():
    mongo_connected = bool(getattr(app.state, "mongo_connected", False))
    return {
        "status": "healthy",
        "service": "NirovaAI",
        "mode": "normal" if mongo_connected else "degraded",
        "mongo_connected": mongo_connected,
    }

# ── Routers with /api prefix ──
app.include_router(auth.router, prefix="/api")
app.include_router(symptoms.router, prefix="/api")
app.include_router(chat.router, prefix="/api")
app.include_router(health.router, prefix="/api")
app.include_router(vision.router, prefix="/api")
app.include_router(language.router, prefix="/api")
app.include_router(analytics.router, prefix="/api")

# ── Serve React Frontend — MUST BE LAST ──
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

if os.path.exists("static"):
    # Serve static assets (JS, CSS, images)
    app.mount("/assets", StaticFiles(directory="static/assets"), name="assets")

    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        # Let API and docs routes pass through
        skip_exact = ["docs", "redoc", "openapi.json", "health"]
        skip_prefix = ["api/"]
        if full_path in skip_exact or any(full_path.startswith(s) for s in skip_prefix):
            from fastapi import HTTPException
            raise HTTPException(status_code=404)
        # Prevent path traversal — reject anything with '..' or absolute paths
        if ".." in full_path or full_path.startswith("/"):
            from fastapi import HTTPException
            raise HTTPException(status_code=400)
        return FileResponse("static/index.html")

