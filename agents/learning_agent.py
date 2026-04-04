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
from datetime import datetime, timedelta
import uuid

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

    cal_event = None
    try:
        # 1. Find a free slot on that date
        free_slot = await find_free_slot(user_id, date, duration_minutes)
        if not free_slot:
            return json.dumps({
                "conflict": True,
                "message": f"No free {duration_minutes}-minute slot found on {date}. "
                           "Try a different date or reduce session length.",
            })

        # 2. Create the Google Calendar event via MCP
        cal_event = await create_study_calendar_event(
            user_id=user_id,
            title=f"Study: {resource_title}",
            start_time=free_slot["start"],
            duration_minutes=duration_minutes,
            description=f"Saarthi study block for '{resource_title}'",
        )

        # 3. Save session to AlloyDB
        session = StudySession(
            user_id=user_id,
            resource_id=resource_id,
            title=f"Study: {resource_title}",
            scheduled_at=free_slot["start"],
            duration_minutes=duration_minutes,
            calendar_event_id=cal_event.get("event_id"),
        )
        saved_session = await create_study_session(session)
        if not saved_session:
            if cal_event and cal_event.get("event_id"):
                try:
                    await delete_calendar_event(user_id, cal_event["event_id"])
                except Exception:
                    logger.warning("Calendar rollback failed for event_id=%s", cal_event["event_id"])
            return _json_error("Unable to save study session. Resource may be invalid for this user.")

        return json.dumps({
            "conflict": False,
            "session": saved_session,
            "calendar_event": cal_event,
            "message": f"Study session scheduled on {date} at {free_slot['start'].strftime('%I:%M %p')}.",
        }, default=str)
    except Exception as exc:
        logger.error("tool_schedule_study_session failed: %s", exc)
        if cal_event and cal_event.get("event_id"):
            try:
                await delete_calendar_event(user_id, cal_event["event_id"])
            except Exception:
                logger.warning("Calendar rollback failed for event_id=%s", cal_event["event_id"])
        return _json_error("Failed to schedule study session.")


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
        estimated_weeks = len(resources) * 2 if resources else 8
 
        path = await create_learning_path(
            user_id=user_id,
            title=path_title,
            description=f"Structured roadmap toward: {target_role or title}",
            target_role=target_role or None,
            estimated_weeks=estimated_weeks,
        )
 
        # Step 4 — add each resource as a step
        steps_created = []
        for i, res in enumerate(resources, start=1):
            step = await add_path_step(
                path_id=path["id"],
                resource_id=res["id"],
                step_order=i,
                title=res["title"],
                why_this=(
                    f"Covers skills needed for {target_role}."
                    if target_role else
                    "Part of your structured learning sequence."
                ),
                estimated_hours=10 if res["resource_type"] == "course" else 4,
            )
            steps_created.append(step)
 
        return json.dumps({
            "action": "created",
            "path": path,
            "steps": steps_created,
            "total_steps": len(steps_created),
            "estimated_weeks": estimated_weeks,
            "skill_gap_addressed": gap_data,
            "message": (
                f"Learning path '{path_title}' created with "
                f"{len(steps_created)} steps. "
                f"Estimated completion: {estimated_weeks} weeks."
            ),
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


def _safe_json_loads(payload: str) -> dict:
    try:
        parsed = json.loads(payload)
        return parsed if isinstance(parsed, dict) else {}
    except Exception:
        return {}


async def _run_goal_orchestration(message: str, user_id: str) -> AgentResponse:
    role = _detect_role_from_text(message)
    if not role:
        return AgentResponse(
            agent="learning_agent",
            status=AgentStatus.PARTIAL,
            summary="Could not detect a target role from your message.",
            conflicts=[],
            actions_taken=[],
            data={"message": message},
        )

    actions_taken: list[str] = []
    conflicts: list[str] = []

    gap = _safe_json_loads(await tool_analyze_skill_gap(user_id, role))
    actions_taken.append(f"Analyzed skill gap for role: {role}")
    if gap.get("error"):
        conflicts.append(gap["error"])

    recommendations = _safe_json_loads(await tool_recommend_resources(user_id, goal=f"become a {role}"))
    actions_taken.append("Built recommendation context")

    path_resp = _safe_json_loads(
        await tool_create_learning_path(
            user_id=user_id,
            action="create",
            title=f"Road to {role}",
            target_role=role,
        )
    )
    actions_taken.append("Created learning path")
    if path_resp.get("error"):
        conflicts.append(path_resp["error"])

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
            )
        )
        actions_taken.append("Scheduled first study session")
        if schedule_resp.get("error"):
            conflicts.append(schedule_resp["error"])
        if schedule_resp.get("conflict"):
            conflicts.append(schedule_resp.get("message", "Unable to schedule first study session"))

    status = AgentStatus.OK if not conflicts else AgentStatus.PARTIAL
    return AgentResponse(
        agent="learning_agent",
        status=status,
        summary=(
            f"Prepared a learning plan toward {role}: analyzed gaps, generated recommendations, created a roadmap, and scheduled the first session."
            if status == AgentStatus.OK
            else f"Prepared a partial learning plan toward {role}; some steps need attention."
        ),
        conflicts=conflicts,
        actions_taken=actions_taken,
        data={
            "role": role,
            "skill_gap": gap,
            "recommendations": recommendations,
            "learning_path": path_resp,
            "first_session": schedule_resp,
        },
    )


