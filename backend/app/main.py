# NirovaAI Backend - Main Application Entry Point

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from app.core.config import settings
from app.core.database import connect_db, disconnect_db
from app.core.redis_client import connect_redis, disconnect_redis
from app.ai.ml.disease_model import load_disease_model
from app.ai.ml.dengue_model import load_dengue_model
from app.ai.vision.skin_model import load_skin_model
from app.ai.rag.embedder import load_embedder

from app.api import auth, symptoms, chat, health, vision

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
    docs_url="/docs",
    redoc_url="/redoc"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_origin_regex=settings.CORS_ORIGIN_REGEX,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.include_router(auth.router)
app.include_router(symptoms.router)
app.include_router(chat.router)
app.include_router(health.router)
app.include_router(vision.router)

@app.get("/", tags=["Status"])
async def home():
    """API welcome endpoint"""
    return {
        "name": "NirovaAI",
        "tagline": "Early Disease Detection for Bangladesh",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
        "health_check": "/health"
    }


@app.get("/health", tags=["Status"])
async def health_check():
    """Health check for deployment (Render, Azure, etc.)"""
    mongo_connected = bool(getattr(app.state, "mongo_connected", False))
    return {
        "status": "healthy",
        "service": "NirovaAI",
        "mode": "normal" if mongo_connected else "degraded",
        "mongo_connected": mongo_connected,
    }

