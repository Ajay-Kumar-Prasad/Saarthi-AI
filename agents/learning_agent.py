"""
Saarthi AI — Learning Agent

Responsibility:
    Manages everything in the 'learning' domain:
    - Tracking books, courses, articles the user is studying
    - Scheduling study sessions on the calendar (via Calendar MCP)
    - Logging notes and summaries (via Notes MCP)
    - Detecting conflicts between study blocks and other life events
    - Reporting learning streaks, progress, and overdue goals

MCP Tools used:
    - Calendar MCP  → create_study_calendar_event, get_calendar_events
    - Notes MCP     → save_learning_note, get_learning_notes

Database:
    - learning_resources — books/courses being tracked
    - study_sessions     — scheduled study blocks
    - study_goals        — high-level learning goals

Returns:
    Always an AgentResponse (see models/schemas.py).
    The orchestrator reads .conflicts to build cross-domain insights.
"""
import re
import json
import logging
import asyncio
from datetime import datetime, timedelta
import uuid

from typing import Any

try:
    from google.adk.agents import Agent
    from google.adk.runners import Runner
    from google.adk.sessions import InMemorySessionService
    from google.genai import types
except Exception:  # pragma: no cover
    class Agent:
        def __init__(self, *args, **kwargs): pass

    class Runner:
        def __init__(self, **kwargs): pass
        async def run_async(self, **kwargs):
            raise RuntimeError("google-adk is required to run the live agent")
            yield
    class InMemorySessionService:
        async def create_session(self, **kwargs): pass

    class types:
        class Content:
            def __init__(self, **kwargs): pass
        class Part:
            @staticmethod
            def text(t): return t

from db.learning_db import (
    get_all_resources,
    add_resource,
    update_resource_progress,
    get_upcoming_sessions,
    create_study_session,
    mark_session_complete,
    get_active_goals,
    create_study_goal,
    get_weekly_study_hours,
    get_study_streak,
    get_user_skills,
    add_user_skill,
    compute_skill_gap,
    get_available_roles,
    get_due_flashcards,
    create_flashcard,
    update_flashcard_after_review,
    get_flashcard_stats,
    get_recommendation_context,
    create_learning_path,
    add_path_step,
    get_learning_path,
    get_all_learning_paths,
    update_path_step_status,
    get_learning_resources_for_path,
    query_learning_history_safe,
)
from tools.learning_tools import (
    save_learning_note,
    get_learning_notes,
    create_study_calendar_event,
    get_calendar_events,
    find_free_slot,
    delete_calendar_event,
)
from db.schemas import (
    AgentResponse,
    AgentStatus,
    LearningResource,
    StudySession,
    StudyGoal,
)

logger = logging.getLogger(__name__)


ALLOWED_RESOURCE_TYPES = {"book", "course", "article", "video", "podcast"}
ALLOWED_PATH_STEP_STATUSES = {"pending", "in_progress", "completed", "skipped"}


def _json_error(message: str, **extra) -> str:
    payload = {"error": message}
    payload.update(extra)
    return json.dumps(payload, default=str)


def _is_valid_date_string(date_value: str) -> bool:
    try:
        datetime.fromisoformat(date_value)
        return True
    except Exception:
        return False


def _detect_role_from_text(text: str) -> str:
    lower = text.lower()
    role_keywords = {
        "data engineer": "Data Engineer",
        "ml engineer": "ML Engineer",
        "machine learning engineer": "ML Engineer",
        "cloud engineer": "Cloud Engineer",
        "backend developer": "Backend Developer",
        "backend engineer": "Backend Developer",
    }
    for keyword, role in role_keywords.items():
        if keyword in lower:
            return role
    return ""


# ── ADK Tool Functions ────────────────────────────────────────────────────────
# Google ADK picks these up via the `tools=` parameter on the Agent.
# Each function must have a complete docstring — ADK uses it as the tool
# description when deciding which function to call.

async def tool_get_learning_status(user_id: str) -> str:
    """
    Get a full snapshot of the user's current learning state.
    Returns active resources, upcoming study sessions, active goals,
    weekly hours studied, and current study streak.
    Use this when the user asks 'what am I learning?', 'how is my learning
    going?', or when the orchestrator needs learning context.

    Args:
        user_id: The user's UUID string.

    Returns:
        JSON string with keys: resources, sessions, goals, weekly_hours, streak_days.
    """
    if not user_id:
        return _json_error("user_id is required.")
    try:
        resources = await get_all_resources(user_id, status="in_progress")
        sessions = await get_upcoming_sessions(user_id, days_ahead=7)
        goals = await get_active_goals(user_id)
        weekly_hours = await get_weekly_study_hours(user_id)
        streak = await get_study_streak(user_id)
        return json.dumps({
            "resources": resources,
            "upcoming_sessions": sessions,
            "active_goals": goals,
            "weekly_hours_studied": round(weekly_hours, 1),
            "streak_days": streak,
        }, default=str)
    except Exception as exc:
        logger.error("tool_get_learning_status failed: %s", exc)
        return _json_error("Failed to fetch learning status.")


async def tool_add_learning_resource(
    user_id: str,
    title: str,
    resource_type: str,
    url: str = "",
    author: str = "",
    total_pages: int = 0,
    tags: str = "",           # comma-separated
) -> str:
    """
    Add a new book, course, article, or video to the user's learning list.
    Use when the user says 'I want to read X', 'add Y course', 'I started Z'.

    Args:
        user_id:       User UUID.
        title:         Title of the book/course/article.
        resource_type: One of: book | course | article | video | podcast.
        url:           Optional URL (for online courses or articles).
        author:        Optional author or instructor name.
        total_pages:   Total pages if it's a book (0 if unknown/not a book).
        tags:          Comma-separated topic tags e.g. "python,programming".

    Returns:
        JSON with the created resource details.
    """
    if not user_id:
        return _json_error("user_id is required.")
    if not title.strip():
        return _json_error("title is required.")
    if resource_type not in ALLOWED_RESOURCE_TYPES:
        return _json_error(
            "Invalid resource_type.",
            allowed=list(sorted(ALLOWED_RESOURCE_TYPES)),
        )
    if total_pages < 0:
        return _json_error("total_pages cannot be negative.")

    try:
        resource = LearningResource(
            user_id=user_id,
            title=title,
            resource_type=resource_type,
            url=url or None,
            author=author or None,
            total_pages=total_pages or None,
            tags=[t.strip() for t in tags.split(",") if t.strip()],
        )
        created = await add_resource(resource)
        return json.dumps({"created": True, "resource": created}, default=str)
    except Exception as exc:
        logger.error("tool_add_learning_resource failed: %s", exc)
        return _json_error("Failed to add learning resource.")


async def tool_update_progress(
    user_id: str,
    resource_id: str,
    progress_pct: int,
    current_page: int = 0,
) -> str:
    """
    Update the user's progress on a book or course.
    Use when the user says 'I finished chapter X', 'I'm at page Y',
    'I completed 70% of the course'.

    Args:
        user_id:      User UUID.
        resource_id:  UUID of the resource to update.
        progress_pct: Completion percentage 0-100.
        current_page: Current page number if it's a book (0 if not applicable).

    Returns:
        JSON with the updated resource.
    """
    if not user_id or not resource_id:
        return _json_error("user_id and resource_id are required.")
    if progress_pct < 0 or progress_pct > 100:
        return _json_error("progress_pct must be between 0 and 100.")
    if current_page < 0:
        return _json_error("current_page cannot be negative.")

    try:
        updated = await update_resource_progress(
            resource_id=resource_id,
            user_id=user_id,
            progress_pct=progress_pct,
            current_page=current_page or None,
        )
        if not updated:
            return _json_error("Resource not found or not owned by user.")
        message = "Resource marked as completed!" if progress_pct >= 100 else "Progress updated."
        return json.dumps({"message": message, "resource": updated}, default=str)
    except Exception as exc:
        logger.error("tool_update_progress failed: %s", exc)
        return _json_error("Failed to update resource progress.")


