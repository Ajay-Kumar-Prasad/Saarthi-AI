"""
Saarthi AI — Learning domain database operations.

All functions are async and use the IAM-authenticated AlloyDB connection.
These are called by learning_tools.py and the learning agent directly.
"""

import logging
from datetime import datetime, timedelta, date
from uuid import uuid4

try:
    from db.alloydb import get_connection
except Exception:  # pragma: no cover - allows unit tests without AlloyDB deps
    async def get_connection():
        raise RuntimeError("AlloyDB dependencies are not installed.")
from db.schemas import LearningResource, StudySession, StudyGoal

logger = logging.getLogger(__name__)
import os
MOCK_DB = os.getenv("MOCK_DB", "false").lower() == "true"



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
    if MOCK_DB:
        import uuid as _uuid
        return {"id": str(_uuid.uuid4()), "user_id": resource.user_id, "title": resource.title, "resource_type": resource.resource_type, "status": "not_started", "progress_pct": 0, "tags": resource.tags}
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
    if progress_pct < 0 or progress_pct > 100:
        return {}
    if current_page is not None and current_page < 0:
        return {}
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
    if MOCK_DB:
        return []
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
        resource = await conn.fetchrow(
            "SELECT id FROM learning_resources WHERE id = $1 AND user_id = $2",
            session.resource_id,
            session.user_id,
        )
        if not resource:
            return {}

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
    if MOCK_DB:
        return [{"id": "goal-001", "title": "Complete GCP certification", "weekly_hours_target": 8.0, "progress_pct": 60, "target_date": "2026-05-04", "status": "active"}]
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
    if MOCK_DB:
        import uuid as _uuid
        return {"id": str(_uuid.uuid4()), "user_id": goal.user_id, "title": goal.title, "weekly_hours_target": goal.weekly_hours_target, "progress_pct": 0, "status": "active"}
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
            date.fromisoformat(goal.target_date) if goal.target_date else None,
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


async def query_learning_history_safe(user_id: str, question: str) -> dict:
    """
    Safely run AlloyDB NL-to-SQL for the learning domain.
    Allows only single SELECT statements and blocks suspicious SQL.
    """
    conn = await get_connection()
    try:
        scoped_question = f"For user_id={user_id} in learning domain only: {question}"
        nl_result = await conn.fetch(
            "SELECT google_ml.nl_to_sql($1, 'saarthi_schema')",
            scoped_question,
        )
        if not nl_result:
            generated_sql = ""
        else:
            row = nl_result[0]
            try:
                generated_sql = (row[0] or "").strip()
            except (KeyError, TypeError):
                generated_sql = (row.get("google_ml.nl_to_sql") or "").strip()
        lower = generated_sql.lower()

        if not generated_sql:
            return {
                "question": question,
                "generated_sql": None,
                "results": [],
                "error": "No SQL generated from query.",
            }

        if not lower.startswith("select") or ";" in generated_sql:
            return {
                "question": question,
                "generated_sql": generated_sql,
                "results": [],
                "error": "Unsafe SQL blocked. Only single SELECT statements are allowed.",
            }

        blocked_keywords = (
            "insert ",
            "update ",
            "delete ",
            "drop ",
            "alter ",
            "create ",
            "grant ",
            "revoke ",
        )
        if any(k in lower for k in blocked_keywords):
            return {
                "question": question,
                "generated_sql": generated_sql,
                "results": [],
                "error": "Unsafe SQL blocked.",
            }

        if "user_id" not in lower:
            return {
                "question": question,
                "generated_sql": generated_sql,
                "results": [],
                "error": "Query was not user-scoped; blocked for safety.",
            }

        rows = await conn.fetch(generated_sql)
        return {
            "question": question,
            "generated_sql": generated_sql,
            "results": [dict(r) for r in rows],
            "row_count": len(rows),
        }
    except Exception as exc:
        logger.error("Safe NL query failed: %s", exc)
        return {
            "question": question,
            "generated_sql": None,
            "results": [],
            "error": str(exc),
        }
    finally:
        await conn.close()

"""
Covers 4 new features:
  1. Skill gap analysis    — user_skills + role_skill_requirements tables
  2. Spaced repetition     — flashcards table (SM-2 algorithm)
  3. Course recommendations— queries existing learning_resources + user_skills
  4. Learning paths        — learning_paths + learning_path_steps tables

"""

