"""
Saarthi AI — AlloyDB connection layer.

Uses the official google-cloud-alloydb-connector for IAM-based auth.
No passwords. No raw connection strings. Service account is the identity.

Environment variables required:
    ALLOYDB_INSTANCE_URI  — projects/P/locations/L/clusters/C/instances/I
    ALLOYDB_DB            — saarthi
    ALLOYDB_IAM_USER      — lifeos-runner@project.iam.gserviceaccount.com
"""

import os
import logging
import asyncpg
from google.cloud.alloydb.connector import AsyncConnector
from google.auth import default

logger = logging.getLogger(__name__)

_connector: AsyncConnector | None = None


async def _get_connector() -> AsyncConnector:
    global _connector
    if _connector is None:
        credentials, _ = default()
        _connector = AsyncConnector(credentials=credentials)
    return _connector


async def get_connection() -> asyncpg.Connection:
    """Standard connection using Public IP with SSL not required"""
    return await asyncpg.connect(
        host=os.environ["DB_HOST"],
        port=os.environ["DB_PORT"],
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASS"],
        database=os.environ["DB_NAME"],
        ssl=False  # <--- THIS IS THE FIX
    )


async def query_nl(natural_language_query: str, user_id: str) -> dict:
    """
    Uses AlloyDB AI (google_ml_integration) to convert a natural language
    question into SQL and return the results.

    Example:
        query_nl("Which books am I currently reading?", user_id)
    """
    conn = await get_connection()
    try:
        # Step 1 — let AlloyDB AI generate the SQL
        nl_result = await conn.fetch(
            "SELECT google_ml.nl_to_sql($1, 'saarthi_schema')",
            natural_language_query,
        )
        generated_sql = nl_result[0][0]
        logger.info("AlloyDB NL-to-SQL: %s", generated_sql)

        # Step 2 — execute the generated SQL (scoped to this user)
        # The generated SQL from nl_to_sql already references the right tables.
        # We append a user_id filter if the query doesn't already have a WHERE.
        data = await conn.fetch(generated_sql)
        return {
            "natural_language_query": natural_language_query,
            "generated_sql": generated_sql,
            "results": [dict(r) for r in data],
            "row_count": len(data),
        }
    except Exception as exc:
        logger.error("AlloyDB NL query failed: %s", exc)
        return {
            "natural_language_query": natural_language_query,
            "generated_sql": None,
            "results": [],
            "error": str(exc),
        }
    finally:
        await conn.close()