async def tool_schedule_study_session(
    user_id: str,
    resource_id: str,
    resource_title: str,
    date: str,
    duration_minutes: int = 60,
) -> str:
    """
    Schedule a study session by creating a calendar block and saving it to DB.
    Use when the user says 'schedule study time for X', 'book time to read Y',
    or when the orchestrator requests study sessions to be planned.

    The function automatically finds a free slot on the requested date and
    avoids clashing with existing calendar events.

    Args:
        user_id:          User UUID.
        resource_id:      UUID of the learning resource.
        resource_title:   Display title (used in calendar event name).
        date:             ISO date string e.g. '2026-04-10'.
        duration_minutes: Length of the session in minutes (default 60).

    Returns:
        JSON with { "session": {...}, "calendar_event": {...}, "conflict": bool }.
    """
    if not user_id or not resource_id or not resource_title:
        return _json_error("user_id, resource_id, and resource_title are required.")
    if not _is_valid_date_string(date):
        return _json_error("date must be a valid ISO date (YYYY-MM-DD).")
    if duration_minutes <= 0 or duration_minutes > 480:
        return _json_error("duration_minutes must be between 1 and 480.")
    if datetime.fromisoformat(date).date() < datetime.utcnow().date():
        return _json_error("Cannot schedule sessions in the past.")

    async def _rollback_calendar_event(event_id: str) -> tuple[bool, str]:
        if not event_id:
            logger.error("Rollback skipped: missing event_id")
            return False, "missing_event_id"
        logger.warning(
            "Attempting calendar rollback for user_id=%s event_id=%s",
            user_id, event_id,
        )
        try:
            rollback_resp = await delete_calendar_event(user_id, event_id)
            if not isinstance(rollback_resp, dict):
                logger.error(
                    "Calendar rollback returned non-dict response user_id=%s event_id=%s type=%s",
                    user_id, event_id, type(rollback_resp).__name__,
                )
                return False, "invalid_rollback_response"
            if rollback_resp.get("deleted"):
                logger.info(
                    "Calendar rollback succeeded for user_id=%s event_id=%s",
                    user_id, event_id,
                )
                return True, ""
            err = rollback_resp.get("error", "unknown_rollback_error")
            logger.error(
                "Calendar rollback failed for user_id=%s event_id=%s error=%s",
                user_id, event_id, err,
            )
            return False, str(err)
        except Exception as rollback_exc:
            logger.exception(
                "Calendar rollback exception for user_id=%s event_id=%s",
                user_id, event_id,
            )
            return False, str(rollback_exc)

    cal_event: dict | None = None
    event_id = ""
    try:
        # 1. Find a free slot on that date
        free_slot = await find_free_slot(user_id, date, duration_minutes)
        if not free_slot:
            return json.dumps({
                "status": "partial",
                "session_id": None,
                "event_id": None,
                "error": None,
                "conflict": True,
                "conflict_detail": f"No free {duration_minutes}-minute slot found on {date}. "
                                   "Try a different date or reduce session length.",
                "message": f"No free {duration_minutes}-minute slot found on {date}. "
                           "Try a different date or reduce session length.",
            })

        # 2. Create the Google Calendar event via MCP (retry once)
        last_calendar_error = ""
        for attempt in (1, 2):
            try:
                cal_event = await asyncio.wait_for(
                    create_study_calendar_event(
                        user_id=user_id,
                        title=f"Study: {resource_title}",
                        start_time=free_slot["start"],
                        duration_minutes=duration_minutes,
                        description=f"Saarthi study block for '{resource_title}'",
                    ),
                    timeout=12,
                )
            except Exception as cal_exc:
                cal_event = {"event_id": None, "error": str(cal_exc)}

            event_id = (cal_event or {}).get("event_id") or ""
            if event_id:
                logger.info(
                    "Calendar create succeeded (attempt=%s) user_id=%s event_id=%s",
                    attempt, user_id, event_id,
                )
                break

            last_calendar_error = (cal_event or {}).get("error") or "calendar_create_failed"
            logger.error(
                "Calendar create failed (attempt=%s) user_id=%s error=%s",
                attempt, user_id, last_calendar_error,
            )
            if attempt == 1:
                logger.info("Retrying calendar create once for user_id=%s", user_id)
        else:
            pass

        if not event_id:
            return _json_error(
                "Calendar event creation failed; session was not saved.",
                status="error",
                session_id=None,
                event_id=None,
                conflict=None,
                calendar_error=last_calendar_error,
            )

        # 3. Save session to AlloyDB (no blind retry)
        session = StudySession(
            user_id=user_id,
            resource_id=resource_id,
            title=f"Study: {resource_title}",
            scheduled_at=free_slot["start"],
            duration_minutes=duration_minutes,
            calendar_event_id=event_id,
        )
        saved_session = await create_study_session(session)
        if not saved_session:
            logger.error(
                "DB session create failed after calendar success user_id=%s event_id=%s",
                user_id, event_id,
            )
            rolled_back, rollback_error = await _rollback_calendar_event(event_id)
            if rolled_back:
                return _json_error(
                    "DB failed, calendar rolled back",
                    status="error",
                    session_id=None,
                    event_id=event_id,
                    conflict=None,
                )
            return json.dumps({
                "status": "partial",
                "session_id": None,
                "event_id": event_id,
                "error": "DB failed after calendar creation; rollback failed.",
                "conflict": "Calendar event exists but DB failed",
                "rollback_error": rollback_error or None,
            }, default=str)

        if saved_session.get("_idempotency") == "existing":
            logger.info(
                "DB idempotency conflict resolved user_id=%s resource_id=%s scheduled_at=%s existing_session_id=%s",
                user_id, resource_id, free_slot["start"], saved_session.get("id"),
            )
            # We created a fresh calendar event in this request, but DB returned an
            # existing session from a concurrent writer. Roll back new event to avoid orphan.
            rolled_back, rollback_error = await _rollback_calendar_event(event_id)
            if not rolled_back:
                return json.dumps({
                    "status": "partial",
                    "session_id": saved_session.get("id"),
                    "event_id": saved_session.get("calendar_event_id"),
                    "session": saved_session,
                    "error": "Session already existed, but calendar cleanup failed for duplicate event.",
                    "conflict": "Duplicate calendar event may exist for idempotent request",
                    "rollback_error": rollback_error or None,
                }, default=str)
            return json.dumps({
                "status": "ok",
                "session_id": saved_session.get("id"),
                "event_id": saved_session.get("calendar_event_id"),
                "session": saved_session,
                "error": None,
                "conflict": None,
                "message": "Session already exists, returning existing",
            }, default=str)

        logger.info(
            "DB session create succeeded user_id=%s session_id=%s event_id=%s",
            user_id, saved_session.get("id"), event_id,
        )

        return json.dumps({
            "status": "ok",
            "session_id": saved_session.get("id"),
            "event_id": event_id,
            "session": saved_session,
            "calendar_event": cal_event,
            "error": None,
            "conflict": None,
            "message": f"Study session scheduled on {date} at {free_slot['start'].strftime('%I:%M %p')}.",
        }, default=str)
    except Exception as exc:
        logger.exception("tool_schedule_study_session failed user_id=%s", user_id)
        if event_id:
            rolled_back, rollback_error = await _rollback_calendar_event(event_id)
            if not rolled_back:
                return json.dumps({
                    "status": "partial",
                    "session_id": None,
                    "event_id": event_id,
                    "error": f"Failed to schedule study session: {exc}",
                    "conflict": "Calendar event exists but DB failed",
                    "rollback_error": rollback_error or None,
                }, default=str)
        return _json_error(
            "Failed to schedule study session.",
            status="error",
            session_id=None,
            event_id=event_id or None,
            conflict=None,
        )