# =============================================================================
# FEATURE 1 — SKILL GAP ANALYSIS
# =============================================================================

async def get_user_skills(user_id: str) -> list[dict]:
    if MOCK_DB:
        return [{"skill_name": "Python", "proficiency": "intermediate"}, {"skill_name": "SQL", "proficiency": "beginner"}]
    """Return all skills the user currently has."""
    conn = await get_connection()
    try:
        rows = await conn.fetch(
            """
            SELECT us.*, lr.title AS source_resource_title
            FROM user_skills us
            LEFT JOIN learning_resources lr ON lr.id = us.source_resource_id
            WHERE us.user_id = $1
            ORDER BY us.category, us.skill_name
            """,
            user_id,
        )
        return [dict(r) for r in rows]
    finally:
        await conn.close()


async def get_role_requirements(role_name: str) -> list[dict]:
    """Return all skills required for a given career role."""
    conn = await get_connection()
    try:
        rows = await conn.fetch(
            """
            SELECT * FROM role_skill_requirements
            WHERE LOWER(role_name) = LOWER($1)
            ORDER BY
                CASE importance
                    WHEN 'required'    THEN 1
                    WHEN 'recommended' THEN 2
                    WHEN 'optional'    THEN 3
                END
            """,
            role_name,
        )
        return [dict(r) for r in rows]
    finally:
        await conn.close()


async def get_available_roles() -> list[str]:
    """Return all roles that have skill requirements defined."""
    conn = await get_connection()
    try:
        rows = await conn.fetch(
            "SELECT DISTINCT role_name FROM role_skill_requirements ORDER BY role_name"
        )
        return [r["role_name"] for r in rows]
    finally:
        await conn.close()


async def add_user_skill(
    user_id: str,
    skill_name: str,
    category: str,
    proficiency: str = "beginner",
    source_resource_id: str | None = None,
) -> dict:
    """Add or update a skill for the user."""
    if MOCK_DB:
        return {"user_id": user_id, "skill_name": skill_name, "proficiency": proficiency}
    conn = await get_connection()
    try:
        # Verify skill by checking if a completed resource covers it
        verified = False
        if source_resource_id:
            row = await conn.fetchrow(
                "SELECT status FROM learning_resources WHERE id = $1 AND user_id = $2",
                source_resource_id, user_id,
            )
            verified = row is not None and row["status"] == "completed"

        row = await conn.fetchrow(
            """
            INSERT INTO user_skills
                (id, user_id, skill_name, category, proficiency,
                 verified, source_resource_id, updated_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, now())
            ON CONFLICT (user_id, skill_name) DO UPDATE
                SET proficiency        = EXCLUDED.proficiency,
                    verified           = EXCLUDED.verified,
                    source_resource_id = EXCLUDED.source_resource_id,
                    updated_at         = now()
            RETURNING *
            """,
            str(uuid4()), user_id, skill_name, category,
            proficiency, verified, source_resource_id,
        )
        return dict(row)
    finally:
        await conn.close()


async def compute_skill_gap(user_id: str, role_name: str) -> dict:
    """
    Compare the user's current skills against the requirements for a role.

    Returns:
        {
          "role": str,
          "required_skills": list,
          "user_skills": list,
          "missing_required": list,    ← must learn these
          "missing_recommended": list, ← should learn these
          "gap_score": int,            ← 0-100, higher = more gaps
          "matched": list,             ← already have these
        }
    """
    conn = await get_connection()
    try:
        # All role requirements
        requirements = await conn.fetch(
            """
            SELECT skill_name, importance
            FROM role_skill_requirements
            WHERE LOWER(role_name) = LOWER($1)
            """,
            role_name,
        )

        # User's current skills (lowercase for comparison)
        user_skills_rows = await conn.fetch(
            "SELECT skill_name, proficiency FROM user_skills WHERE user_id = $1",
            user_id,
        )
        user_skill_names = {r["skill_name"].lower() for r in user_skills_rows}

        missing_required    = []
        missing_recommended = []
        matched             = []

        for req in requirements:
            skill = req["skill_name"]
            if skill.lower() in user_skill_names:
                matched.append(skill)
            elif req["importance"] == "required":
                missing_required.append(skill)
            elif req["importance"] == "recommended":
                missing_recommended.append(skill)

        total = len(requirements)
        gap_score = int((len(missing_required) + len(missing_recommended) * 0.5) / max(total, 1) * 100)

        return {
            "role": role_name,
            "total_skills_required": total,
            "matched": matched,
            "missing_required": missing_required,
            "missing_recommended": missing_recommended,
            "gap_score": gap_score,             # 0 = no gap, 100 = complete gap
            "readiness_pct": 100 - gap_score,
        }
    finally:
        await conn.close()


