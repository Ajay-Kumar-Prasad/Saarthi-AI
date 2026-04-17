"""
Saarthi AI — Health Agent

Responsibility:
    Manages everything in the 'health' domain:
    - Monitoring fitness activities (running, cycling, yoga, etc.)
    - Reporting daily metrics: steps, calories, active minutes
    - Monitoring resting heart rate and cardiovascular trends
    - Reporting health insights to the orchestrator

Data flow:
    Google Fit API is called ONCE during user onboarding (after OAuth callback).
    All data is persisted to AlloyDB at that point.
    During chat the agent reads ONLY from AlloyDB — no API calls at runtime.

    If the user explicitly asks to refresh / sync their data, the agent
    calls tool_sync_health_data which re-hits the Fit API and updates AlloyDB.

Database:
    - health_tokens        — Google OAuth2 access/refresh tokens per user
    - health_activity_logs — individual workout/activity session records
    - health_daily_metrics — daily step/calorie/active-minute aggregates

Returns:
    Always an AgentResponse (see models/schemas.py).
    The orchestrator reads .conflicts to build cross-domain insights.
"""

import json
import logging
import re
from datetime import datetime, timezone

try:
    from google.adk.agents import Agent
    from google.adk.runners import Runner
    from google.adk.sessions import InMemorySessionService
    from google.genai import types as genai_types
    _ADK_AVAILABLE = True
except Exception:  # pragma: no cover
    _ADK_AVAILABLE = False

    class Agent:  # type: ignore
        def __init__(self, *args, **kwargs):
            pass

    class Runner:  # type: ignore
        def __init__(self, agent, app_name="", session_service=None):
            self.agent = agent

        async def run_async(self, user_id, session_id, new_message):
            raise RuntimeError("google-adk is required to run the live agent")

    class InMemorySessionService:  # type: ignore
        async def create_session(self, app_name, user_id):
            class _S:
                id = "stub-session"
            return _S()

from tools.google_fit import (
    fetch_sleep_data,
    fetch_activity_sessions,
    fetch_daily_metrics,
)
from db.health_db import (
    save_sleep_sessions,
    save_activity_sessions,
    save_daily_metrics,
    update_resting_heart_rate,
    get_health_summary,
)
from models.schemas import (
    AgentResponse,
    AgentStatus,
    HealthSummary,
)

logger = logging.getLogger(__name__)


# ── Internal sync helper (called during onboarding, not by the agent directly) ─

def _error_response(summary: str, data: dict | None = None) -> AgentResponse:
    return AgentResponse(
        agent="health_agent",
        status=AgentStatus.ERROR,
        summary=summary,
        conflicts=[],
        actions_taken=[],
        data=data,
    )


def _is_valid_user_id(user_id: str) -> bool:
    return isinstance(user_id, str) and bool(user_id.strip())


def _sanitize_days(days: int, default: int = 7, max_days: int = 30) -> int:
    if not isinstance(days, int):
        return default
    if days < 1:
        return 1
    return min(days, max_days)


def _json_error(message: str, **extra) -> str:
    payload = {"error": message}
    payload.update(extra)
    return json.dumps(payload, default=str)


async def _safe_fetch_health_data(user_id: str, days: int) -> tuple[list, list, list, list[str]]:
    issues: list[str] = []
    sleep_sessions, activity_sessions, daily_metrics = [], [], []
    try:
        sleep_sessions = await fetch_sleep_data(user_id, days)
    except Exception as exc:
        logger.exception("Failed to fetch sleep data for user_id=%s", user_id)
        issues.append(f"sleep_fetch_failed: {exc}")
    try:
        activity_sessions = await fetch_activity_sessions(user_id, days)
    except Exception as exc:
        logger.exception("Failed to fetch activity data for user_id=%s", user_id)
        issues.append(f"activity_fetch_failed: {exc}")
    try:
        daily_metrics = await fetch_daily_metrics(user_id, days)
    except Exception as exc:
        logger.exception("Failed to fetch daily metrics for user_id=%s", user_id)
        issues.append(f"metrics_fetch_failed: {exc}")
    return sleep_sessions, activity_sessions, daily_metrics, issues


async def _safe_persist_health_data(
    user_id: str, sleep_sessions: list, activity_sessions: list, daily_metrics: list
) -> tuple[int, int, int, list[str]]:
    issues: list[str] = []
    sleep_saved = activity_saved = metrics_saved = 0
    try:
        sleep_saved = await save_sleep_sessions(user_id, sleep_sessions)
    except Exception as exc:
        logger.exception("Failed to persist sleep data for user_id=%s", user_id)
        issues.append(f"sleep_save_failed: {exc}")
    try:
        activity_saved = await save_activity_sessions(user_id, activity_sessions)
    except Exception as exc:
        logger.exception("Failed to persist activity data for user_id=%s", user_id)
        issues.append(f"activity_save_failed: {exc}")
    try:
        metrics_saved = await save_daily_metrics(user_id, daily_metrics)
    except Exception as exc:
        logger.exception("Failed to persist daily metrics for user_id=%s", user_id)
        issues.append(f"metrics_save_failed: {exc}")
    return sleep_saved, activity_saved, metrics_saved, issues