async def tool_log_study_note(
    user_id: str,
    resource_title: str,
    note_content: str,
    tags: str = "",
) -> str:
    """
    Save a study note to the Notes MCP server.
    Use when the user says 'take a note', 'I learned that...', 'save this'.

    Args:
        user_id:         User UUID.
        resource_title:  Which book/course this note relates to.
        note_content:    The note text to save.
        tags:            Comma-separated topic tags.

    Returns:
        JSON with { "saved": bool, "note_id": str }.
    """
    if not user_id or not resource_title.strip():
        return _json_error("user_id and resource_title are required.")
    if not note_content.strip():
        return _json_error("note_content cannot be empty.")
    try:
        tag_list = [t.strip() for t in tags.split(",") if t.strip()]
        result = await save_learning_note(
            user_id=user_id,
            resource_title=resource_title,
            note_content=note_content,
            tags=tag_list,
        )
        return json.dumps(result)
    except Exception as exc:
        logger.error("tool_log_study_note failed: %s", exc)
        return _json_error("Failed to save study note.")


async def tool_get_notes(user_id: str, resource_title: str = "") -> str:
    """
    Retrieve learning notes from the Notes MCP server.
    Use when the user asks 'show my notes on X', 'what did I write about Y'.

    Args:
        user_id:        User UUID.
        resource_title: Optional filter — leave blank to get all learning notes.

    Returns:
        JSON list of notes.
    """
    if not user_id:
        return _json_error("user_id is required.")
    try:
        notes = await get_learning_notes(user_id, resource_title or None)
        return json.dumps({"notes": notes, "count": len(notes)}, default=str)
    except Exception as exc:
        logger.error("tool_get_notes failed: %s", exc)
        return _json_error("Failed to fetch notes.")


async def tool_mark_session_done(
    user_id: str,
    session_id: str,
    notes: str = "",
) -> str:
    """
    Mark a study session as completed.
    Use when the user says 'done with today's study', 'completed my session'.

    Args:
        user_id:    User UUID.
        session_id: UUID of the study session.
        notes:      Optional notes about what was studied.

    Returns:
        JSON with the updated session.
    """
    if not user_id or not session_id:
        return _json_error("user_id and session_id are required.")
    try:
        updated = await mark_session_complete(session_id, user_id, notes)
        if not updated:
            return _json_error("Session not found or not owned by user.")
        return json.dumps({"completed": True, "session": updated}, default=str)
    except Exception as exc:
        logger.error("tool_mark_session_done failed: %s", exc)
        return _json_error("Failed to mark session complete.")


async def tool_query_learning_history(user_id: str, question: str) -> str:
    """
    Query the user's learning history using AlloyDB AI natural language.
    Use for questions like: 'How many hours did I study last month?',
    'Which courses have I paused?', 'What did I complete this year?'

    Args:
        user_id:  User UUID.
        question: Natural language question about their learning history.

    Returns:
        JSON with { "question", "generated_sql", "results" }.
    """
    if not user_id:
        return _json_error("user_id is required.")
    if not question.strip():
        return _json_error("question is required.")
    result = await query_learning_history_safe(user_id, question)
    return json.dumps(result, default=str)


async def tool_create_study_goal(
    user_id: str,
    title: str,
    target_date: str,
    weekly_hours_target: float,
    resource_id: str = "",
) -> str:
    """
    Create a high-level learning goal (e.g. 'Finish Python book by June').
    Use when the user sets a long-term learning objective.

    Args:
        user_id:              User UUID.
        title:                Goal description.
        target_date:          ISO date string e.g. '2026-06-30'.
        weekly_hours_target:  Hours per week to invest.
        resource_id:          Optional UUID of the linked resource.

    Returns:
        JSON with the created goal.
    """
    if not user_id or not title.strip():
        return _json_error("user_id and title are required.")
    if weekly_hours_target <= 0:
        return _json_error("weekly_hours_target must be > 0.")
    if target_date and not _is_valid_date_string(target_date):
        return _json_error("target_date must be a valid ISO date (YYYY-MM-DD).")

    goal = StudyGoal(
        user_id=user_id,
        title=title,
        target_date=target_date,
        weekly_hours_target=weekly_hours_target,
        resource_id=resource_id or None,
    )
    created = await create_study_goal(goal)
    return json.dumps({"created": True, "goal": created}, default=str)

# =============================================================================
# TOOL 10 — SKILL GAP ANALYSIS
# =============================================================================
 
async def tool_analyze_skill_gap(user_id: str, role_name: str) -> str:
    """
    Analyze the gap between the user's current skills and the skills required
    for a specific career role. Returns what they are missing and what they
    already have.
 
    Use this when the user asks:
      - "What skills am I missing to become a data engineer?"
      - "How ready am I to be a cloud engineer?"
      - "What do I need to learn to switch to ML?"
      - "Skill gap for [role]"
 
    Available roles: Data Engineer, ML Engineer, Cloud Engineer, Backend Developer.
    If the user names a role not in this list, pick the closest match.
 
    Args:
        user_id:   The user's UUID string.
        role_name: Career role to analyse against e.g. "Data Engineer".
 
    Returns:
        JSON with missing_required, missing_recommended, matched skills,
        readiness_pct (0-100), and a gap_score.
    """
    if not user_id or not role_name.strip():
        return _json_error("user_id and role_name are required.")

    # Check if role exists; suggest available roles if not found
    available = await get_available_roles()
    available_lower = [r.lower() for r in available]
 
    if role_name.lower() not in available_lower:
        return json.dumps({
            "error": f"Role '{role_name}' not found.",
            "available_roles": available,
            "suggestion": f"Try one of: {', '.join(available)}",
        })
 
    # Match to exact casing
    exact_role = available[[r.lower() for r in available].index(role_name.lower())]
 
    gap = await compute_skill_gap(user_id, exact_role)
    user_skills = await get_user_skills(user_id)
 
    return json.dumps({
        "role": exact_role,
        "readiness_pct": gap["readiness_pct"],
        "gap_score": gap["gap_score"],
        "skills_you_have": gap["matched"],
        "missing_required": gap["missing_required"],
        "missing_recommended": gap["missing_recommended"],
        "your_current_skills": [
            {"skill": s["skill_name"], "level": s["proficiency"]}
            for s in user_skills
        ],
        "next_step": (
            f"Focus on: {gap['missing_required'][0]}"
            if gap["missing_required"] else
            "You have all required skills! Work on recommended ones next."
        ),
    }, default=str)
 
 
