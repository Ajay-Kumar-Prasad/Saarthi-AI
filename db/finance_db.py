from __future__ import annotations

from datetime import datetime

from db.alloydb import get_connection


async def insert_expense(
    amount: float,
    category: str,
    description: str,
    date: datetime,
    user_id: str | None = None,
) -> None:
    conn = await get_connection()
    try:
        await conn.execute(
            """
            INSERT INTO expenses (amount, category, description, date, user_id)
            VALUES ($1, $2, $3, $4, $5)
            """,
            amount,
            category,
            description,
            date,
            user_id,
        )
    finally:
        await conn.close()


async def get_all_expenses(user_id: str | None = None) -> list[dict]:
    conn = await get_connection()
    try:
        if user_id:
            rows = await conn.fetch(
                """
                SELECT amount, category, description, date
                FROM expenses
                WHERE user_id = $1
                ORDER BY date DESC
                """,
                user_id,
            )
        else:
            rows = await conn.fetch(
                """
                SELECT amount, category, description, date
                FROM expenses
                ORDER BY date DESC
                """
            )
        return [dict(r) for r in rows]
    finally:
        await conn.close()

