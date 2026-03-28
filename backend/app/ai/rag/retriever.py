"""
NirovaAI - Hybrid RAG Retriever
================================
Retrieval strategy:
1) Mongo text search (fast lexical relevance)
2) Optional semantic rerank using local embeddings
3) Confidence scoring + compact grounded context assembly
"""

from __future__ import annotations

from typing import Any, Dict, List, Tuple
import logging
import math
import re

from app.core.database import knowledge
from app.ai.rag.embedder import embed_text

log = logging.getLogger(__name__)


def _tokenize(text: str) -> List[str]:
    return re.findall(r"[a-zA-Z0-9\u0980-\u09FF]+", (text or "").lower())


def _keyword_overlap_score(query: str, text: str) -> float:
    q = set(_tokenize(query))
    if not q:
        return 0.0
    t = set(_tokenize(text))
    if not t:
        return 0.0
    overlap = len(q & t)
    return overlap / max(1, len(q))


def _cosine(a: List[float], b: List[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = 0.0
    na = 0.0
    nb = 0.0
    for x, y in zip(a, b):
        dot += x * y
        na += x * x
        nb += y * y
    if na <= 0.0 or nb <= 0.0:
        return 0.0
    return dot / (math.sqrt(na) * math.sqrt(nb))


def _band(score: float) -> str:
    if score >= 0.70:
        return "high"
    if score >= 0.45:
        return "medium"
    return "low"


async def retrieve_knowledge(
    query: str,
    *,
    top_k: int = 4,
    candidate_limit: int = 30,
) -> Tuple[List[Dict[str, Any]], bool]:
    """
    Return top retrieved knowledge docs and whether external knowledge is strong enough.
    """
    query = (query or "").strip()
    if not query:
        return [], False

    candidates: Dict[str, Dict[str, Any]] = {}

    # 1) Lexical candidate generation (text search).
    try:
        text_hits: List[Dict[str, Any]] = []
        cursor = knowledge().find(
            {"$text": {"$search": query}},
            {
                "content": 1,
                "source": 1,
                "category": 1,
                "embedding": 1,
                "_id": 0,
                "text_score": {"$meta": "textScore"},
            },
        ).limit(candidate_limit)

        async for doc in cursor:
            text_hits.append(doc)

        text_hits.sort(key=lambda d: float(d.get("text_score", 0.0)), reverse=True)
        for doc in text_hits:
            key = f"{doc.get('source','')}|{doc.get('category','')}|{hash(doc.get('content',''))}"
            candidates[key] = doc
    except Exception as exc:
        # Keep service resilient when text index is missing or query parser fails.
        log.warning(f"RAG text search unavailable: {exc}")

    # 2) Fallback candidate generation if text search produced nothing.
    if not candidates:
        try:
            # Sample a bounded window of docs and score overlap.
            cursor = knowledge().find(
                {},
                {"content": 1, "source": 1, "category": 1, "embedding": 1, "_id": 0},
            ).limit(candidate_limit)
            async for doc in cursor:
                key = f"{doc.get('source','')}|{doc.get('category','')}|{hash(doc.get('content',''))}"
                candidates[key] = doc
        except Exception as exc:
            log.warning(f"RAG fallback candidate fetch failed: {exc}")
            return [], False

    # 3) Semantic rerank when embedder is available.
    query_vec: List[float] = []
    try:
        query_vec = embed_text(query)
    except Exception:
        query_vec = []

    scored: List[Dict[str, Any]] = []
    for doc in candidates.values():
        content = doc.get("content", "")
        text_score = float(doc.get("text_score", 0.0))
        overlap = _keyword_overlap_score(query, content)
        sem = 0.0
        emb = doc.get("embedding")
        if query_vec and isinstance(emb, list) and emb:
            sem = _cosine(query_vec, emb)

        # Hybrid score - semantic dominant, lexical as backstop.
        hybrid = (0.60 * sem) + (0.25 * overlap) + (0.15 * min(text_score / 10.0, 1.0))
        scored.append(
            {
                "content": content,
                "source": doc.get("source") or "Medical Reference",
                "category": doc.get("category") or "general",
                "score": round(hybrid, 4),
                "confidence": _band(hybrid),
            }
        )

    scored.sort(key=lambda x: x["score"], reverse=True)
    top = scored[:top_k]

    # Evidence is considered strong if we have at least one medium+ chunk.
    has_strong_external = any(d["score"] >= 0.45 for d in top)
    return top, has_strong_external


def build_knowledge_context(docs: List[Dict[str, Any]], *, max_chars: int = 2600) -> str:
    """Build compact citation-friendly knowledge block for the prompt."""
    if not docs:
        return "No external guideline evidence retrieved for this question."

    lines: List[str] = []
    used = 0
    for idx, doc in enumerate(docs, start=1):
        source = doc.get("source", "Medical Reference")
        category = doc.get("category", "general")
        conf = doc.get("confidence", "low")
        content = (doc.get("content") or "").strip().replace("\n", " ")
        entry = f"[KB{idx}] ({conf}) {source} | {category}: {content}"
        if used + len(entry) > max_chars:
            break
        lines.append(entry)
        used += len(entry) + 1

    return "\n".join(lines) if lines else "No external guideline evidence retrieved for this question."
