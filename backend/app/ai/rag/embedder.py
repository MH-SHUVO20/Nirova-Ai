"""
NirovaAI — Text Embedder
=========================
Converts text into vectors for semantic search.
Runs locally — no API key needed, no cost.
Supports both Bangla and English (multilingual model).
"""

from sentence_transformers import SentenceTransformer
from typing import List
import logging

log = logging.getLogger(__name__)

_model = None


def load_embedder():
    """Load the multilingual embedding model"""
    global _model
    log.info("Loading multilingual embedding model (~120MB, first time only)...")
    _model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
    log.info("✅ Embedder loaded — supports Bangla + English (384 dimensions)")


def embed_text(text: str) -> List[float]:
    """Convert a single text to a 384-dim embedding vector"""
    if not _model:
        raise RuntimeError("Embedder not loaded. Call load_embedder() first.")
    return _model.encode(text, normalize_embeddings=True).tolist()


def embed_batch(texts: List[str]) -> List[List[float]]:
    """Convert multiple texts to embeddings — faster than one by one"""
    if not _model:
        raise RuntimeError("Embedder not loaded. Call load_embedder() first.")
    return _model.encode(
        texts,
        normalize_embeddings=True,
        batch_size=32,
        show_progress_bar=True
    ).tolist()
