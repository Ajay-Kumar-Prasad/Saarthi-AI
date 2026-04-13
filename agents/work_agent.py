"""
Saarthi AI — Work Agent

Responsibility:
    Manages everything in the 'work' domain:
    - Tasks (Google Tasks via Workspace MCP)
    - Calendar (Google Calendar via Workspace MCP)
    - Gmail (unread, urgent messages via Workspace MCP)
    - Deadline detection and conflict flagging
    - Cross-domain data for the orchestrator (task load, calendar blocks)

MCP Tools used (via local workspace-mcp Docker server):
    - Google Calendar → list events, create events, find free slots
    - Google Tasks    → list tasks, create tasks, complete tasks
    - Gmail           → list messages, read threads

Returns:
    Always an AgentResponse (see db/schemas.py).
    The orchestrator reads .conflicts and .data for cross-domain insights.
"""

import logging
import os
from datetime import datetime

from db.schemas import AgentResponse, AgentStatus

logger = logging.getLogger(__name__)

MOCK_WORKSPACE_MCP = os.getenv("MOCK_WORKSPACE_MCP", "false").lower() == "true"


def _build_response(
    status: AgentStatus,
    summary: str,
    conflicts: list[str] | None = None,
    actions_taken: list[str] | None = None,
    data: dict | None = None,
) -> AgentResponse:
    return AgentResponse(
        agent="work_agent",
        status=status,
        summary=summary,
        conflicts=conflicts or [],
        actions_taken=actions_taken or [],
        data=data,
    )


def _empty_tasks_data() -> dict:
    return {"tasks": [], "high_priority_tasks": 0, "due_today": 0, "high_priority_list": []}


def _empty_calendar_data() -> dict:
    return {"calendar_events": [], "meetings_today": 0, "back_to_back_warnings": []}


def _empty_gmail_data() -> dict:
    return {"unread_emails": [], "unread_count": 0}


def _validate_inputs(message: str, user_id: str) -> AgentResponse | None:
    if not isinstance(user_id, str) or not user_id.strip():
        return _build_response(AgentStatus.ERROR, "Missing required user_id.")
    if not isinstance(message, str) or not message.strip():
        return _build_response(AgentStatus.ERROR, "Missing required message.")
    return None

# ── ADK Agent definition ──────────────────────────────────────────────────────

try:
    from google.adk.agents import Agent
    from tools.workspace_mcp.client import get_toolset

    _toolset = get_toolset()
    _tools = [_toolset] if _toolset is not None else []

    WORK_AGENT_INSTRUCTION = """
You are the Work Agent for Saarthi AI — a personal AI life operating system.

Your domain: everything related to the user's professional work life.
This includes tasks, calendar events, deadlines, emails, meetings,
and work-life balance signals.

TOOLS available via Google Workspace MCP:
- Google Calendar: list events, create events, check free slots
- Google Tasks: list tasks, create tasks, mark complete
- Gmail: list messages, search by sender or subject

WHAT TO DO:
1. When asked about tasks → use tasks tools to list and summarise
2. When asked about calendar → use calendar tools to list upcoming events
3. When asked about email → use gmail tools to find urgent messages
4. Always look for CONFLICTS:
   - More than 5 high-priority tasks due today → flag overload
   - Back-to-back meetings with no break → flag meeting fatigue
   - Unread emails from manager or critical senders → flag urgency

RESPONSE FORMAT:
Always return valid JSON matching AgentResponse schema:
{
  "agent": "work_agent",
  "status": "ok" | "error" | "partial",
  "summary": "One paragraph human-readable summary",
  "conflicts": ["list of flagged conflicts"],
  "actions_taken": ["list of actions you took"],
  "data": {
    "tasks": [...],
    "calendar_events": [...],
    "unread_emails": [...],
    "high_priority_tasks": <count>,
    "meetings_today": <count>
  }
}

Return ONLY valid JSON. Do NOT use markdown code blocks.
"""

    work_agent = Agent(
        name="work_agent",
        model="gemini-2.5-flash",
        description=(
            "Manages the user's work life — tasks, calendar, email, deadlines. "
            "Uses Google Workspace MCP tools. Detects work overload and urgent items."
        ),
        instruction=WORK_AGENT_INSTRUCTION,
        tools=_tools,
    )

