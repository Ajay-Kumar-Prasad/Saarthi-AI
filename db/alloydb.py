"""
Production AlloyDB async access layer.

Supports:
- IAM auth via AlloyDB connector (preferred)
- Direct host/port auth fallback
- Async connection pooling
- Retry for transient connection failures
"""

import asyncio
import logging
import os
from typing import Any

import asyncpg
from google.auth import default
from google.cloud.alloydb.connector import AsyncConnector

logger = logging.getLogger(__name__)

_connector: AsyncConnector | None = None
_pool: asyncpg.Pool | None = None
_pool_lock = asyncio.Lock()

_TRANSIENT_ERRORS = (
    asyncpg.PostgresConnectionError,
    asyncpg.CannotConnectNowError,
    asyncpg.ConnectionDoesNotExistError,
    OSError,
    TimeoutError,
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


def _env(name: str, default_value: str = "") -> str:
    return os.getenv(name, default_value).strip()


async def _with_retries(coro_factory, operation: str, attempts: int = 3):
    delay = 0.5
    last_exc: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            return await coro_factory()
        except _TRANSIENT_ERRORS as exc:
            last_exc = exc
            logger.warning(
                "Transient DB error during %s (attempt=%d/%d): %s",
                operation,
                attempt,
                attempts,
                exc,
            )
            if attempt < attempts:
                await asyncio.sleep(delay)
                delay *= 2
        except Exception:
            logger.exception("Non-transient DB error during %s", operation)
            raise
    raise RuntimeError(f"{operation} failed after {attempts} attempts: {last_exc}")


async def _get_connector() -> AsyncConnector:
    global _connector
    if _connector is None:
        credentials, _ = default()
        _connector = AsyncConnector(credentials=credentials)
        logger.info("Initialized AlloyDB async connector with IAM credentials.")
    return _connector


def _use_iam_mode() -> bool:
    return bool(_env("ALLOYDB_INSTANCE_URI") and _env("ALLOYDB_DB") and _env("ALLOYDB_IAM_USER"))


async def _connect_via_iam() -> asyncpg.Connection:
    connector = await _get_connector()
    instance_uri = _env("ALLOYDB_INSTANCE_URI")
    database = _env("ALLOYDB_DB")
    iam_user = _env("ALLOYDB_IAM_USER")
    if not (instance_uri and database and iam_user):
        raise RuntimeError("Missing IAM DB configuration: ALLOYDB_INSTANCE_URI/ALLOYDB_DB/ALLOYDB_IAM_USER")

    return await connector.connect(
        instance_uri,
        "asyncpg",
        user=iam_user,
        db=database,
        enable_iam_auth=True,
    )


async def _connect_direct() -> asyncpg.Connection:
    host = _env("DB_HOST")
    port = int(_env("DB_PORT", "5432"))
    user = _env("DB_USER")
    password = _env("DB_PASS")
    database = _env("DB_NAME")
    ssl_mode = _env("DB_SSL", "false").lower() == "true"

    if not all([host, user, database]):
        raise RuntimeError("Missing direct DB configuration: DB_HOST/DB_USER/DB_NAME")

    return await asyncpg.connect(
        host=host,
        port=port,
        user=user,
        password=password,
        database=database,
        ssl=ssl_mode,
    )


async def _create_pool() -> asyncpg.Pool:
    async def _connect(*args, **kwargs):
        if _use_iam_mode():
            return await _connect_via_iam()
        return await _connect_direct()

    logger.info("Creating AlloyDB pool (mode=%s)", "iam" if _use_iam_mode() else "direct")
    return await asyncpg.create_pool(
        min_size=int(_env("DB_POOL_MIN_SIZE", "1")),
        max_size=int(_env("DB_POOL_MAX_SIZE", "10")),
        max_inactive_connection_lifetime=float(_env("DB_POOL_MAX_IDLE_SECONDS", "300")),
        timeout=float(_env("DB_POOL_ACQUIRE_TIMEOUT_SECONDS", "10")),
        init=lambda conn: conn.execute("SET TIME ZONE 'UTC'"),
        connect=_connect,
    )


async def _get_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        async with _pool_lock:
            if _pool is None:
                _pool = await _with_retries(_create_pool, "create_db_pool")
    return _pool


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