# =============================================================================
# TOOL 11 — SPACED REPETITION / FLASHCARD REVIEW
# =============================================================================
 
async def tool_schedule_flashcard_review(
    user_id: str,
    action: str,
    resource_id: str = "",
    question: str = "",
    answer: str = "",
    flashcard_id: str = "",
    quality: int = 3,
) -> str:
    """
    Manage flashcards for spaced repetition learning.
    Supports three actions: 'due' | 'create' | 'review'
 
    Use 'due'    when user asks: "What flashcards do I need to review?",
                                 "Show me today's review cards"
    Use 'create' when user asks: "Create a flashcard for [question] / [answer]",
                                 "Add this to my flashcards"
    Use 'review' when user says: "I got that right" / "I struggled with that"
                                  (requires flashcard_id and quality 0-5)
 
    Quality scale for 'review':
        0 = complete blackout
        1 = wrong, but remembered on seeing answer
        2 = wrong, but easy to recall
        3 = correct with effort
        4 = correct with small hesitation
        5 = perfect recall
 
    Args:
        user_id:      The user's UUID string.
        action:       "due" | "create" | "review"
        resource_id:  UUID of the resource (required for 'create').
        question:     Flashcard front (required for 'create').
        answer:       Flashcard back (required for 'create').
        flashcard_id: UUID of the flashcard (required for 'review').
        quality:      Review quality 0-5 (required for 'review', default 3).
 
    Returns:
        JSON with flashcard data and next review schedule.
    """
    if not user_id:
        return _json_error("user_id is required.")

    if action == "due":
        due_cards = await get_due_flashcards(user_id, limit=10)
        stats     = await get_flashcard_stats(user_id)
        return json.dumps({
            "action": "due",
            "due_count": len(due_cards),
            "cards": due_cards,
            "stats": dict(stats),
            "message": (
                f"{len(due_cards)} cards due for review."
                if due_cards else
                "No cards due right now — great job staying on top of reviews!"
            ),
        }, default=str)
 
    elif action == "create":
        if not resource_id or not question or not answer:
            return json.dumps({
                "error": "resource_id, question, and answer are required to create a flashcard."
            })
        card = await create_flashcard(user_id, resource_id, question, answer)
        if not card:
            return _json_error("Could not create flashcard. Ensure resource_id belongs to this user.")
        return json.dumps({
            "action": "created",
            "card": dict(card),
            "message": f"Flashcard created. First review due: now.",
        }, default=str)
 
    elif action == "review":
        if not flashcard_id:
            return json.dumps({"error": "flashcard_id is required for review action."})
        if quality < 0 or quality > 5:
            return _json_error("quality must be between 0 and 5.")
        updated = await update_flashcard_after_review(flashcard_id, user_id, quality)
        if not updated:
            return _json_error("Flashcard not found, not owned by user, or invalid quality.")
        next_review = updated.get("next_review_at", "")
        interval    = updated.get("interval_days", 1)
        return json.dumps({
            "action": "reviewed",
            "quality": quality,
            "result": "correct" if quality >= 3 else "needs_more_practice",
            "next_review_in_days": interval,
            "next_review_at": str(next_review),
            "card": dict(updated),
        }, default=str)
 
    return json.dumps({"error": f"Unknown action '{action}'. Use: due | create | review"})
 
 
# =============================================================================
# TOOL 12 — COURSE RECOMMENDATIONS
# =============================================================================
 
async def tool_recommend_resources(user_id: str, goal: str = "") -> str:
    """
    Recommend what the user should study next based on their current resources,
    completed topics, active goals, and skill gaps.
 
    Use this when the user asks:
      - "What should I study next?"
      - "Recommend a course for me"
      - "What should I focus on to become a data engineer?"
      - "What's the best next step in my learning?"
 
    This tool gathers the user's full learning context and passes it to
    Gemini for intelligent recommendations. It does NOT call an external API
    — the recommendation is generated by the agent itself using AlloyDB data.
 
    Args:
        user_id: The user's UUID string.
        goal:    Optional goal context e.g. "become a data engineer" or
                 "pass the GCP exam". Leave blank for general recommendations.
 
    Returns:
        JSON with the user's learning context ready for the agent to reason over.
        The agent will generate the actual recommendations in its response.
    """
    if not user_id:
        return _json_error("user_id is required.")

    context = await get_recommendation_context(user_id)
    skill_gap = None
 
    # If a role is mentioned in the goal, compute the skill gap
    role_keywords = {
        "data engineer": "Data Engineer",
        "ml engineer": "ML Engineer",
        "machine learning": "ML Engineer",
        "cloud engineer": "Cloud Engineer",
        "backend": "Backend Developer",
        "backend developer": "Backend Developer",
    }
    for keyword, role in role_keywords.items():
        if keyword in goal.lower():
            skill_gap = await compute_skill_gap(user_id, role)
            break
 
    return json.dumps({
        "recommendation_context": {
            "user_goal": goal or "general improvement",
            "completed_resources": context["completed"],
            "in_progress_resources": context["in_progress"],
            "active_goals": context["goals"],
            "current_skills": context["skills"],
            "skill_gap": skill_gap,
        },
        "instruction_for_agent": (
            "Based on the above context, recommend 3 specific resources the user "
            "should study next. For each: give a title, explain WHY it fits their "
            "current level and goals, and estimate weekly hours needed. "
            "Prioritise filling skill gaps if present."
        ),
    }, default=str)
 
 
# =============================================================================
# TOOL 13 — LEARNING PATH / ROADMAP
# =============================================================================
 
