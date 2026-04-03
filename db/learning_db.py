"""
Saarthi AI — Learning domain database operations.

All functions are async and use the IAM-authenticated AlloyDB connection.
These are called by learning_tools.py and the learning agent directly.
"""

import logging
from datetime import datetime, timedelta
from uuid import uuid4

from db.alloydb import get_connection
from models.schemas import LearningResource, StudySession, StudyGoal

logger = logging.getLogger(__name__)


# ── Learning Resources ────────────────────────────────────────────────────────

async def get_all_resources(user_id: str, status: str | None = None) -> list[dict]:
    """Fetch all learning resources for a user, optionally filtered by status."""
    conn = await get_connection()
    try:
        if status:
            rows = await conn.fetch(
                """
                SELECT * FROM learning_resources
                WHERE user_id = $1 AND status = $2
                ORDER BY updated_at DESC
                """,
                user_id, status,
            )
        else:
            rows = await conn.fetch(
                """
                SELECT * FROM learning_resources
                WHERE user_id = $1
                ORDER BY
                    CASE status
                        WHEN 'in_progress' THEN 1
                        WHEN 'not_started' THEN 2
                        WHEN 'paused'      THEN 3
                        WHEN 'completed'   THEN 4
                    END,
                    updated_at DESC
                """,
                user_id,
            )
        return [dict(r) for r in rows]
    finally:
        await conn.close()


async def add_resource(resource: LearningResource) -> dict:
    """Insert a new learning resource and return the created row."""
    conn = await get_connection()
    try:
        row = await conn.fetchrow(
            """
            INSERT INTO learning_resources
                (id, user_id, title, resource_type, url, author,
                 status, progress_pct, total_pages, current_page,
                 notes, tags)
            VALUES
                ($1, $2, $3, $4, $5, $6,
                 $7, $8, $9, $10,
                 $11, $12)
            RETURNING *
            """,
            str(uuid4()),
            resource.user_id,
            resource.title,
            resource.resource_type,
            resource.url,
            resource.author,
            resource.status,
            resource.progress_pct,
            resource.total_pages,
            resource.current_page,
            resource.notes,
            resource.tags,
        )
        return dict(row)
    finally:
        await conn.close()


async def update_resource_progress(
    resource_id: str, user_id: str, progress_pct: int, current_page: int | None = None
) -> dict:
    """Update progress percentage (and optional page) on a resource."""
    conn = await get_connection()
    try:
        new_status = "completed" if progress_pct >= 100 else "in_progress"
        row = await conn.fetchrow(
            """
            UPDATE learning_resources
            SET progress_pct = $1,
                current_page = COALESCE($2, current_page),
                status       = $3,
                updated_at   = now()
            WHERE id = $4 AND user_id = $5
            RETURNING *
            """,
            progress_pct,
            current_page,
            new_status,
            resource_id,
            user_id,
        )
        return dict(row) if row else {}
    finally:
        await conn.close()


# ── Study Sessions ────────────────────────────────────────────────────────────

async def get_upcoming_sessions(user_id: str, days_ahead: int = 7) -> list[dict]:
    """Fetch all upcoming study sessions within the next N days."""
    conn = await get_connection()
    try:
        rows = await conn.fetch(
            """
            SELECT ss.*, lr.title AS resource_title, lr.resource_type
            FROM study_sessions ss
            JOIN learning_resources lr ON lr.id = ss.resource_id
            WHERE ss.user_id = $1
              AND ss.scheduled_at BETWEEN now() AND now() + ($2 * INTERVAL '1 day')
              AND ss.completed = false
            ORDER BY ss.scheduled_at ASC
            """,
            user_id,
            days_ahead,
        )
        return [dict(r) for r in rows]
    finally:
        await conn.close()


async def create_study_session(session: StudySession) -> dict:
    """Create a study session record (after the calendar event is booked via MCP)."""
    conn = await get_connection()
    try:
        row = await conn.fetchrow(
            """
            INSERT INTO study_sessions
                (id, user_id, resource_id, title, scheduled_at,
                 duration_minutes, calendar_event_id, completed, notes)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            RETURNING *
            """,
            str(uuid4()),
            session.user_id,
            session.resource_id,
            session.title,
            session.scheduled_at,
            session.duration_minutes,
            session.calendar_event_id,
            session.completed,
            session.notes,
        )
        return dict(row)
    finally:
        await conn.close()


async def mark_session_complete(session_id: str, user_id: str, notes: str = "") -> dict:
    """Mark a study session as completed."""
    conn = await get_connection()
    try:
        row = await conn.fetchrow(
            """
            UPDATE study_sessions
            SET completed = true, notes = COALESCE($1, notes)
            WHERE id = $2 AND user_id = $3
            RETURNING *
            """,
            notes or None,
            session_id,
            user_id,
        )
        return dict(row) if row else {}
    finally:
        await conn.close()


# ── Study Goals ───────────────────────────────────────────────────────────────

async def get_active_goals(user_id: str) -> list[dict]:
    """Return all active study goals for the user."""
    conn = await get_connection()
    try:
        rows = await conn.fetch(
            """
            SELECT sg.*, lr.title AS resource_title
            FROM study_goals sg
            LEFT JOIN learning_resources lr ON lr.id = sg.resource_id
            WHERE sg.user_id = $1 AND sg.status = 'active'
            ORDER BY sg.target_date ASC NULLS LAST
            """,
            user_id,
        )
        return [dict(r) for r in rows]
    finally:
        await conn.close()


async def create_study_goal(goal: StudyGoal) -> dict:
    """Persist a new study goal."""
    conn = await get_connection()
    try:
        row = await conn.fetchrow(
            """
            INSERT INTO study_goals
                (id, user_id, resource_id, title, target_date,
                 weekly_hours_target, progress_pct, status)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            RETURNING *
            """,
            str(uuid4()),
            goal.user_id,
            goal.resource_id,
            goal.title,
            goal.target_date,
            goal.weekly_hours_target,
            goal.progress_pct,
            goal.status,
        )
        return dict(row)
    finally:
        await conn.close()


# ── Analytics ─────────────────────────────────────────────────────────────────

async def get_weekly_study_hours(user_id: str) -> float:
    """Total hours of completed study sessions in the past 7 days."""
    conn = await get_connection()
    try:
        row = await conn.fetchrow(
            """
            SELECT COALESCE(SUM(duration_minutes) / 60.0, 0) AS hours
            FROM study_sessions
            WHERE user_id = $1
              AND completed = true
              AND scheduled_at > now() - INTERVAL '7 days'
            """,
            user_id,
        )
        return float(row["hours"])
    finally:
        await conn.close()


async def get_study_streak(user_id: str) -> int:
    """
    Counts how many consecutive days (ending today) the user
    completed at least one study session.
    """
    conn = await get_connection()
    try:
        rows = await conn.fetch(
            """
            SELECT DISTINCT DATE(scheduled_at) AS study_date
            FROM study_sessions
            WHERE user_id = $1 AND completed = true
            ORDER BY study_date DESC
            """,
            user_id,
        )
        streak = 0
        expected = datetime.utcnow().date()
        for row in rows:
            if row["study_date"] == expected:
                streak += 1
                expected = expected - timedelta(days=1)
            else:
                break
        return streak
    finally:
        await conn.close()