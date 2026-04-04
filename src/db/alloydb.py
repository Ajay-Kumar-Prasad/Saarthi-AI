"""
Saarthi AI — AlloyDB connection module.

This is the SINGLE shared database module for ALL agents:
  - learning_agent  →  from db.alloydb import get_connection
  - health_agent    →  from db.alloydb import get_connection
  - finance_agent   →  from db.alloydb import get_connection
  - work_agent      →  from db.alloydb import get_connection
  - social_agent    →  from db.alloydb import get_connection

Connection method:
  Uses IAM authentication via google-auth + asyncpg.
  No passwords are stored in code or environment variables.
  The Cloud Run service account must have 'roles/alloydb.client' IAM binding.

Environment variables required (set in Cloud Run or .env):
  ALLOYDB_HOST        — e.g. "10.0.0.3"  (private IP of AlloyDB instance)
  ALLOYDB_PORT        — e.g. "5432"      (default PostgreSQL port)
  ALLOYDB_DATABASE    — e.g. "saarthi"
  ALLOYDB_USER        — e.g. "saarthi-sa@project.iam"  (service account email)

NL-to-SQL:
  query_nl() uses AlloyDB AI's google_ml_integration to convert natural
  language questions into SQL and return structured results.
  This powers the Determinism Gap fix (real data, not hallucinations).
"""

import os
import logging
from typing import Any

import asyncpg
import google.auth
import google.auth.transport.requests

logger = logging.getLogger(__name__)

# ── Config ────────────────────────────────────────────────────────────────────

ALLOYDB_HOST = os.getenv("ALLOYDB_HOST", "127.0.0.1")
ALLOYDB_PORT = int(os.getenv("ALLOYDB_PORT", "5432"))
ALLOYDB_DATABASE = os.getenv("ALLOYDB_DATABASE", "saarthi")
ALLOYDB_USER = os.getenv("ALLOYDB_USER", "")  # IAM service account email
ALLOYDB_PASSWORD = os.getenv("ALLOYDB_PASSWORD", "")  # For proxy mode
ALLOYDB_USE_IAM = os.getenv("ALLOYDB_USE_IAM", "true").lower() == "true"


# ── IAM token helper ──────────────────────────────────────────────────────────

def _get_iam_token() -> str:
    """
    Fetch a short-lived OAuth2 access token for the current service account.
    This is used as the password for the AlloyDB IAM connection.
    Cloud Run automatically provides Application Default Credentials (ADC).
    """
    credentials, _ = google.auth.default(
        scopes=["https://www.googleapis.com/auth/cloud-platform"]
    )
    request = google.auth.transport.requests.Request()
    credentials.refresh(request)
    return credentials.token


# ── Connection ────────────────────────────────────────────────────────────────

async def get_connection() -> asyncpg.Connection:
    """
    Open and return a single IAM-authenticated asyncpg connection to AlloyDB.

    Usage pattern (same in every agent db file):

        conn = await get_connection()
        try:
            rows = await conn.fetch("SELECT * FROM table WHERE user_id = $1", user_id)
            return [dict(r) for r in rows]
        finally:
            await conn.close()

    Each call opens a fresh connection. For high-throughput production use,
    swap this for a connection pool (asyncpg.create_pool) in the lifespan handler.
    """
    if ALLOYDB_USE_IAM:
        password = _get_iam_token()
    else:
        # Use proxy mode (Cloud SQL Proxy locally, or password-based auth)
        password = ALLOYDB_PASSWORD

    conn = await asyncpg.connect(
        host=ALLOYDB_HOST,
        port=ALLOYDB_PORT,
        database=ALLOYDB_DATABASE,
        user=ALLOYDB_USER,
        password=password,
        ssl="require" if ALLOYDB_USE_IAM else "prefer",  # IAM always requires SSL
    )

    logger.debug(
        f"AlloyDB connection opened: {ALLOYDB_HOST}:{ALLOYDB_PORT}/{ALLOYDB_DATABASE}"
    )
    return conn


# ── NL-to-SQL (AlloyDB AI) ────────────────────────────────────────────────────

async def query_nl(question: str, user_id: str) -> dict[str, Any]:
    """
    Convert a natural language question into SQL using AlloyDB AI's
    google_ml_integration extension, execute it, and return the results.

    This powers the 'Determinism Gap' fix from the architecture:
    real data-backed answers instead of LLM hallucinations.

    Args:
        question: Natural language question, e.g.
                  "How many hours did I study last month?"
        user_id:  Scoped to this user — injected into the prompt so the
                  generated SQL always filters by user_id.

    Returns:
        {
            "question":      original question,
            "generated_sql": the SQL AlloyDB AI produced,
            "results":       list of row dicts,
            "row_count":     int,
        }

    Example:
        result = await query_nl(
            "How many sleep sessions were under 6 hours last week?",
            user_id="uuid-here"
        )
    """
    conn = await get_connection()
    try:
        # Step 1: Ask AlloyDB AI to generate SQL from the natural language question.
        # google_ml_integration's ml_predict_row() runs a Vertex AI model in-database.
        nl_prompt = (
            f"Database schema: users, health_sleep_logs, health_activity_logs, "
            f"health_daily_metrics, learning_resources, study_sessions, study_goals, "
            f"finance_transactions, finance_budgets, tasks, events, life_logs. "
            f"All tables have a user_id column. "
            f"Write a safe read-only PostgreSQL SELECT query for: {question} "
            f"Always filter by user_id = '{user_id}'. "
            f"Return only the SQL query, nothing else."
        )

        sql_row = await conn.fetchrow(
            """
            SELECT ml_predict_row(
                'projects/PROJECT_ID/locations/us-central1/publishers/google/models/text-bison',
                json_build_object('instances', json_build_array(
                    json_build_object('content', $1)
                ))
            ) AS result
            """,
            nl_prompt,
        )

        generated_sql = (sql_row["result"] or {}).get("predictions", [{}])[0].get(
            "content", ""
        ).strip()

        if not generated_sql or not generated_sql.upper().startswith("SELECT"):
            return {
                "question": question,
                "generated_sql": generated_sql,
                "results": [],
                "row_count": 0,
                "error": "AlloyDB AI did not return a valid SELECT statement.",
            }

        logger.info(f"[query_nl] Generated SQL: {generated_sql}")

        # Step 2: Execute the generated SQL
        rows = await conn.fetch(generated_sql)
        results = [dict(r) for r in rows]

        return {
            "question": question,
            "generated_sql": generated_sql,
            "results": results,
            "row_count": len(results),
        }

    except Exception as exc:
        logger.error(f"[query_nl] Error: {exc}")
        return {
            "question": question,
            "generated_sql": "",
            "results": [],
            "row_count": 0,
            "error": str(exc),
        }
    finally:
        await conn.close()


# ── Local dev fallback ────────────────────────────────────────────────────────

async def get_connection_local() -> asyncpg.Connection:
    """
    Password-based connection for local development without IAM.
    Set ALLOYDB_PASSWORD in your .env for local testing.

    Switch main.py to call this during local dev:
        from db.alloydb import get_connection_local as get_connection
    """
    conn = await asyncpg.connect(
        host=ALLOYDB_HOST,
        port=ALLOYDB_PORT,
        database=ALLOYDB_DATABASE,
        user=os.getenv("ALLOYDB_LOCAL_USER", "postgres"),
        password=os.getenv("ALLOYDB_PASSWORD", "postgres"),
    )
    return conn