# =============================================================================
# FEATURE 2 — SPACED REPETITION (SM-2 Algorithm)
# =============================================================================

async def get_due_flashcards(user_id: str, limit: int = 10) -> list[dict]:
    """Return flashcards due for review right now."""
    conn = await get_connection()
    try:
        rows = await conn.fetch(
            """
            SELECT f.*, lr.title AS resource_title
            FROM flashcards f
            JOIN learning_resources lr ON lr.id = f.resource_id
            WHERE f.user_id = $1
              AND f.next_review_at <= now()
            ORDER BY f.next_review_at ASC
            LIMIT $2
            """,
            user_id, limit,
        )
        return [dict(r) for r in rows]
    finally:
        await conn.close()


async def create_flashcard(
    user_id: str,
    resource_id: str,
    question: str,
    answer: str,
    tags: list[str] | None = None,
) -> dict:
    """Create a new flashcard for a learning resource."""
    conn = await get_connection()
    try:
        resource = await conn.fetchrow(
            "SELECT id FROM learning_resources WHERE id = $1 AND user_id = $2",
            resource_id,
            user_id,
        )
        if not resource:
            return {}

        row = await conn.fetchrow(
            """
            INSERT INTO flashcards
                (id, user_id, resource_id, question, answer, tags)
            VALUES ($1, $2, $3, $4, $5, $6)
            RETURNING *
            """,
            str(uuid4()), user_id, resource_id, question, answer,
            tags or [],
        )
        return dict(row)
    finally:
        await conn.close()


async def update_flashcard_after_review(
    flashcard_id: str,
    user_id: str,
    quality: int,           # 0-5 (SM-2 scale): 0=blackout, 3=correct, 5=perfect
) -> dict:
    """
    Apply the SM-2 spaced repetition algorithm after a review.
    quality: 0-2 = incorrect/hard, 3-4 = correct, 5 = perfect

    SM-2 rules:
      - If quality < 3: reset repetitions to 0, interval = 1 day
      - If quality >= 3: update ease_factor and interval
        new_ef = ef + (0.1 - (5-q) * (0.08 + (5-q) * 0.02))
        interval: rep=1→1d, rep=2→6d, rep>2→prev_interval * ef
    """
    conn = await get_connection()
    try:
        if quality < 0 or quality > 5:
            return {}

        card = await conn.fetchrow(
            "SELECT * FROM flashcards WHERE id = $1 AND user_id = $2",
            flashcard_id, user_id,
        )
        if not card:
            return {}

        ef          = float(card["ease_factor"])
        repetitions = card["repetitions"]
        interval    = card["interval_days"]

        if quality < 3:
            # Incorrect — reset
            repetitions = 0
            interval    = 1
        else:
            # Correct — apply SM-2
            ef = ef + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
            ef = max(1.3, round(ef, 2))     # never drop below 1.3

            if repetitions == 0:
                interval = 1
            elif repetitions == 1:
                interval = 6
            else:
                interval = round(interval * ef)

            repetitions += 1

        next_review = datetime.utcnow() + timedelta(days=interval)

        row = await conn.fetchrow(
            """
            UPDATE flashcards
            SET ease_factor      = $1,
                interval_days    = $2,
                repetitions      = $3,
                next_review_at   = $4,
                last_reviewed_at = now()
            WHERE id = $5 AND user_id = $6
            RETURNING *
            """,
            ef, interval, repetitions, next_review,
            flashcard_id, user_id,
        )
        return dict(row)
    finally:
        await conn.close()