async def sync_all_health_data(user_id: str, days: int = 30) -> dict:
    """
    Pull all health data from Google Fit and persist to AlloyDB.
    Called ONCE during OAuth onboarding and also from the /health/sync endpoint.
    NOT exposed as an ADK tool — the agent reads from DB only during chat.

    Args:
        user_id: The user's email string.
        days:    Number of past days to back-fill (default 30).

    Returns:
        Dict with counts of records saved per category.
    """
    if not _is_valid_user_id(user_id):
        return {"error": "user_id is required for health sync."}

    days = _sanitize_days(days, default=30, max_days=30)
    sleep_sessions, activity_sessions, daily_metrics, fetch_issues = await _safe_fetch_health_data(
        user_id, days
    )
    sleep_saved, activity_saved, metrics_saved, persist_issues = await _safe_persist_health_data(
        user_id, sleep_sessions, activity_sessions, daily_metrics
    )
    issues = fetch_issues + persist_issues

    logger.info(
        f"[sync_all_health_data] user={user_id} "
        f"sleep={sleep_saved} activity={activity_saved} "
        f"metrics={metrics_saved}"
    )
    return {
        "sleep_sessions_saved": sleep_saved,
        "activity_sessions_saved": activity_saved,
        "daily_metrics_saved": metrics_saved,
        "period_days": days,
        "issues": issues,
    }


# ── Helpers ───────────────────────────────────────────────────────────────────

def _strip_code_fences(text: str) -> str:
    """
    Remove markdown code fences that Gemini sometimes wraps JSON in.
    Handles ```json ... ``` and plain ``` ... ``` blocks.
    Falls back to the original text if no fences are detected.
    """
    text = text.strip()
    match = re.match(r"^```(?:json)?\s*([\s\S]*?)\s*```$", text)
    if match:
        return match.group(1).strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


# ── ADK Tool Functions ─────────────────────────────────────────────────────────
# These are the ONLY tools the agent uses during a chat session.
# All reads go to AlloyDB — no Google Fit API calls at chat time.

def generate_health_insight(data: list[dict]) -> str:
    if not data:
        return "No health data available."

    total_steps_list = [r.get("total_steps") or 0 for r in data if r.get("total_steps") is not None]
    if not total_steps_list:
        return "No activity data found"
        
    avg_steps = sum(total_steps_list) / len(total_steps_list)

    if avg_steps < 3000:
        insight = "Low activity level"
    elif avg_steps < 7000:
        insight = "Moderate activity"
    else:
        insight = "Good activity level"
        
    if all(d.get("sleep_duration_min") is None for d in data):
        insight += ". Sleep data not available"
        
    return insight

async def tool_get_health_summary(user_id: str) -> str:
    """
    Build a comprehensive health summary from AlloyDB data.
    Args:
        user_id: The user's email string.
    Returns:
        JSON string.
    """
    logger.info("Fetching data for user: %s", user_id)
    if not _is_valid_user_id(user_id):
        return _json_error("user_id is required.")
    try:
        raw_db = await get_health_summary(user_id)
        
        data = []
        for r in raw_db:
            row = dict(r)
            if row.get("total_calories") is not None:
                row["total_calories"] = float(row["total_calories"])
            data.append(row)
            
        logger.info("DB result: %s", data)
        return {
            "health_summary": data,
            "insight": generate_health_insight(data)
        }
    except Exception as exc:
        logger.exception("tool_get_health_summary failed user_id=%s", user_id)
        return _json_error("Failed to build health summary.", details=str(exc))


async def tool_sync_health_data(user_id: str, days: int = 30) -> str:
    """
    Manually re-sync health data from Google Fit and update AlloyDB.
    Use this ONLY when the user explicitly asks to 'refresh', 'sync', or 'update'
    their health data. Do NOT call this for normal health queries — read from DB instead.

    Args:
        user_id: The user's email string.
        days:    Number of past days to re-fetch (default 30, max 90).

    Returns:
        JSON string with counts of records synced per category.
    """
    if not _is_valid_user_id(user_id):
        return _json_error("user_id is required.")
    days = _sanitize_days(days, default=30, max_days=30)
    result = await sync_all_health_data(user_id, days)
    logger.info(f"[tool_sync_health_data] manual sync triggered for user {user_id}")
    return result