except Exception as _adk_err:
    logger.warning("ADK or Workspace MCP not available: %s — using direct dispatch only", _adk_err)
    work_agent = None


# ── Direct tool functions (used in both mock and real paths) ──────────────────

async def _get_tasks_summary(user_id: str) -> dict:
    try:
        from tools.workspace_mcp.client import get_tasks
    except Exception as exc:
        logger.warning("Tasks dependency unavailable: %s", exc)
        return _empty_tasks_data()
    tasks = await get_tasks(user_id, max_results=20)
    high_priority = [t for t in tasks if t.get("priority") == "high" and t.get("status") != "completed"]
    due_today_str = datetime.utcnow().date().isoformat()
    due_today = [t for t in tasks if t.get("due", "").startswith(due_today_str)]
    return {
        "tasks": tasks,
        "high_priority_tasks": len(high_priority),
        "due_today": len(due_today),
        "high_priority_list": [str(t.get("title", "Untitled task")) for t in high_priority[:5]],
    }


async def _get_calendar_summary(user_id: str) -> dict:
    try:
        from tools.workspace_mcp.client import get_calendar_events
    except Exception as exc:
        logger.warning("Calendar dependency unavailable: %s", exc)
        return _empty_calendar_data()
    events = await get_calendar_events(user_id, max_results=10)
    today_str = datetime.utcnow().date().isoformat()
    today_events = [e for e in events if e.get("start", "").startswith(today_str)]

    # Detect back-to-back meetings (< 15 min gap)
    back_to_back = []
    sorted_events = sorted(today_events, key=lambda e: e.get("start", ""))
    for i in range(len(sorted_events) - 1):
        try:
            end_curr = datetime.fromisoformat(sorted_events[i]["end"])
            start_next = datetime.fromisoformat(sorted_events[i + 1]["start"])
            gap_minutes = (start_next - end_curr).total_seconds() / 60
            if gap_minutes < 15:
                back_to_back.append(
                    f"{sorted_events[i]['summary']} → {sorted_events[i+1]['summary']} "
                    f"(only {int(gap_minutes)} min gap)"
                )
        except Exception:
            continue

    return {
        "calendar_events": events,
        "meetings_today": len(today_events),
        "back_to_back_warnings": back_to_back,
    }


async def _get_gmail_summary(user_id: str) -> dict:
    try:
        from tools.workspace_mcp.client import get_gmail_messages
    except Exception as exc:
        logger.warning("Gmail dependency unavailable: %s", exc)
        return _empty_gmail_data()
    messages = await get_gmail_messages(user_id, max_results=10, query="is:unread")
    unread_count = len([m for m in messages if m.get("unread")])
    return {
        "unread_emails": messages,
        "unread_count": unread_count,
    }


def _detect_work_conflicts(tasks_data: dict, calendar_data: dict, gmail_data: dict) -> list[str]:
    conflicts = []

    if tasks_data["high_priority_tasks"] > 5:
        conflicts.append(
            f"Work overload: {tasks_data['high_priority_tasks']} high-priority tasks pending. "
            f"Top items: {', '.join(tasks_data['high_priority_list'][:3])}"
        )

    if tasks_data["due_today"] > 3:
        conflicts.append(f"{tasks_data['due_today']} tasks due today — consider deferring lower-priority ones.")

    for warning in calendar_data.get("back_to_back_warnings", []):
        conflicts.append(f"Back-to-back meetings detected: {warning}")

    if calendar_data["meetings_today"] > 5:
        conflicts.append(
            f"Heavy meeting day: {calendar_data['meetings_today']} meetings today. "
            "Deep-focus work may not be possible."
        )

    if gmail_data["unread_count"] > 20:
        conflicts.append(f"{gmail_data['unread_count']} unread emails — inbox needs attention.")

    return conflicts


# ── Main entry point ──────────────────────────────────────────────────────────