async def tool_create_learning_path(
    user_id: str,
    action: str,
    title: str = "",
    target_role: str = "",
    path_id: str = "",
    step_order: int = 0,
    step_status: str = "",
) -> str:
    """
    Create and manage structured learning paths (roadmaps) toward a goal or role.
 
    Supports three actions: 'create' | 'view' | 'update_step'
 
    Use 'create'      when user says: "Create a learning path to become a data engineer",
                                      "Build me a roadmap for GCP certification",
                                      "Make a structured plan to learn ML"
 
    Use 'view'        when user says: "Show my learning path",
                                      "What's my roadmap?", "Show all my paths"
 
    Use 'update_step' when user says: "I finished step 2 of my path",
                                      "Mark step 3 as done", "Skip step 1"
 
    When action='create', the agent automatically:
      1. Computes the skill gap for target_role (if provided)
      2. Selects resources from learning_resources that fill the gaps
      3. Orders them from foundational → advanced
      4. Creates the path and saves all steps to AlloyDB
 
    Args:
        user_id:     The user's UUID string.
        action:      "create" | "view" | "update_step"
        title:       Path title (for 'create') e.g. "Road to Data Engineer"
        target_role: Career goal (for 'create') e.g. "Data Engineer"
        path_id:     UUID of the path (for 'view' single path or 'update_step')
        step_order:  Step number to update (for 'update_step')
        step_status: New status for the step: completed | in_progress | skipped
 
    Returns:
        JSON with the full path, steps, and progress percentage.
    """
    if not user_id:
        return _json_error("user_id is required.")

    def _tokenize(text: str) -> set[str]:
        parts = re.findall(r"[a-z0-9]+", (text or "").lower())
        return {p for p in parts if len(p) >= 2}

    def _resource_score_for_skill(res: dict, skill: str) -> int:
        skill_tokens = _tokenize(skill)
        title_tokens = _tokenize(str(res.get("title", "")))
        tag_tokens: set[str] = set()
        tags = res.get("tags") or []
        if isinstance(tags, list):
            for t in tags:
                tag_tokens.update(_tokenize(str(t)))
        haystack = title_tokens | tag_tokens

        overlap = len(skill_tokens & haystack)
        score = overlap * 10
        skill_lower = skill.lower()
        title_lower = str(res.get("title", "")).lower()
        if skill_lower in title_lower:
            score += 15
        if any(skill_lower in str(t).lower() for t in tags):
            score += 20

        # Prefer resources that are not completed for actionable roadmap steps.
        status = str(res.get("status", ""))
        status_bonus = {
            "not_started": 3,
            "in_progress": 2,
            "paused": 1,
            "completed": 0,
        }.get(status, 0)
        return score + status_bonus

    if action == "create":
        # Step 1 — compute skill gap if role provided
        gap_data = None
        if target_role:
            available = await get_available_roles()
            if target_role.lower() in [r.lower() for r in available]:
                gap_data = await compute_skill_gap(user_id, target_role)
 
        # Step 2 — get user's existing resources to build steps from
        resources = await get_learning_resources_for_path(user_id)
 
        # Step 3 — create the path container
        path_title = title or f"Learning Path: {target_role or 'My Roadmap'}"
        required_missing = gap_data.get("missing_required", []) if gap_data else []
        recommended_missing = gap_data.get("missing_recommended", []) if gap_data else []

        # Build a deterministic, skill-driven plan:
        #   - required skills first
        #   - recommended skills second
        used_resource_ids: set[str] = set()
        step_plan: list[dict[str, Any]] = []
        ordered_skills = [("required", s) for s in required_missing] + [("recommended", s) for s in recommended_missing]

        for priority, skill in ordered_skills:
            scored: list[tuple[int, dict[str, Any]]] = []
            for res in resources:
                if res.get("id") in used_resource_ids:
                    continue
                score = _resource_score_for_skill(res, skill)
                if score > 0:
                    scored.append((score, res))

            scored.sort(key=lambda x: (-x[0], str(x[1].get("title", "")).lower()))
            top_matches = [r for _, r in scored[:2]]
            if top_matches:
                used_resource_ids.add(top_matches[0].get("id"))
                step_plan.append({
                    "skill": skill,
                    "priority": priority,
                    "resources": [
                        {
                            "id": r.get("id"),
                            "title": r.get("title"),
                            "resource_type": r.get("resource_type"),
                            "status": r.get("status"),
                        }
                        for r in top_matches
                    ],
                    "reason": (
                        f"Targets missing {priority} skill '{skill}'. "
                        f"Highest-signal match from your existing resources."
                    ),
                    "missing_resource": False,
                })
            else:
                # Mark explicitly rather than creating an empty hidden gap.
                step_plan.append({
                    "skill": skill,
                    "priority": priority,
                    "resources": [],
                    "reason": (
                        f"'{skill}' is a missing {priority} skill, but no matching resource "
                        "was found in your library."
                    ),
                    "missing_resource": True,
                })

        # Fallback when no gap/role context exists: deterministic resource sequence
        if not step_plan:
            fallback_resources = sorted(
                resources,
                key=lambda r: (
                    {"not_started": 0, "in_progress": 1, "paused": 2, "completed": 3}.get(str(r.get("status", "")), 9),
                    str(r.get("title", "")).lower(),
                ),
            )
            for res in fallback_resources:
                step_plan.append({
                    "skill": "General progression",
                    "priority": "recommended",
                    "resources": [{
                        "id": res.get("id"),
                        "title": res.get("title"),
                        "resource_type": res.get("resource_type"),
                        "status": res.get("status"),
                    }],
                    "reason": "No explicit skill gap provided; using your current learning resources in a structured order.",
                    "missing_resource": False,
                })

        actionable_steps = [s for s in step_plan if s.get("resources")]
        estimated_weeks = max(4, len(actionable_steps) * 2) if step_plan else 8
 
        path = await create_learning_path(
            user_id=user_id,
            title=path_title,
            description=f"Structured roadmap toward: {target_role or title}",
            target_role=target_role or None,
            estimated_weeks=estimated_weeks,
        )
 
        # Step 4 — persist one DB step per actionable skill step
        steps_created = []
        step_order_counter = 1
        for plan_step in step_plan:
            if not plan_step.get("resources"):
                continue
            primary = plan_step["resources"][0]
            step = await add_path_step(
                path_id=path["id"],
                resource_id=primary["id"],
                step_order=step_order_counter,
                title=f"{plan_step['skill']}: {primary['title']}",
                why_this=plan_step["reason"],
                estimated_hours=10 if primary.get("resource_type") == "course" else 4,
            )
            steps_created.append(step)
            step_order_counter += 1
 
        summary = (
            f"Built a skill-driven roadmap for {target_role}: "
            f"{len(required_missing)} required and {len(recommended_missing)} recommended gaps analyzed; "
            f"{len(steps_created)} actionable steps created."
            if target_role else
            f"Built a structured roadmap with {len(steps_created)} actionable steps from your learning resources."
        )

        return json.dumps({
            "action": "created",
            "path": path,
            "steps": step_plan,
            "db_steps": steps_created,
            "total_steps": len(steps_created),
            "estimated_weeks": estimated_weeks,
            "skill_gap_addressed": gap_data,
            "summary": summary,
            "message": summary,
        }, default=str)
 
    elif action == "view":
        if path_id:
            # View a single path with all steps
            path = await get_learning_path(user_id, path_id)
            return json.dumps({"action": "view", "path": path}, default=str)
        else:
            # View all paths
            paths = await get_all_learning_paths(user_id)
            return json.dumps({
                "action": "view_all",
                "paths": paths,
                "count": len(paths),
            }, default=str)
 
    elif action == "update_step":
        if not path_id or not step_order or not step_status:
            return json.dumps({
                "error": "path_id, step_order, and step_status are required for update_step."
            })
        if step_status not in ALLOWED_PATH_STEP_STATUSES:
            return _json_error(
                "Invalid step_status.",
                allowed=list(sorted(ALLOWED_PATH_STEP_STATUSES)),
            )
        updated = await update_path_step_status(user_id, path_id, step_order, step_status)
        if not updated:
            return _json_error("Path step not found or not owned by user.")
        path    = await get_learning_path(user_id, path_id)
        return json.dumps({
            "action": "step_updated",
            "step": updated,
            "path_progress_pct": path.get("progress_pct", 0),
            "message": f"Step {step_order} marked as {step_status}.",
        }, default=str)
 
    return json.dumps({"error": f"Unknown action '{action}'. Use: create | view | update_step"})


# ── Agent Definition ──────────────────────────────────────────────────────────