# Module-level session service — shared across all calls
_session_service = InMemorySessionService()
APP_NAME = "saarthi_learning_agent"


async def run_learning_agent(message: str, user_id: str) -> AgentResponse:
    """
    Run the learning agent directly (used for unit tests and the demo endpoint).
    In production the orchestrator calls this agent via sub_agents=[learning_agent].
    """
    if not user_id:
        return AgentResponse(
            agent="learning_agent",
            status=AgentStatus.ERROR,
            summary="Missing required user_id.",
            conflicts=[],
            actions_taken=[],
            data=None,
        )

    if _is_goal_orchestration_intent(message):
        try:
            return await _run_goal_orchestration(message, user_id)
        except Exception as exc:
            logger.error("Goal orchestration failed: %s", exc)

    # ── NEW: correct ADK runner pattern ──────────────────────────────────────
    try:
        runner = Runner(
            agent=learning_agent,
            app_name=APP_NAME,
            session_service=_session_service,
        )

        # Each request gets its own session so history doesn't bleed across calls
        session_id = str(uuid.uuid4())
        await _session_service.create_session(
            app_name=APP_NAME,
            user_id=user_id,
            session_id=session_id,
        )

        # Wrap the message in the format ADK expects
        content = types.Content(
            role="user",
            parts=[types.Part(text=message)],
        )

        # run_async returns an async generator — iterate to find the final response
        final_text = ""
        async for event in runner.run_async(
            user_id=user_id,
            session_id=session_id,
            new_message=content,
        ):
            if event.is_final_response():
                if event.content and event.content.parts:
                    final_text = event.content.parts[0].text or ""
                break

        # Parse the JSON the agent returns
        try:
            # Strip markdown code fences if model wraps response in ```json ... ```
            cleaned = final_text.strip()
            if cleaned.startswith("```"):
                cleaned = re.sub(r"^```[a-z]*\n?", "", cleaned)
                cleaned = re.sub(r"\n?```$", "", cleaned)
                cleaned = cleaned.strip()
            raw = json.loads(cleaned)
            return AgentResponse(**raw)
        except (json.JSONDecodeError, ValueError):
            return AgentResponse(
                agent="learning_agent",
                status=AgentStatus.PARTIAL,
                summary=final_text or "Model returned an empty response.",
                conflicts=[],
                actions_taken=[],
                data={"raw_text": final_text},
            )

    except Exception as exc:
        logger.error("Learning agent error: %s", exc)
        return AgentResponse(
            agent="learning_agent",
            status=AgentStatus.ERROR,
            summary=f"Learning agent encountered an error: {exc}",
            conflicts=[],
            actions_taken=[],
            data=None,
        )