async def run_work_agent(message: str, user_id: str) -> AgentResponse:
    """
    Entry point called by the orchestrator.
    Uses direct tool dispatch (mock or real) for reliability.
    ADK runner is available for natural language queries via the /work/chat route.
    """
    invalid = _validate_inputs(message, user_id)
    if invalid:
        return invalid

    user_id = user_id.strip()
    message = message.strip()

    try:
        # Run all three data fetches concurrently
        tasks_data, calendar_data, gmail_data = await asyncio.gather(
            _get_tasks_summary(user_id),
            _get_calendar_summary(user_id),
            _get_gmail_summary(user_id),
            return_exceptions=True,
        )

        # Handle partial failures gracefully
        partial_reasons = []
        if isinstance(tasks_data, Exception):
            logger.error("Tasks fetch failed: %s", tasks_data)
            tasks_data = _empty_tasks_data()
            partial_reasons.append("Tasks data unavailable.")

        if isinstance(calendar_data, Exception):
            logger.error("Calendar fetch failed: %s", calendar_data)
            calendar_data = _empty_calendar_data()
            partial_reasons.append("Calendar data unavailable.")

        if isinstance(gmail_data, Exception):
            logger.error("Gmail fetch failed: %s", gmail_data)
            gmail_data = _empty_gmail_data()
            partial_reasons.append("Gmail data unavailable.")

        all_conflicts = _detect_work_conflicts(tasks_data, calendar_data, gmail_data)
        message_lc = (message or "").lower()

        # Intent routing based on user message
        if "task" in message_lc:
            summary = (
                f"Task status: {len(tasks_data.get('tasks', []))} task(s), "
                f"{tasks_data.get('high_priority_tasks', 0)} high-priority, "
                f"{tasks_data.get('due_today', 0)} due today."
            )
            intent_conflicts = [c for c in all_conflicts if "task" in c.lower() or "overload" in c.lower()]
            actions_taken = ["Fetched tasks from Google Tasks"]
            response_data = {
                "tasks": tasks_data.get("tasks", []),
                "high_priority_tasks": tasks_data.get("high_priority_tasks", 0),
                "due_today": tasks_data.get("due_today", 0),
            }
        elif "meeting" in message_lc or "calendar" in message_lc:
            summary = (
                f"Calendar status: {calendar_data.get('meetings_today', 0)} meeting(s) today, "
                f"{len(calendar_data.get('back_to_back_warnings', []))} back-to-back warning(s)."
            )
            intent_conflicts = [c for c in all_conflicts if "meeting" in c.lower() or "calendar" in c.lower()]
            actions_taken = ["Fetched calendar events from Google Calendar"]
            response_data = {
                "calendar_events": calendar_data.get("calendar_events", []),
                "meetings_today": calendar_data.get("meetings_today", 0),
                "back_to_back_warnings": calendar_data.get("back_to_back_warnings", []),
            }
        elif "email" in message_lc:
            summary = f"Email status: {gmail_data.get('unread_count', 0)} unread email(s)."
            intent_conflicts = [c for c in all_conflicts if "email" in c.lower() or "inbox" in c.lower()]
            actions_taken = ["Fetched unread email count from Gmail"]
            response_data = {
                "unread_emails": gmail_data.get("unread_emails", []),
                "unread_count": gmail_data.get("unread_count", 0),
            }
        else:
            # Existing full-summary behavior
            summary_parts = []
            if tasks_data["high_priority_tasks"] > 0:
                summary_parts.append(
                    f"{tasks_data['high_priority_tasks']} high-priority task(s) pending"
                )
            if calendar_data["meetings_today"] > 0:
                summary_parts.append(f"{calendar_data['meetings_today']} meeting(s) today")
            if gmail_data["unread_count"] > 0:
                summary_parts.append(f"{gmail_data['unread_count']} unread email(s)")

            summary = (
                "Work status: " + ", ".join(summary_parts) + "."
                if summary_parts else
                "No urgent work items found."
            )
            intent_conflicts = all_conflicts
            actions_taken = [
                "Fetched tasks from Google Tasks",
                "Fetched calendar events from Google Calendar",
                "Fetched unread email count from Gmail",
            ]
            response_data = {
                **tasks_data,
                **calendar_data,
                **gmail_data,
            }

        if partial_reasons:
            summary += f" Note: {' '.join(partial_reasons)}"

        status = AgentStatus.PARTIAL if partial_reasons else AgentStatus.OK

        return _build_response(
            status=status,
            summary=summary,
            conflicts=intent_conflicts,
            actions_taken=actions_taken,
            data=response_data,
        )

    except Exception as exc:
        logger.exception("work_agent failed for user_id=%s", user_id)
        return _build_response(AgentStatus.ERROR, f"Work agent error: {exc}")