async def get_flashcard_stats(user_id: str) -> dict:
    if MOCK_DB:
        return {"total_cards": 0, "due_now": 0, "reviewed_at_least_once": 0, "avg_ease_factor": 2.5, "max_streak": 0}
    """Return flashcard review statistics for the user."""
    conn = await get_connection()
    try:
        row = await conn.fetchrow(
            """
            SELECT
                COUNT(*)                                        AS total_cards,
                COUNT(*) FILTER (WHERE next_review_at <= now()) AS due_now,
                COUNT(*) FILTER (WHERE repetitions > 0)        AS reviewed_at_least_once,
                ROUND(AVG(ease_factor), 2)                      AS avg_ease_factor,
                MAX(repetitions)                                AS max_streak
            FROM flashcards
            WHERE user_id = $1
            """,
            user_id,
        )
        return dict(row)
    finally:
        await conn.close()


# =============================================================================
# FEATURE 3 — COURSE RECOMMENDATIONS
# =============================================================================

async def get_recommendation_context(user_id: str) -> dict:
    """
    Pull all data the recommendation engine needs:
    - completed resources (what the user knows)
    - in_progress resources (what they're doing)
    - active goals (where they want to go)
    - user skills (current proficiency map)
    - skill gaps if they have a goal role
    """
    conn = await get_connection()
    try:
        completed = await conn.fetch(
            "SELECT title, tags FROM learning_resources WHERE user_id=$1 AND status='completed'",
            user_id,
        )
        in_progress = await conn.fetch(
            "SELECT title, progress_pct, tags FROM learning_resources WHERE user_id=$1 AND status='in_progress'",
            user_id,
        )
        goals = await conn.fetch(
            "SELECT title, target_date, weekly_hours_target FROM study_goals WHERE user_id=$1 AND status='active'",
            user_id,
        )
        skills = await conn.fetch(
            "SELECT skill_name, proficiency FROM user_skills WHERE user_id=$1",
            user_id,
        )
        return {
            "completed":   [dict(r) for r in completed],
            "in_progress": [dict(r) for r in in_progress],
            "goals":       [dict(r) for r in goals],
            "skills":      [dict(r) for r in skills],
        }
    finally:
        await conn.close()


# =============================================================================
# FEATURE 4 — LEARNING PATHS
# =============================================================================

async def create_learning_path(
    user_id: str,
    title: str,
    description: str,
    target_role: str | None,
    estimated_weeks: int | None,
) -> dict:
    """Create a new learning path (the container)."""
    conn = await get_connection()
    if MOCK_DB:
        import uuid as _uuid
        return {"id": str(_uuid.uuid4()), "user_id": user_id, "title": title, "target_role": target_role, "status": "active", "estimated_weeks": estimated_weeks, "created_at": "2026-04-04", "updated_at": "2026-04-04"}
    try:
        row = await conn.fetchrow(
            """
            INSERT INTO learning_paths
                (id, user_id, title, description, target_role, estimated_weeks)
            VALUES ($1, $2, $3, $4, $5, $6)
            RETURNING *
            """,
            str(uuid4()), user_id, title, description,
            target_role, estimated_weeks,
        )
        return dict(row)
    finally:
        await conn.close()


async def get_learning_resources_for_path(user_id: str) -> list[dict]:
    if MOCK_DB:
        return [{"id": "res-001", "title": "Python Crash Course", "resource_type": "book", "status": "in_progress", "progress_pct": 45, "tags": ["python"]}, {"id": "res-002", "title": "GCP Professional Certificate", "resource_type": "course", "status": "in_progress", "progress_pct": 60, "tags": ["gcp"]}]
    """Return user resources ordered for path construction."""
    conn = await get_connection()
    try:
        rows = await conn.fetch(
            """
            SELECT id, title, resource_type, status, progress_pct, tags
            FROM learning_resources
            WHERE user_id = $1
            ORDER BY
                CASE status
                    WHEN 'completed'   THEN 1
                    WHEN 'in_progress' THEN 2
                    WHEN 'not_started' THEN 3
                    WHEN 'paused'      THEN 4
                END
            """,
            user_id,
        )
        return [dict(r) for r in rows]
    finally:
        await conn.close()


