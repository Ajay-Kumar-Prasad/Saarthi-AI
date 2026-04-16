"""
Production AlloyDB async access layer.

Supports one explicit connection mode at a time:
- IAM auth via AlloyDB connector
- Direct host/port auth (proxy/private-ip compatible)
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Awaitable, Callable

import asyncpg

from core.config import get_db_settings

logger = logging.getLogger(__name__)

_pool: asyncpg.Pool | None = None
_pool_lock = asyncio.Lock()

_TRANSIENT_ERRORS = (
    asyncpg.PostgresConnectionError,
    asyncpg.CannotConnectNowError,
    asyncpg.ConnectionDoesNotExistError,
    asyncpg.TooManyConnectionsError,
    OSError,
    TimeoutError,
    asyncio.TimeoutError,
)

_AUTH_ERRORS = (
    asyncpg.InvalidAuthorizationSpecificationError,
    asyncpg.InvalidPasswordError,
)


class _ConnectionProxy:
    """Wrap pooled connection and release on close()."""

    def __init__(self, pool: asyncpg.Pool, conn: asyncpg.Connection):
        self._pool = pool
        self._conn = conn
        self._closed = False

    def __getattr__(self, item: str) -> Any:
        return getattr(self._conn, item)

    async def close(self) -> None:
        if not self._closed:
            self._closed = True
            await self._pool.release(self._conn)


def _classify_db_error(exc: Exception) -> str:
    if isinstance(exc, (TimeoutError, asyncio.TimeoutError)):
        return "timeout"
    if isinstance(exc, _AUTH_ERRORS):
        return "auth"
    if isinstance(exc, OSError):
        return "network"
    return "unknown"


async def _with_retries(
    coro_factory: Callable[[], Awaitable[Any]],
    operation: str,
    attempts: int | None = None,
):
    settings = get_db_settings()
    max_attempts = attempts or settings.db_retry_attempts
    delay = 0.5
    last_exc: Exception | None = None

    for attempt in range(1, max_attempts + 1):
        try:
            return await coro_factory()
        except _AUTH_ERRORS as exc:
            logger.exception(
                "DB auth failure during %s (attempt=%d/%d, class=%s)",
                operation,
                attempt,
                max_attempts,
                _classify_db_error(exc),
            )
            raise
        except _TRANSIENT_ERRORS as exc:
            last_exc = exc
            logger.warning(
                "Transient DB error during %s (attempt=%d/%d, class=%s): %s",
                operation,
                attempt,
                max_attempts,
                _classify_db_error(exc),
                exc,
            )
            if attempt < max_attempts:
                await asyncio.sleep(delay)
                delay *= 2
        except Exception as exc:
            logger.exception(
                "Non-transient DB error during %s (class=%s)",
                operation,
                _classify_db_error(exc),
            )
            raise

    logger.error(
        "DB operation failed after retries operation=%s attempts=%d class=%s error=%s",
        operation,
        max_attempts,
        _classify_db_error(last_exc) if last_exc else "unknown",
        last_exc,
    )
    raise RuntimeError(f"{operation} failed after {max_attempts} attempts: {last_exc}")


async def _connect_direct() -> asyncpg.Connection:
    settings = get_db_settings()
    if settings.debug:
        logger.info(
            "Attempting direct DB connection host=%s port=%d db=%s user=%s ssl=%s",
            settings.db_host,
            settings.db_port,
            settings.db_name,
            settings.db_user,
            settings.db_ssl,
        )

    try:
        return await asyncpg.connect(
            host=settings.db_host,
            port=settings.db_port,
            user=settings.db_user,
            password=settings.db_pass,
            database=settings.db_name,
            ssl=settings.db_ssl,
            timeout=settings.db_connect_timeout_seconds,
        )
    except Exception:
        logger.exception("Direct DB connection failed.")
        raise


async def _create_pool() -> asyncpg.Pool:
    settings = get_db_settings()
    settings.validate_for_startup()

    async def _connect(*args, **kwargs):
        del args, kwargs
        return await _connect_direct()

    logger.info(
        "Creating AlloyDB pool min_size=%d max_size=%d acquire_timeout=%.2fs",
        settings.db_pool_min_size,
        settings.db_pool_max_size,
        settings.db_pool_acquire_timeout_seconds,
    )
    return await asyncpg.create_pool(
        min_size=settings.db_pool_min_size,
        max_size=settings.db_pool_max_size,
        max_inactive_connection_lifetime=settings.db_pool_max_idle_seconds,
        timeout=settings.db_pool_acquire_timeout_seconds,
        init=lambda conn: conn.execute("SET TIME ZONE 'UTC'"),
        connect=_connect,
    )


async def _get_pool() -> asyncpg.Pool:
    global _pool
    if _pool is not None:
        return _pool

    async with _pool_lock:
        if _pool is None:
            _pool = await _with_retries(_create_pool, "create_db_pool")
    return _pool


async def init_pool() -> None:
    await _get_pool()


async def get_connection() -> asyncpg.Connection:
    """
    Returns a pooled connection proxy.
    Callers should still use `await conn.close()`; it releases back to pool.
    """
    pool = await _get_pool()
    conn = await _with_retries(pool.acquire, "acquire_connection")
    return _ConnectionProxy(pool, conn)  # type: ignore[return-value]


def _validate_generated_sql(sql: str) -> None:
    lowered = (sql or "").strip().lower()
    if not lowered:
        raise ValueError("Generated SQL is empty.")
    if ";" in lowered:
        raise ValueError("Generated SQL contains multiple statements.")
    if not (lowered.startswith("select") or lowered.startswith("with")):
        raise ValueError("Only SELECT/WITH queries are allowed for NL query execution.")
    blocked = ("insert ", "update ", "delete ", "drop ", "alter ", "truncate ", "grant ", "revoke ")
    if any(token in lowered for token in blocked):
        raise ValueError("Generated SQL contains unsafe operation.")


async def query_nl(natural_language_query: str, user_id: str) -> dict:
    if not isinstance(natural_language_query, str) or not natural_language_query.strip():
        return {"natural_language_query": natural_language_query, "generated_sql": None, "results": [], "error": "Query is required."}
    if not isinstance(user_id, str) or not user_id.strip():
        return {"natural_language_query": natural_language_query, "generated_sql": None, "results": [], "error": "user_id is required."}

    conn = await get_connection()
    try:
        prompt = f"For user_id={user_id.strip()}, {natural_language_query.strip()}"
        nl_result = await _with_retries(
            lambda: conn.fetch("SELECT google_ml.nl_to_sql($1, 'saarthi_schema')", prompt),
            "nl_to_sql_generation",
        )
        generated_sql = nl_result[0][0] if nl_result else ""
        _validate_generated_sql(generated_sql)
        logger.info("AlloyDB NL-to-SQL generated query for user_id=%s", user_id)

        data = await _with_retries(lambda: conn.fetch(generated_sql), "nl_sql_execution")
        return {
            "natural_language_query": natural_language_query,
            "generated_sql": generated_sql,
            "results": [dict(r) for r in data],
            "row_count": len(data),
        }
    except Exception as exc:
        logger.exception("AlloyDB NL query failed for user_id=%s", user_id)
        return {
            "natural_language_query": natural_language_query,
            "generated_sql": None,
            "results": [],
            "error": f"Failed to execute natural language query: {exc}",
        }
    finally:
        await conn.close()


async def close_pool() -> None:
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None
        logger.info("AlloyDB pool closed.")


async def close_connector() -> None:
    # Deprecated: IAM connector no longer in use
    pass