async def tool_get_agent_status(user_id: str) -> str:
    """
    Return a structured AgentResponse for the orchestrator.
    Args:
        user_id: The user's email string.
    Returns:
        JSON string matching the AgentResponse schema.
    """
    if not _is_valid_user_id(user_id):
        return _json_error("user_id is required.")
    print("Fetching data for user:", user_id)
    try:
        data = await get_health_summary(user_id)
        print("DB result:", data)
    except Exception as exc:
        logger.exception("tool_get_agent_status failed user_id=%s", user_id)
        return _json_error("Failed to build agent status.", details=str(exc))

    one_line = f"Health data ready: extracted {len(data)} records."
    
    response = AgentResponse(
        agent="health_agent",
        status=AgentStatus.OK,
        summary=one_line,
        data={
            "health_summary": data,
            "insight": generate_health_insight(data)
        },
    )

    return response.model_dump()


# ── Agent Definition ───────────────────────────────────────────────────────────

HEALTH_AGENT_INSTRUCTION = """
You are the Health Agent for Saarthi AI — a personal AI life operating system.

Your mission: Help users understand and improve their physical health by analyzing their sleep, fitness activities, daily steps, calories, active minutes, and resting heart rate. All data is sourced from AlloyDB, which is populated from Google Fit during onboarding or when the user explicitly requests a sync.

USER IDENTIFICATION:
Every message starts with a prefix: [user_id: <value>]
Always extract this value and pass it as the user_id argument to every tool call. Never guess or invent a user_id.
Example: "[user_id: abc123]\n\nHow many steps did I take?" → all tools get user_id="abc123"

DATA FLOW:
- Read health data ONLY from AlloyDB during chat. Never call Google Fit APIs at chat time.
- Data is fetched from Google Fit and stored in AlloyDB during onboarding (OAuth) or when the user requests a sync.
- Only use tool_sync_health_data if the user explicitly asks to refresh or sync their data.

TOOLS AVAILABLE:
- tool_get_activity_from_db:   Get workout/activity sessions from AlloyDB
- tool_get_daily_metrics_from_db: Get daily steps, calories, active minutes, resting heart rate
- tool_get_health_summary:     Aggregate all stored data into a summary
- tool_analyze_health_trends:  Analyze trends and detect health conflicts
- tool_sync_health_data:       Sync from Google Fit (only on explicit user request)
- tool_get_agent_status:       Return a structured AgentResponse for the orchestrator

TOOL USAGE EXAMPLES:
- "Show me my workouts" → tool_get_activity_from_db
- "How many steps?" → tool_get_daily_metrics_from_db
- "How am I doing overall?" → tool_get_health_summary, then tool_analyze_health_trends
- "Refresh/sync my data" → tool_sync_health_data (only if user requests)
- Orchestrator status request → tool_get_agent_status

CONFLICT DETECTION — Always flag these:

1. Average daily steps <7,500:
    "low_step_count: avg [X] steps/day"
2. High-activity day (>60 active min) with <6h sleep:
    "high_activity_low_sleep on [DATE]: active [X] min but only [Y]h sleep"
3. Resting heart rate >80 bpm avg:
    "elevated_resting_hr: [X] bpm avg"

RESPONSE FORMAT:
Always return valid JSON matching the AgentResponse schema:
{
  "agent": "health_agent",
  "status": "ok" | "error" | "partial",
  "summary": "One-paragraph, human-readable summary",
  "conflicts": ["list of flagged conflicts"],
  "actions_taken": ["list of actions you took"],
  "data": { ...raw structured data for the orchestrator... }
}

TONE & GUIDANCE:
- Be specific: mention exact numbers, dates, and activity types.
- If data is missing, state this clearly and suggest the user visit /auth/google/login to connect Google Fit.
- Never provide medical diagnoses or prescriptions. Stick to factual observations and general wellness advice.
"""

health_agent = Agent(
    name="health_agent",
    model="gemini-2.5-flash",
    description=(
        "Manages the user's physical health — sleep tracking, fitness activities, "
        "step counts, calories, and heart rate. Reads from AlloyDB (populated during "
        "onboarding via Google Fit OAuth). Detects cross-domain health conflicts "
        "(e.g. insufficient recovery after high-intensity workouts). "
        "Part of the Saarthi multi-agent personal assistant."
    ),
    instruction=HEALTH_AGENT_INSTRUCTION,
    tools=[
        tool_get_health_summary,
        tool_sync_health_data,
        tool_get_agent_status,
    ],
)


# ── Standalone Runner ──────────────────────────────────────────────────────────

async def run_health_agent(message: str, user_id: str) -> AgentResponse:
    if not _is_valid_user_id(user_id):
        return _error_response("Missing required user_id.")

    try:
        data = await tool_get_health_summary(user_id)
        
        return AgentResponse(
            agent="health_agent",
            status=AgentStatus.OK,
            summary="Health status retrieved.",
            conflicts=[],
            actions_taken=["get_health_summary"],
            data=data
        )
    except Exception as exc:
        logger.exception("run_health_agent failed: %s", exc)
        return _error_response(f"Health agent failed: {exc}")