LEARNING_AGENT_INSTRUCTION = """
You are the Learning Agent for Saarthi AI — a personal AI life operating system.
 
Your domain: everything related to the user's learning journey.
This includes books, online courses, articles, videos, study schedules,
learning notes, streaks, progress, skill gaps, flashcards, course
recommendations, and structured learning paths / roadmaps.
 
YOUR TOOLS (13 total):
 
Core tools (original):
- tool_get_learning_status       → full snapshot (call this first for any status query)
- tool_add_learning_resource     → add a new book/course/article
- tool_update_progress           → update % or page on a resource
- tool_schedule_study_session    → book a study block on the calendar
- tool_log_study_note            → save notes to Notes MCP
- tool_get_notes                 → retrieve past notes
- tool_mark_session_done         → mark a study session completed
- tool_query_learning_history    → natural language query via AlloyDB AI
- tool_create_study_goal         → create a high-level learning goal
 
New tools (additions):
- tool_analyze_skill_gap         → compare user skills vs role requirements
- tool_schedule_flashcard_review → create / review / get due flashcards (SM-2)
- tool_recommend_resources       → suggest what to study next based on context
- tool_create_learning_path      → build / view / update a structured roadmap
 
WHEN TO USE EACH NEW TOOL:
- "What skills am I missing to become X?"   → tool_analyze_skill_gap
- "How ready am I for [role]?"              → tool_analyze_skill_gap
- "What should I study next?"               → tool_recommend_resources
- "Recommend a course for me"               → tool_recommend_resources
- "Create a flashcard for X"                → tool_schedule_flashcard_review(action='create')
- "What cards do I need to review today?"   → tool_schedule_flashcard_review(action='due')
- "I got that right / I struggled"         → tool_schedule_flashcard_review(action='review')
- "Create a roadmap to become a data eng." → tool_create_learning_path(action='create')
- "Show my learning path"                   → tool_create_learning_path(action='view')
- "I finished step 2 of my path"           → tool_create_learning_path(action='update_step')
 
CONFLICT DETECTION RULES — check for these and flag them:
1. Study session clashes with an existing calendar event
   → flag: "Study block on [DATE] overlaps with [EVENT]"
2. Weekly study hours < 50% of the user's goal target
   → flag: "Study hours this week ([X]h) are below your [Y]h weekly target"
3. A resource has been 'in_progress' for > 30 days with 0% progress change
   → flag: "Stalled resource: '[TITLE]' has had no progress for 30+ days"
4. Goal target date is within 7 days and progress < 80%
   → flag: "Goal '[TITLE]' is due in [N] days but only [X]% complete"
5. Skill gap score > 70% for user's stated career goal
   → flag: "Large skill gap detected for [ROLE]: missing [N] required skills"
6. Flashcards overdue by more than 3 days
   → flag: "[N] flashcards are overdue — spaced repetition effectiveness dropping"
 
RESPONSE FORMAT:
Always return valid JSON matching the AgentResponse schema:
{
  "agent": "learning_agent",
  "status": "ok" | "error" | "partial",
  "summary": "One paragraph human-readable summary",
  "conflicts": ["list of flagged conflicts"],
  "actions_taken": ["list of actions you took"],
  "data": { ...raw structured data for the orchestrator... }
}

Return ONLY valid JSON.
Do NOT call functions.
Do NOT use tool calls.
 
TONE: Encouraging, specific, data-backed. Mention exact titles, percentages,
dates, skill names. Never be vague. Celebrate streaks and milestones.
"""

learning_agent = Agent(
    name="learning_agent",
    model="gemini-2.5-flash",
    description=(
        "Manages the user's learning journey — books, courses, study schedules, "
        "notes, streaks, and progress. Detects conflicts between study sessions "
        "and other calendar events. Uses Calendar MCP and Notes MCP."
    ),
    instruction=LEARNING_AGENT_INSTRUCTION,
    tools=[
        tool_get_learning_status,
        tool_add_learning_resource,
        tool_update_progress,
        tool_schedule_study_session,
        tool_log_study_note,
        tool_get_notes,
        tool_mark_session_done,
        tool_query_learning_history,
        tool_create_study_goal,
        tool_analyze_skill_gap,
        tool_schedule_flashcard_review,
        tool_recommend_resources,
        tool_create_learning_path,
    ],
)


# ── Standalone Runner (for testing without the orchestrator) ──────────────────

def _is_goal_orchestration_intent(message: str) -> bool:
    lower = message.lower()
    return (
        ("become" in lower or "roadmap" in lower or "learning path" in lower)
        and bool(_detect_role_from_text(lower))
    )


def _safe_json_loads(payload: str, fallback: dict | None = None) -> dict:
    try:
        parsed = json.loads(payload)
        return parsed if isinstance(parsed, dict) else {}
    except Exception:
        if fallback is not None:
            return fallback
        return {
            "agent": "learning_agent",
            "status": "error",
            "summary": "Invalid LLM response",
            "conflicts": [],
            "actions_taken": [],
            "data": {"raw": payload},
        }


def _parse_tool_output(tool_output: Any) -> tuple[dict[str, Any], list[str]]:
    partial_reasons: list[str] = []

    if isinstance(tool_output, dict):
        return dict(tool_output), partial_reasons

    if isinstance(tool_output, str):
        try:
            parsed = json.loads(tool_output)
            if isinstance(parsed, dict):
                return parsed, partial_reasons
            partial_reasons.append("Tool output was JSON but not an object.")
            return {"raw_output": parsed}, partial_reasons
        except Exception:
            partial_reasons.append("Tool output was not valid JSON.")
            return {"raw_output": tool_output}, partial_reasons

    partial_reasons.append("Tool output type was unexpected.")
    return {"raw_output": str(tool_output)}, partial_reasons


