"""
NirovaAI - MongoDB Database Connection
======================================
We use Motor (async MongoDB driver) so database operations
don't block the FastAPI event loop.

Collections:
- users              -> user accounts
- symptom_logs       -> daily symptom entries
- disease_alerts     -> high-risk alerts for users
- chat_sessions      -> AI conversation history
- knowledge_chunks   -> RAG medical knowledge base
- health_timeline    -> monthly health summaries
- vision_analyses    -> saved AI outputs from skin/lab/prescription scans
- symptom_analyses   -> saved symptom-model outputs for chat grounding
"""

from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import ASCENDING, DESCENDING, IndexModel
from fastapi import HTTPException
from app.core.config import settings
import logging

log = logging.getLogger(__name__)

# Global database client - created once, reused for all requests
client: AsyncIOMotorClient = None
db = None


async def connect_db():
    """Connect to MongoDB Atlas when the server starts"""
    global client, db

    if not settings.MONGODB_URI:
        raise RuntimeError("MONGODB_URI is not set")

    try:
        client_kwargs = {
            "serverSelectionTimeoutMS": 30000,  # 30 seconds
            "connectTimeoutMS": 30000,
            "socketTimeoutMS": 30000,
            "retryWrites": True,
            "w": "majority",
        }

        # Atlas SRV URIs require TLS by default; local mongodb:// typically does not.
        if settings.MONGODB_URI.startswith("mongodb+srv://"):
            client_kwargs["tls"] = True

        # Optional insecure mode for local troubleshooting only.
        if settings.MONGO_INSECURE_TLS:
            client_kwargs["tlsAllowInvalidCertificates"] = True
            client_kwargs["tlsAllowInvalidHostnames"] = True
            log.warning(
                "MONGO_INSECURE_TLS=true: TLS certificate and hostname verification are disabled. "
                "Do not use this setting in production."
            )

        log.info("Connecting to MongoDB...")
        log.info(f"Database: {settings.MONGODB_DB_NAME}")
        log.info(f"Connection timeout: {client_kwargs['serverSelectionTimeoutMS']}ms")

        temp_client = AsyncIOMotorClient(settings.MONGODB_URI, **client_kwargs)
        temp_db = temp_client[settings.MONGODB_DB_NAME]

        # Test the connection with a ping command
        log.info("Testing MongoDB connection with ping...")
        await temp_client.admin.command("ping")

        # Only publish globals after a successful connection check.
        client = temp_client
        db = temp_db
        log.info(f"MongoDB connected successfully: {settings.MONGODB_DB_NAME}")

        # Create indexes for fast queries
        await setup_indexes()

    except Exception as e:
        # Log SSL errors with more detail
        if hasattr(e, "args") and any("SSL" in str(arg) for arg in e.args):
            log.error(f"MongoDB SSL error: {e}")
            log.error(
                "If you are on Windows, try upgrading certifi and Python, "
                "or set MONGO_INSECURE_TLS=true as a last resort."
            )
        client = None
        db = None
        log.error(f"MongoDB connection failed: {e}")
        raise


async def disconnect_db():
    """Close MongoDB connection when server shuts down"""
    global client
    if client:
        client.close()
        log.info("MongoDB disconnected")


async def setup_indexes():
    """
    Create database indexes for performance.
    Without indexes, queries scan every document (slow).
    With indexes, MongoDB finds documents directly (fast).
    """
    try:
        # Users: fast login by email
        await db.users.create_index(
            [("email", ASCENDING)], unique=True
        )

        # Symptom logs: fast history queries by user + date
        await db.symptom_logs.create_indexes([
            IndexModel([("user_id", ASCENDING), ("date", DESCENDING)]),
            IndexModel([("date", DESCENDING)])
        ])

        # Alerts: fast lookup of unresolved alerts
        await db.disease_alerts.create_indexes([
            IndexModel([("user_id", ASCENDING), ("resolved", ASCENDING)]),
            IndexModel([("created_at", DESCENDING)])
        ])

        # Chat history: latest sessions first
        await db.chat_sessions.create_index(
            [("user_id", ASCENDING), ("created_at", DESCENDING)]
        )

        # Vision analysis history: recent per-user lookups and type filters
        await db.vision_analyses.create_indexes([
            IndexModel([("user_id", ASCENDING), ("created_at", DESCENDING)]),
            IndexModel([("analysis_type", ASCENDING), ("created_at", DESCENDING)]),
        ])

        # Symptom analysis history: recent per-user lookups and analyzer mode filters
        await db.symptom_analyses.create_indexes([
            IndexModel([("user_id", ASCENDING), ("created_at", DESCENDING)]),
            IndexModel([("analysis_mode", ASCENDING), ("created_at", DESCENDING)]),
        ])

        # Knowledge base: source lookup for RAG
        await db.knowledge_chunks.create_indexes([
            IndexModel([("source", ASCENDING), ("category", ASCENDING)]),
            IndexModel([("content", "text")]),
        ])

        log.info("Database indexes created")

    except Exception as e:
        if "already exists" not in str(e):
            raise
        log.warning(f"Index setup warning: {e}")


def get_db():
    """Get the database instance - used as a FastAPI dependency"""
    if db is None:
        raise HTTPException(
            status_code=503,
            detail="Database is not connected. Check MONGODB_URI and try again."
        )
    return db


# Shortcut functions so we don't repeat collection names everywhere
def users():
    return get_db().users


def symptom_logs():
    return get_db().symptom_logs


def alerts():
    return get_db().disease_alerts


def chat_sessions():
    return get_db().chat_sessions


def knowledge():
    return get_db().knowledge_chunks


def timeline():
    return get_db().health_timeline


def vision_analyses():
    return get_db().vision_analyses


def symptom_analyses():
    return get_db().symptom_analyses
