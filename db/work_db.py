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

async def create_task(
    user_id: str,
    title: str,
    status: str = "pending",
    due_date: str | None = None,
):
    conn = await get_connection()
    try:
        row = await conn.fetchrow(
            """
            INSERT INTO tasks (user_id, title, status, due_date)
            VALUES ($1, $2, $3, $4)
            RETURNING *
            """,
            user_id,
            title,
            status,
            due_date,
        )
        return dict(row)
    finally:
        await conn.close()

async def update_task(
    task_id: int,
    status: str | None = None,
    title: str | None = None,
):
    conn = await get_connection()
    try:
        row = await conn.fetchrow(
            """
            UPDATE tasks
            SET
                status = COALESCE($2, status),
                title = COALESCE($3, title)
            WHERE id = $1
            RETURNING *
            """,
            task_id,
            status,
            title,
        )
        return dict(row) if row else None
    finally:
        await conn.close()

async def delete_task(task_id: int):
    conn = await get_connection()
    try:
        await conn.execute(
            "DELETE FROM tasks WHERE id = $1",
            task_id
        )
        return {"deleted": True}
    finally:
        await conn.close()

async def get_task_by_id(task_id: int):
    conn = await get_connection()
    try:
        row = await conn.fetchrow(
            "SELECT * FROM tasks WHERE id = $1",
            task_id
        )
        return dict(row) if row else None
    finally:
        await conn.close()