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

import json
import logging
from datetime import datetime

from google.adk.agents import Agent
from google.adk.runners import Runner

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
)
from db.alloydb import query_nl
from tools.learning_tools import (
    save_learning_note,
    get_learning_notes,
    create_study_calendar_event,
    get_calendar_events,
    find_free_slot,
)
from db.schemas import (
    AgentResponse,
    AgentStatus,
    LearningResource,
    StudySession,
    StudyGoal,
)

logger = logging.getLogger(__name__)


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
    updated = await update_resource_progress(
        resource_id=resource_id,
        user_id=user_id,
        progress_pct=progress_pct,
        current_page=current_page or None,
    )
    message = "Resource marked as completed!" if progress_pct >= 100 else "Progress updated."
    return json.dumps({"message": message, "resource": updated}, default=str)


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

    return json.dumps({
        "conflict": False,
        "session": saved_session,
        "calendar_event": cal_event,
        "message": f"Study session scheduled on {date} at {free_slot['start'].strftime('%I:%M %p')}.",
    }, default=str)


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
    tag_list = [t.strip() for t in tags.split(",") if t.strip()]
    result = await save_learning_note(
        user_id=user_id,
        resource_title=resource_title,
        note_content=note_content,
        tags=tag_list,
    )
    return json.dumps(result)


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
    notes = await get_learning_notes(user_id, resource_title or None)
    return json.dumps({"notes": notes, "count": len(notes)}, default=str)


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
    updated = await mark_session_complete(session_id, user_id, notes)
    return json.dumps({"completed": True, "session": updated}, default=str)


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
    # Prepend user scope so NL-to-SQL stays within this user's data
    scoped_question = f"For user {user_id}: {question}"
    result = await query_nl(scoped_question, user_id)
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
    goal = StudyGoal(
        user_id=user_id,
        title=title,
        target_date=target_date,
        weekly_hours_target=weekly_hours_target,
        resource_id=resource_id or None,
    )
    created = await create_study_goal(goal)
    return json.dumps({"created": True, "goal": created}, default=str)


# ── Agent Definition ──────────────────────────────────────────────────────────

LEARNING_AGENT_INSTRUCTION = """
You are the Learning Agent for Saarthi AI — a personal AI life operating system.

Your domain: everything related to the user's learning journey.
This includes books, online courses, articles, videos, study schedules,
learning notes, streaks, and progress towards learning goals.

YOUR TOOLS:
- tool_get_learning_status       → full snapshot (always call this first)
- tool_add_learning_resource     → add a new book/course/article
- tool_update_progress           → update % or page on a resource
- tool_schedule_study_session    → book a study block on the calendar
- tool_log_study_note            → save notes to Notes MCP
- tool_get_notes                 → retrieve past notes
- tool_mark_session_done         → mark a study session completed
- tool_query_learning_history    → natural language query via AlloyDB AI
- tool_create_study_goal         → create a high-level learning goal

CONFLICT DETECTION RULES — check for these and flag them:
1. Study session clashes with an existing calendar event
   → flag: "Study block on [DATE] overlaps with [EVENT]"
2. Weekly study hours < 50% of the user's goal target
   → flag: "Study hours this week ([X]h) are below your [Y]h weekly target"
3. A resource has been 'in_progress' for > 30 days with 0% progress change
   → flag: "Stalled resource: '[TITLE]' has had no progress for 30+ days"
4. Goal target date is within 7 days and progress < 80%
   → flag: "Goal '[TITLE]' is due in [N] days but only [X]% complete"

RESPONSE FORMAT:
Always end your internal reasoning with a call to build_agent_response().
Your final output MUST be valid JSON matching the AgentResponse schema:
{
  "agent": "learning_agent",
  "status": "ok" | "error" | "partial",
  "summary": "One paragraph human-readable summary",
  "conflicts": ["list of flagged conflicts"],
  "actions_taken": ["list of actions you took"],
  "data": { ...raw structured data for the orchestrator... }
}

TONE: Be encouraging about learning progress. Celebrate streaks.
Be specific — mention exact book titles, percentages, dates.
Never be vague. If something is at risk, say so clearly.
"""

learning_agent = Agent(
    name="learning_agent",
    model="gemini-2.0-flash",
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
    ],
)


# ── Standalone Runner (for testing without the orchestrator) ──────────────────

async def run_learning_agent(message: str, user_id: str) -> AgentResponse:
    """
    Run the learning agent directly (used for unit tests and the demo endpoint).
    In production the orchestrator calls this agent via sub_agents=[learning_agent].
    """
    runner = Runner(agent=learning_agent)
    try:
        result = await runner.run(
            user_message=message,
            context={"user_id": user_id},
        )

        # Parse the JSON response the agent returns
        try:
            raw = json.loads(result.text)
            return AgentResponse(**raw)
        except (json.JSONDecodeError, ValueError):
            # If the agent didn't return valid JSON, wrap the text response
            return AgentResponse(
                agent="learning_agent",
                status=AgentStatus.PARTIAL,
                summary=result.text,
                conflicts=[],
                actions_taken=[],
                data=None,
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