async def add_path_step(
    path_id: str,
    resource_id: str,
    step_order: int,
    title: str,
    why_this: str,
    estimated_hours: int,
) -> dict:
    """Add a step (resource) to an existing learning path."""
    conn = await get_connection()
    if MOCK_DB:
        import uuid as _uuid
        return {"id": str(_uuid.uuid4()), "path_id": path_id, "resource_id": resource_id, "step_order": step_order, "title": title, "why_this": why_this, "status": "pending", "estimated_hours": estimated_hours}
    try:
        row = await conn.fetchrow(
            """
            INSERT INTO learning_path_steps
                (id, path_id, resource_id, step_order, title, why_this, estimated_hours)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            ON CONFLICT (path_id, step_order) DO UPDATE
                SET title           = EXCLUDED.title,
                    why_this        = EXCLUDED.why_this,
                    estimated_hours = EXCLUDED.estimated_hours
            RETURNING *
            """,
            str(uuid4()), path_id, resource_id,
            step_order, title, why_this, estimated_hours,
        )
        return dict(row)
    finally:
        await conn.close()


async def get_learning_path(user_id: str, path_id: str) -> dict:
    if MOCK_DB:
        return {"id": path_id, "user_id": user_id, "title": "Mock Path", "status": "active", "steps": [], "progress_pct": 0}
    """Return a learning path and all its steps with resource details."""
    conn = await get_connection()
    try:
        path = await conn.fetchrow(
            "SELECT * FROM learning_paths WHERE id = $1 AND user_id = $2",
            path_id, user_id,
        )
        if not path:
            return {}

        steps = await conn.fetch(
            """
            SELECT lps.*, lr.title AS resource_title,
                   lr.status AS resource_status,
                   lr.progress_pct, lr.resource_type, lr.url
            FROM learning_path_steps lps
            JOIN learning_resources lr ON lr.id = lps.resource_id
            WHERE lps.path_id = $1
            ORDER BY lps.step_order ASC
            """,
            path_id,
        )

        total_hours    = sum(s["estimated_hours"] or 0 for s in steps)
        completed_steps = sum(1 for s in steps if s["status"] == "completed")
        progress_pct    = int(completed_steps / max(len(steps), 1) * 100)

        return {
            **dict(path),
            "steps":          [dict(s) for s in steps],
            "total_steps":    len(steps),
            "completed_steps": completed_steps,
            "progress_pct":   progress_pct,
            "total_hours":    total_hours,
        }
    finally:
        await conn.close()


async def get_all_learning_paths(user_id: str) -> list[dict]:
    """Return all learning paths for a user with high-level progress."""
    conn = await get_connection()
    try:
        rows = await conn.fetch(
            """
            SELECT lp.*,
                COUNT(lps.id)                                           AS total_steps,
                COUNT(lps.id) FILTER (WHERE lps.status = 'completed')  AS completed_steps
            FROM learning_paths lp
            LEFT JOIN learning_path_steps lps ON lps.path_id = lp.id
            WHERE lp.user_id = $1
            GROUP BY lp.id
            ORDER BY lp.created_at DESC
            """,
            user_id,
        )
        result = []
        for r in rows:
            d = dict(r)
            total = d["total_steps"] or 0
            done  = d["completed_steps"] or 0
            d["progress_pct"] = int(done / max(total, 1) * 100)
            result.append(d)
        return result
    finally:
        await conn.close()


async def update_path_step_status(
    user_id: str, path_id: str, step_order: int, status: str
) -> dict:
    """Mark a path step as completed, in_progress, or skipped."""
    conn = await get_connection()
    if MOCK_DB:
        return {"id": "step-001", "path_id": path_id, "step_order": step_order, "status": status}
    try:
        if status not in {"completed", "in_progress", "skipped", "pending"}:
            return {}

        completed_at = datetime.utcnow() if status == "completed" else None
        row = await conn.fetchrow(
            """
            UPDATE learning_path_steps lps
            SET status = $1, completed_at = $2
            FROM learning_paths lp
            WHERE lps.path_id = lp.id
              AND lps.path_id = $3
              AND lps.step_order = $4
              AND lp.user_id = $5
            RETURNING lps.*
            """,
            status, completed_at, path_id, step_order, user_id,
        )
        return dict(row) if row else {}
    finally:
        await conn.close()
