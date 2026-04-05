"""
Saarthi AI — Notes MCP using AlloyDB life_logs table.
Google Keep API requires workspace account, so we store notes
in the life_logs table with domain='learning'.
"""

import os
import logging
from datetime import datetime
from uuid import uuid4

logger = logging.getLogger(__name__)


async def save_learning_note(
    user_id: str,
    resource_title: str,
    note_content: str,
    tags: list[str] | None = None,
) -> dict:
    """Save a study note to AlloyDB life_logs table."""
    try:
        from db.alloydb import get_connection
        conn = await get_connection()
        try:
            entry = f"[{resource_title}] {note_content}"
            row = await conn.fetchrow(
                """
                INSERT INTO life_logs (id, user_id, domain, entry, logged_at)
                VALUES ($1, $2, 'learning', $3, now())
                RETURNING id, logged_at
                """,
                str(uuid4()), user_id, entry,
            )
            logger.info("Note saved for user %s", user_id)
            return {
                "note_id": str(row["id"]),
                "saved": True,
                "resource": resource_title,
                "logged_at": str(row["logged_at"]),
            }
        finally:
            await conn.close()
    except Exception as exc:
        logger.error("Failed to save note: %s", exc)
        return {"note_id": None, "saved": False, "error": str(exc)}


async def get_learning_notes(
    user_id: str,
    resource_title: str | None = None,
) -> list[dict]:
    """Retrieve learning notes from AlloyDB life_logs."""
    try:
        from db.alloydb import get_connection
        conn = await get_connection()
        try:
            if resource_title:
                rows = await conn.fetch(
                    """
                    SELECT id, entry, logged_at
                    FROM life_logs
                    WHERE user_id = $1
                      AND domain = 'learning'
                      AND entry ILIKE $2
                    ORDER BY logged_at DESC
                    LIMIT 20
                    """,
                    user_id, f"%{resource_title}%",
                )
            else:
                rows = await conn.fetch(
                    """
                    SELECT id, entry, logged_at
                    FROM life_logs
                    WHERE user_id = $1 AND domain = 'learning'
                    ORDER BY logged_at DESC
                    LIMIT 20
                    """,
                    user_id,
                )
            return [
                {
                    "note_id": str(r["id"]),
                    "content": r["entry"],
                    "logged_at": str(r["logged_at"]),
                }
                for r in rows
            ]
        finally:
            await conn.close()
    except Exception as exc:
        logger.error("Failed to fetch notes: %s", exc)
        return []
