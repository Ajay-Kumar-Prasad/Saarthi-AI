import logging

try:
    from db.alloydb import get_connection
except Exception:
    async def get_connection():
        raise RuntimeError("AlloyDB dependencies are not installed.")

logger = logging.getLogger(__name__)

async def get_all_tasks(user_id: str) -> list[dict]:
    conn = await get_connection()
    try:
        rows = await conn.fetch(
            "SELECT * FROM tasks WHERE user_id = $1 ORDER BY created_at DESC",
            user_id
        )
        return [dict(r) for r in rows]
    finally:
        await conn.close()