def normalize_agent_response(
    tool_output: dict,
    agent_name: str,
    action: str,
) -> AgentResponse:
    parsed, partial_reasons = _parse_tool_output(tool_output)

    expected_keys_by_action: dict[str, list[str]] = {
        "tool_get_learning_status": [
            "resources", "upcoming_sessions", "active_goals",
            "weekly_hours_studied", "streak_days",
        ],
        "tool_schedule_flashcard_review": ["action"],
        "tool_analyze_skill_gap": ["role", "readiness_pct", "missing_required"],
        "tool_create_learning_path": ["action"],
        "tool_add_learning_resource": ["created"],
        "tool_log_study_note": ["saved"],
        "tool_get_notes": ["notes", "count"],
        "goal_orchestration": ["role", "skill_gap", "recommendations", "learning_path"],
    }

    raw_status = parsed.get("status")
    explicit_status: AgentStatus | None = None
    if isinstance(raw_status, str):
        lowered = raw_status.strip().lower()
        if lowered in {AgentStatus.OK.value, AgentStatus.ERROR.value, AgentStatus.PARTIAL.value}:
            explicit_status = AgentStatus(lowered)

    error_msg = parsed.get("error")
    conflicts: list[str] = []
    actions_taken: list[str] = [action]
    parsed_actions = parsed.get("actions_taken")
    if isinstance(parsed_actions, list):
        for a in parsed_actions:
            a_str = str(a).strip()
            if a_str and a_str not in actions_taken:
                actions_taken.append(a_str)
    expected_keys = expected_keys_by_action.get(action, [])
    missing_keys = [k for k in expected_keys if k not in parsed]
    if missing_keys:
        partial_reasons.append(f"Missing expected fields: {', '.join(missing_keys)}")

    if parsed.get("_fallback"):
        partial_reasons.append("Fallback handling was used.")

    conflict_value = parsed.get("conflict")
    if conflict_value is True:
        partial_reasons.append(parsed.get("message") or "Conflict detected in tool output.")
    elif isinstance(conflict_value, str) and conflict_value.strip():
        conflicts.append(conflict_value.strip())
    elif isinstance(conflict_value, list):
        conflicts.extend(str(c).strip() for c in conflict_value if str(c).strip())

    for flag in ("saved", "created", "completed", "deleted"):
        if flag in parsed and parsed.get(flag) is False:
            partial_reasons.append(f"{flag} flag indicates incomplete execution.")

    calendar_event = parsed.get("calendar_event")
    if isinstance(calendar_event, dict) and not calendar_event.get("event_id"):
        partial_reasons.append("Calendar event details are incomplete.")

    declared_conflicts = parsed.get("conflicts")
    if isinstance(declared_conflicts, list):
        conflicts.extend(str(c) for c in declared_conflicts if str(c).strip())
    elif isinstance(declared_conflicts, str) and declared_conflicts.strip():
        conflicts.append(declared_conflicts.strip())

    conflict_detail = parsed.get("conflict_detail")
    if isinstance(conflict_detail, str) and conflict_detail.strip():
        conflicts.append(conflict_detail.strip())

    issues = parsed.get("issues")
    if isinstance(issues, list):
        partial_reasons.extend(str(i) for i in issues if str(i).strip())

    has_error = isinstance(error_msg, str) and error_msg.strip() != ""
    if has_error:
        conflicts.append(error_msg.strip())

    has_partial_signals = bool(partial_reasons)
    has_conflicts = bool([c for c in conflicts if str(c).strip()])

    # Status resolution (strict order):
    # 1) explicit valid status
    # 2) error
    # 3) partial signals/conflicts
    # 4) default ok
    if explicit_status is not None:
        status = explicit_status
    elif has_error:
        status = AgentStatus.ERROR
    elif has_partial_signals or has_conflicts:
        status = AgentStatus.PARTIAL
    else:
        status = AgentStatus.OK

    # Safety floors:
    # - Never OK when error exists
    # - Never OK when conflicts exist
    # - Never OK when fallback/parse/incomplete signals exist
    if has_error and status == AgentStatus.OK:
        status = AgentStatus.ERROR
    if (has_conflicts or has_partial_signals) and status == AgentStatus.OK:
        status = AgentStatus.PARTIAL

    if has_partial_signals:
        conflicts.extend(partial_reasons)

    if status == AgentStatus.ERROR:
        summary = parsed.get("summary") or parsed.get("message") or (
            f"{action} failed: {error_msg.strip()}" if has_error else f"{action} failed."
        )
    elif status == AgentStatus.PARTIAL:
        summary = parsed.get("summary") or parsed.get("message") or f"{action} completed partially."
    else:
        summary = parsed.get("summary") or parsed.get("message") or f"{action} completed successfully."

    # Deduplicate conflicts while preserving order
    deduped_conflicts: list[str] = []
    for c in conflicts:
        if c and c not in deduped_conflicts:
            deduped_conflicts.append(c)

    return AgentResponse(
        agent=agent_name,
        status=status,
        summary=summary,
        conflicts=deduped_conflicts,
        actions_taken=actions_taken,
        data=parsed,
    )


def _extract_model_parts(result: Any) -> tuple[str, list[dict[str, Any]]]:
    """
    Extract plain text and function_call payloads from Gemini-style output parts.
    """
    text_chunks: list[str] = []
    function_calls: list[dict[str, Any]] = []

    candidates = getattr(result, "candidates", None) or []
    if candidates:
        content = getattr(candidates[0], "content", None)
        parts = getattr(content, "parts", None) or []
        for part in parts:
            part_text = getattr(part, "text", None)
            if isinstance(part_text, str) and part_text.strip():
                text_chunks.append(part_text)

            function_call = getattr(part, "function_call", None)
            if function_call:
                function_calls.append({
                    "name": getattr(function_call, "name", ""),
                    "args": getattr(function_call, "args", {}),
                })

    if not text_chunks:
        raw_text = getattr(result, "text", "")
        if isinstance(raw_text, str) and raw_text.strip():
            text_chunks.append(raw_text)

    return "\n".join(text_chunks).strip(), function_calls


def _structured_intent(message: str) -> str | None:
    msg = message.strip()

    if _is_goal_orchestration_intent(msg):
        return "goal_orchestration"

    if re.match(r"^save.*?note.*?for\s+.+?:\s+.+", msg, re.IGNORECASE | re.DOTALL):
        return "save_note"

    if re.match(r"^(show|get)\s+(my\s+)?notes(\s+(for|on|about)\s+.+)?$", msg, re.IGNORECASE):
        return "get_notes"

    if re.match(
        r"^update learning path step:\s*path_id=[^,\s]+,\s*step_id=\d+,\s*status=[a-z_]+$",
        msg,
        re.IGNORECASE,
    ):
        return "update_path_step"

    if re.match(
        r"^create a flashcard:\s*question=\".*?\",\s*answer=\".*?\",\s*resource_id=[^,\s]+$",
        msg,
        re.IGNORECASE | re.DOTALL,
    ):
        return "create_flashcard"

    return None


def route_learning_request(message: str) -> str:
    """
    Route requests between deterministic flows and ADK runner.
    Returns: "deterministic" | "adk"
    """
    return "deterministic" if _structured_intent(message) else "adk"


async def _run_deterministic_request(message: str, user_id: str, intent: str) -> AgentResponse:
    msg_lower = message.lower()

    if intent == "goal_orchestration":
        return await _run_goal_orchestration(message, user_id)

    if intent == "create_flashcard":
        m = re.search(
            r"create a flashcard:\s*question=\"(.*?)\",\s*answer=\"(.*?)\",\s*resource_id=([^\s,]+)",
            message,
            re.IGNORECASE | re.DOTALL,
        )
        if not m:
            return normalize_agent_response(
                {"error": "Invalid flashcard command format."},
                "learning_agent",
                "tool_schedule_flashcard_review",
            )
        question, answer, resource_id = m.group(1).strip(), m.group(2).strip(), m.group(3).strip()
        raw = await tool_schedule_flashcard_review(
            user_id=user_id,
            action="create",
            resource_id=resource_id,
            question=question,
            answer=answer,
        )
        data = _safe_json_loads(raw, fallback={"_fallback": True, "raw_output": raw})
        if data.get("action") == "created":
            data["message"] = "Flashcard created successfully."
        return normalize_agent_response(data, "learning_agent", "tool_schedule_flashcard_review")

    if intent == "save_note":
        for_match = re.search(r"save.*?note.*?for\s+(.+?):\s+(.+)", message, re.IGNORECASE | re.DOTALL)
        if not for_match:
            return normalize_agent_response(
                {"error": "Invalid note command format."},
                "learning_agent",
                "tool_log_study_note",
            )
        resource_title = for_match.group(1).strip()
        note_content = for_match.group(2).strip()
        raw = await tool_log_study_note(
            user_id=user_id,
            resource_title=resource_title,
            note_content=note_content,
        )
        data = _safe_json_loads(raw, fallback={"_fallback": True, "raw_output": raw})
        if data.get("saved"):
            data["message"] = f"Note saved for '{resource_title}'."
        else:
            data["message"] = f"Failed to save note: {data.get('error', 'unknown error')}"
        return normalize_agent_response(data, "learning_agent", "tool_log_study_note")

    if intent == "get_notes":
        resource_match = re.search(r"(?:notes? on|notes? about|notes? for)\s+([A-Za-z][^,\.]+)", message, re.IGNORECASE)
        resource_title = resource_match.group(1).strip() if resource_match else ""
        raw = await tool_get_notes(user_id=user_id, resource_title=resource_title)
        data = _safe_json_loads(raw, fallback={"_fallback": True, "raw_output": raw})
        count = data.get("count", 0)
        data["message"] = f"Found {count} note(s)" + (f" for '{resource_title}'." if resource_title else ".")
        return normalize_agent_response(data, "learning_agent", "tool_get_notes")

    if intent == "update_path_step":
        m = re.search(
            r"path_id=([^,\s]+),\s*step_id=(\d+),\s*status=([a-z_]+)",
            message,
            re.IGNORECASE,
        )
        if not m:
            return normalize_agent_response(
                {"error": "Invalid path step update format."},
                "learning_agent",
                "tool_create_learning_path",
            )
        path_id, step_order, step_status = m.group(1).strip(), int(m.group(2)), m.group(3).strip().lower()
        raw = await tool_create_learning_path(
            user_id=user_id,
            action="update_step",
            path_id=path_id,
            step_order=step_order,
            step_status=step_status,
        )
        data = _safe_json_loads(raw, fallback={"_fallback": True, "raw_output": raw})
        return normalize_agent_response(data, "learning_agent", "tool_create_learning_path")

    return normalize_agent_response(
        {"error": f"Unsupported deterministic intent: {intent}"},
        "learning_agent",
        "deterministic_dispatch",
    )


