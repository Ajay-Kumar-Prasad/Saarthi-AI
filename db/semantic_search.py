"""
Semantic search layer for life_logs using pgvector.

This module provides:
- Embedding generation with graceful fallback error handling
- Parameterized pgvector insert/search queries
- Retry for transient API/DB failures
- Structured, agent-friendly result payloads
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Any

from db.alloydb import get_connection

logger = logging.getLogger(__name__)

DEFAULT_EMBED_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-004")
DEFAULT_TOP_K = int(os.getenv("SEMANTIC_TOP_K", "8"))
DEFAULT_MIN_SIMILARITY = float(os.getenv("SEMANTIC_MIN_SIMILARITY", "0.55"))
VECTOR_DIM = int(os.getenv("SEMANTIC_VECTOR_DIM", "768"))

_TRANSIENT_ERRORS = (TimeoutError, OSError, ConnectionError)


def _vector_literal(values: list[float]) -> str:
    return "[" + ",".join(f"{v:.8f}" for v in values) + "]"


def _validate_user_id(user_id: str) -> None:
    if not isinstance(user_id, str) or not user_id.strip():
        raise ValueError("user_id is required.")


def _validate_text(name: str, value: str, min_len: int = 1) -> None:
    if not isinstance(value, str) or len(value.strip()) < min_len:
        raise ValueError(f"{name} is required and must be at least {min_len} character(s).")


async def _with_retries(coro_factory, operation: str, attempts: int = 3):
    delay = 0.35
    last_exc: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            return await coro_factory()
        except _TRANSIENT_ERRORS as exc:
            last_exc = exc
            logger.warning(
                "Transient failure in %s attempt=%d/%d error=%s",
                operation,
                attempt,
                attempts,
                exc,
            )
            if attempt < attempts:
                await asyncio.sleep(delay)
                delay *= 2
        except Exception:
            logger.exception("Non-transient failure in %s", operation)
            raise
    raise RuntimeError(f"{operation} failed after {attempts} attempts: {last_exc}")


async def generate_embedding(text: str, model: str = DEFAULT_EMBED_MODEL) -> list[float]:
    """
    Generate embedding values for text.

    Returns a list[float] of length VECTOR_DIM (default 768).
    Raises RuntimeError with meaningful detail on failure.
    """
    _validate_text("text", text, min_len=3)

    try:
        from google import genai
    except Exception as exc:
        raise RuntimeError(f"Embedding dependency unavailable (google-genai): {exc}") from exc

    def _extract_values(response: Any) -> list[float]:
        embeddings = getattr(response, "embeddings", None)
        if embeddings and len(embeddings) > 0:
            first = embeddings[0]
            values = getattr(first, "values", None)
            if values:
                return [float(v) for v in values]
        raise RuntimeError("Embedding response did not include vector values.")

    async def _call_embed():
        # Client call is sync; run in thread to keep FastAPI event loop responsive.
        def _sync_call():
            client = genai.Client()
            return client.models.embed_content(model=model, contents=[text])

        response = await asyncio.to_thread(_sync_call)
        values = _extract_values(response)
        if len(values) != VECTOR_DIM:
            logger.warning(
                "Unexpected embedding dimension expected=%d actual=%d",
                VECTOR_DIM,
                len(values),
            )
        return values

    try:
        return await _with_retries(_call_embed, "generate_embedding")
    except Exception as exc:
        logger.exception("Embedding generation failed")
        raise RuntimeError(f"Failed to generate embedding: {exc}") from exc


async def ensure_semantic_indexes() -> None:
    """Best-effort index setup for semantic search performance."""
    conn = await get_connection()
    try:
        await conn.execute(
            """
            CREATE INDEX IF NOT EXISTS life_logs_user_logged_idx
            ON life_logs (user_id, logged_at DESC)
            """
        )
        await conn.execute("ANALYZE life_logs")
        logger.info("Semantic search indexes ensured and analyzed.")
    except Exception:
        logger.exception("Failed to ensure semantic indexes")
        raise
    finally:
        await conn.close()


async def index_life_log(
    user_id: str,
    domain: str,
    entry: str,
    mood: int | None = None,
) -> dict[str, Any]:
    """
    Insert a life_log record with embedding.
    """
    _validate_user_id(user_id)
    _validate_text("domain", domain)
    _validate_text("entry", entry, min_len=3)
    if mood is not None and not (1 <= int(mood) <= 10):
        raise ValueError("mood must be between 1 and 10.")

    embedding = await generate_embedding(entry)
    vector = _vector_literal(embedding)

    conn = await get_connection()
    try:
        row = await _with_retries(
            lambda: conn.fetchrow(
                """
                INSERT INTO life_logs (user_id, domain, entry, mood, embedding)
                VALUES ($1, $2, $3, $4, $5::vector)
                RETURNING id, user_id, domain, entry, mood, logged_at
                """,
                user_id.strip(),
                domain.strip().lower(),
                entry.strip(),
                mood,
                vector,
            ),
            "index_life_log",
        )
        return {"status": "ok", "record": dict(row) if row else None}
    except Exception as exc:
        logger.exception("Failed to index life log for user_id=%s", user_id)
        return {"status": "error", "error": f"Failed to index life log: {exc}", "record": None}
    finally:
        await conn.close()


async def semantic_search_life_logs(
    user_id: str,
    query: str,
    domain: str | None = None,
    top_k: int = DEFAULT_TOP_K,
    min_similarity: float = DEFAULT_MIN_SIMILARITY,
) -> dict[str, Any]:
    """
    Semantic retrieval over life_logs with pgvector cosine distance.

    Returns:
    {
      "status": "ok" | "error",
      "query": str,
      "matches": [{id, domain, entry, mood, logged_at, similarity}],
      "count": int,
      "error": str | None
    }
    """
    _validate_user_id(user_id)
    _validate_text("query", query, min_len=2)
    if top_k < 1 or top_k > 50:
        raise ValueError("top_k must be between 1 and 50.")
    if min_similarity < 0 or min_similarity > 1:
        raise ValueError("min_similarity must be between 0 and 1.")

    try:
        query_embedding = await generate_embedding(query)
    except Exception as exc:
        return {
            "status": "error",
            "query": query,
            "matches": [],
            "count": 0,
            "error": f"Embedding generation failed: {exc}",
        }

    vector = _vector_literal(query_embedding)
    conn = await get_connection()
    try:
        # Hint ivfflat to probe more lists for quality while still avoiding full scans.
        await conn.execute("SET LOCAL ivfflat.probes = 10")
        rows = await _with_retries(
            lambda: conn.fetch(
                """
                SELECT
                    id,
                    domain,
                    entry,
                    mood,
                    logged_at,
                    1 - (embedding <=> $1::vector) AS similarity
                FROM life_logs
                WHERE user_id = $2
                  AND embedding IS NOT NULL
                  AND ($3::text IS NULL OR domain = $3)
                ORDER BY embedding <=> $1::vector
                LIMIT $4
                """,
                vector,
                user_id.strip(),
                domain.strip().lower() if isinstance(domain, str) and domain.strip() else None,
                top_k,
            ),
            "semantic_search_life_logs",
        )

        matches = []
        for r in rows:
            similarity = float(r["similarity"] or 0.0)
            if similarity < min_similarity:
                continue
            matches.append(
                {
                    "id": str(r["id"]),
                    "domain": r["domain"],
                    "entry": r["entry"],
                    "mood": r["mood"],
                    "logged_at": r["logged_at"].isoformat() if r["logged_at"] else None,
                    "similarity": round(similarity, 4),
                }
            )

        return {
            "status": "ok",
            "query": query,
            "matches": matches,
            "count": len(matches),
            "error": None,
        }
    except Exception as exc:
        logger.exception("Semantic search failed user_id=%s", user_id)
        return {
            "status": "error",
            "query": query,
            "matches": [],
            "count": 0,
            "error": f"Semantic search failed: {exc}",
        }
    finally:
        await conn.close()