async def _run_goal_orchestration(message: str, user_id: str) -> AgentResponse:
    role = _detect_role_from_text(message)
    if not role:
        return normalize_agent_response(
            {
                "message": "Could not detect a target role from your message.",
                "_fallback": True,
                "input_message": message,
            },
            "learning_agent",
            "goal_orchestration",
        )

    actions_taken: list[str] = []
    issues: list[str] = []

    gap = _safe_json_loads(await tool_analyze_skill_gap(user_id, role), fallback={"_fallback": True})
    actions_taken.append(f"Analyzed skill gap for role: {role}")
    if gap.get("error"):
        issues.append(str(gap["error"]))

    recommendations = _safe_json_loads(
        await tool_recommend_resources(user_id, goal=f"become a {role}"),
        fallback={"_fallback": True},
    )
    actions_taken.append("Built recommendation context")
    if recommendations.get("error"):
        issues.append(str(recommendations["error"]))

    path_resp = _safe_json_loads(
        await tool_create_learning_path(
            user_id=user_id,
            action="create",
            title=f"Road to {role}",
            target_role=role,
        ),
        fallback={"_fallback": True},
    )
    actions_taken.append("Created learning path")
    if path_resp.get("error"):
        issues.append(str(path_resp["error"]))

    schedule_resp = {}
    steps = path_resp.get("steps") or []
    if steps:
        first_step = steps[0]
        tomorrow = (datetime.utcnow().date() + timedelta(days=1)).isoformat()
        schedule_resp = _safe_json_loads(
            await tool_schedule_study_session(
                user_id=user_id,
                resource_id=first_step.get("resource_id", ""),
                resource_title=first_step.get("title", "Learning Session"),
                date=tomorrow,
                duration_minutes=60,
            ),
            fallback={"_fallback": True},
        )
        actions_taken.append("Scheduled first study session")
        if schedule_resp.get("error"):
            issues.append(str(schedule_resp["error"]))
        if schedule_resp.get("conflict"):
            issues.append(schedule_resp.get("message", "Unable to schedule first study session"))

    response = normalize_agent_response(
        {
            "role": role,
            "skill_gap": gap,
            "recommendations": recommendations,
            "learning_path": path_resp,
            "first_session": schedule_resp,
            "issues": issues,
            "message": (
                f"Prepared a learning plan toward {role}: analyzed gaps, generated recommendations, created a roadmap, and scheduled the first session."
                if not issues else
                f"Prepared a partial learning plan toward {role}; some steps need attention."
            ),
        },
        "learning_agent",
        "goal_orchestration",
    )
    response.actions_taken = actions_taken
    return response


# Module-level session service — shared across all calls
_session_service = InMemorySessionService()
APP_NAME = "saarthi_learning_agent"


async def run_learning_agent(message: str, user_id: str) -> AgentResponse:
    """
    Run the learning agent directly (used for unit tests and the demo endpoint).
    In production the orchestrator calls this agent via sub_agents=[learning_agent].
    """
    if not user_id:
        return normalize_agent_response(
            {"error": "Missing required user_id."},
            "learning_agent",
            "run_learning_agent",
        )

    route = route_learning_request(message)
    logger.info("Learning agent routing decision route=%s user_id=%s", route, user_id)

    if route == "deterministic":
        intent = _structured_intent(message) or "unknown"
        logger.info("Learning agent executing deterministic flow intent=%s user_id=%s", intent, user_id)
        try:
            return await _run_deterministic_request(message, user_id, intent)
        except Exception as exc:
            logger.exception("Deterministic flow failed intent=%s user_id=%s", intent, user_id)
            return normalize_agent_response(
                {
                    "error": f"Deterministic flow failed: {exc}",
                    "summary": f"Deterministic flow failed for intent '{intent}'.",
                    "intent": intent,
                    "message": message,
                    "user_id": user_id,
                },
                "learning_agent",
                "deterministic_dispatch",
            )

    logger.info("Learning agent executing ADK runner path user_id=%s", user_id)
    try:
        runner = Runner(
            agent=learning_agent,
            app_name=APP_NAME,
            session_service=_session_service,
        )
        session_id = str(uuid.uuid4())
        await _session_service.create_session(
            app_name=APP_NAME,
            user_id=user_id,
            session_id=session_id,
        )

        content = types.Content(
            role="user",
            parts=[types.Part(text=message)],
        )

        text_chunks: list[str] = []
        function_calls: list[dict[str, Any]] = []

        async for event in runner.run_async(
            user_id=user_id,
            session_id=session_id,
            new_message=content,
        ):
            if not event.is_final_response():
                continue

            parts = getattr(getattr(event, "content", None), "parts", None) or []
            for part in parts:
                part_text = getattr(part, "text", None)
                if isinstance(part_text, str) and part_text.strip():
                    text_chunks.append(part_text)

                function_call = getattr(part, "function_call", None)
                if function_call:
                    function_calls.append({
                        "name": getattr(function_call, "name", ""),
                        "args": getattr(function_call, "args", {}),
                    })
            break

        text_payload = "\n".join(text_chunks).strip()
        cleaned = text_payload.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```[a-z]*\n?", "", cleaned)
            cleaned = re.sub(r"\n?```$", "", cleaned)
            cleaned = cleaned.strip()

        if function_calls:
            logger.warning("Function call detected in learning agent output: %s", function_calls)

        raw = _safe_json_loads(cleaned)
        if function_calls:
            data = raw.get("data") if isinstance(raw.get("data"), dict) else {}
            data["function_calls"] = function_calls
            raw["data"] = data
        return normalize_agent_response(raw, "learning_agent", "llm_runner")

    except ValueError:
        return normalize_agent_response(
            {
                "message": "Model response was not valid AgentResponse JSON.",
                "_fallback": True,
                "raw_text": text_payload if "text_payload" in locals() else "",
                "function_calls": function_calls if "function_calls" in locals() else [],
            },
            "learning_agent",
            "llm_runner",
        )
    except Exception as exc:
        logger.error("Learning agent error: %s", exc)
        return normalize_agent_response(
            {"error": f"Learning agent encountered an error: {exc}"},
            "learning_agent",
            "llm_runner",
        )
