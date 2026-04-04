"""
Saarthi AI — Health Agent

Responsibility:
    Manages everything in the 'health' domain:
    - Tracking sleep sessions and quality
    - Monitoring fitness activities (running, cycling, yoga, etc.)
    - Reporting daily metrics: steps, calories, active minutes
    - Monitoring resting heart rate and cardiovascular trends
    - Detecting cross-domain conflicts (e.g. high-intensity workout after < 5h sleep)
    - Reporting health insights to the orchestrator

Data flow:
    Google Fit API is called ONCE during user onboarding (after OAuth callback).
    All data is persisted to AlloyDB at that point.
    During chat the agent reads ONLY from AlloyDB — no API calls at runtime.

    If the user explicitly asks to refresh / sync their data, the agent
    calls tool_sync_health_data which re-hits the Fit API and updates AlloyDB.

Database:
    - health_tokens        — Google OAuth2 access/refresh tokens per user
    - health_sleep_logs    — nightly sleep session records
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
    fetch_heart_rate,
)
from db.health_db import (
    save_sleep_sessions,
    save_activity_sessions,
    save_daily_metrics,
    update_resting_heart_rate,
    build_health_summary,
    get_sleep_summary_from_db,
    get_activity_summary_from_db,
    get_daily_metrics_from_db,
)
from models.schemas import (
    AgentResponse,
    AgentStatus,
    HealthSummary,
)

logger = logging.getLogger(__name__)


# ── Internal sync helper (called during onboarding, not by the agent directly) ─

async def sync_all_health_data(user_id: str, days: int = 30) -> dict:
    """
    Pull all health data from Google Fit and persist to AlloyDB.
    Called ONCE during OAuth onboarding and also from the /health/sync endpoint.
    NOT exposed as an ADK tool — the agent reads from DB only during chat.

    Args:
        user_id: The user's UUID string.
        days:    Number of past days to back-fill (default 30).

    Returns:
        Dict with counts of records saved per category.
    """
    days = min(days, 90)

    sleep_sessions = await fetch_sleep_data(user_id, days)
    activity_sessions = await fetch_activity_sessions(user_id, days)
    daily_metrics = await fetch_daily_metrics(user_id, days)
    hr_data = await fetch_heart_rate(user_id, days)

    sleep_saved = await save_sleep_sessions(user_id, sleep_sessions)
    activity_saved = await save_activity_sessions(user_id, activity_sessions)
    metrics_saved = await save_daily_metrics(user_id, daily_metrics)
    await update_resting_heart_rate(user_id, hr_data)

    logger.info(
        f"[sync_all_health_data] user={user_id} "
        f"sleep={sleep_saved} activity={activity_saved} "
        f"metrics={metrics_saved} hr={len(hr_data)}"
    )
    return {
        "sleep_sessions_saved": sleep_saved,
        "activity_sessions_saved": activity_saved,
        "daily_metrics_saved": metrics_saved,
        "heart_rate_days_saved": len(hr_data),
        "period_days": days,
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

async def tool_get_sleep_from_db(user_id: str, days: int = 7) -> str:
    """
    Read the user's sleep sessions for the last `days` days from AlloyDB.
    Returns sleep duration, start/end times, and sleep stage breakdown.
    Use this when the user asks about sleep quality, duration, or patterns.
    Data was pre-loaded from Google Fit during onboarding.

    Args:
        user_id: The user's UUID string.
        days:    Number of past days to read (default 7, max 30).

    Returns:
        JSON string with keys: sessions, count, period_days.
    """
    days = min(days, 30)
    sessions = await get_sleep_summary_from_db(user_id, days)
    return json.dumps({
        "sessions": [s.model_dump() for s in sessions],
        "count": len(sessions),
        "period_days": days,
    }, default=str)


async def tool_get_activity_from_db(user_id: str, days: int = 7) -> str:
    """
    Read the user's workout and activity sessions for the last `days` days from AlloyDB.
    Returns activity type (running, cycling, yoga, etc.), duration, calories burned,
    steps, and average heart rate per session.
    Use this when the user asks about workouts, exercise history, or activity levels.
    Data was pre-loaded from Google Fit during onboarding.

    Args:
        user_id: The user's UUID string.
        days:    Number of past days to read (default 7, max 30).

    Returns:
        JSON string with keys: sessions, count, period_days.
    """
    days = min(days, 30)
    sessions = await get_activity_summary_from_db(user_id, days)
    return json.dumps({
        "sessions": [s.model_dump() for s in sessions],
        "count": len(sessions),
        "period_days": days,
    }, default=str)


async def tool_get_daily_metrics_from_db(user_id: str, days: int = 7) -> str:
    """
    Read daily aggregate metrics (steps, calories, active minutes, resting heart rate)
    for the last `days` days from AlloyDB.
    Use this when the user asks about step counts, calorie burn, or daily activity trends.
    Data was pre-loaded from Google Fit during onboarding.

    Args:
        user_id: The user's UUID string.
        days:    Number of past days to read (default 7, max 30).

    Returns:
        JSON string with keys: daily_metrics, count, period_days.
    """
    days = min(days, 30)
    metrics = await get_daily_metrics_from_db(user_id, days)
    return json.dumps({
        "daily_metrics": [m.model_dump() for m in metrics],
        "count": len(metrics),
        "period_days": days,
    }, default=str)


async def tool_get_health_summary(user_id: str, days: int = 7) -> str:
    """
    Build a comprehensive health summary from AlloyDB data.
    Aggregates sleep, activity, daily metrics, and resting heart rate into one object.
    Use this for an overall health overview or when the user asks 'how am I doing?'.
    Data was pre-loaded from Google Fit during onboarding.

    Args:
        user_id: The user's UUID string.
        days:    Number of past days to summarize (default 7).

    Returns:
        JSON string with the full HealthSummary object.
    """
    summary = await build_health_summary(user_id, days)
    return json.dumps(summary.model_dump(), default=str)


async def tool_analyze_health_trends(user_id: str, days: int = 14) -> str:
    """
    Perform a cross-domain health trend analysis using AlloyDB data.
    Compares sleep patterns against activity levels to detect correlations and anomalies.
    Examples: 'sleep is worse on high-activity days', 'resting heart rate elevated this week',
    'not hitting step goals on weekdays'.
    Use this for deep health insights and conflict detection.

    Args:
        user_id: The user's UUID string.
        days:    Number of past days to analyze (default 14).

    Returns:
        JSON string with keys: insights, conflicts, confidence, period_days, summary.
    """
    summary = await build_health_summary(user_id, days)
    insights = []
    conflicts = []

    sleep_sessions = summary.sleep_sessions
    daily_metrics = summary.daily_metrics

    # Sleep analysis
    if sleep_sessions:
        under_7h = [s for s in sleep_sessions if s.duration_minutes < 420]
        if len(under_7h) > len(sleep_sessions) * 0.5:
            insights.append(
                f"More than half of nights ({len(under_7h)}/{len(sleep_sessions)}) "
                f"had less than 7 hours of sleep."
            )
            conflicts.append(f"chronic_sleep_deficit: {len(under_7h)} nights under 7h")
        avg_sleep_h = round((summary.avg_sleep_minutes or 0) / 60, 1)
        if avg_sleep_h > 0:
            insights.append(f"Average sleep duration: {avg_sleep_h} hours per night.")

    # Step analysis
    if summary.avg_steps:
        avg_steps = int(summary.avg_steps)
        if avg_steps < 7500:
            insights.append(
                f"Average daily steps ({avg_steps:,}) is below the recommended 7,500-10,000."
            )
            conflicts.append(f"low_step_count: avg {avg_steps:,} steps/day")
        else:
            insights.append(f"Average daily steps: {avg_steps:,} — meeting activity goals.")

    # Sleep vs activity correlation
    if sleep_sessions and daily_metrics:
        sleep_by_date = {s.date: s.duration_minutes for s in sleep_sessions}
        metrics_by_date = {m.date: m for m in daily_metrics}
        for date, sleep_min in sleep_by_date.items():
            metric = metrics_by_date.get(date)
            if metric and metric.active_minutes and metric.active_minutes > 60 and sleep_min < 360:
                conflict_msg = (
                    f"high_activity_low_sleep on {date}: "
                    f"active {metric.active_minutes} min but only slept {round(sleep_min/60, 1)}h"
                )
                conflicts.append(conflict_msg)
                insights.append(
                    f"On {date}: active for {metric.active_minutes} min but only slept "
                    f"{round(sleep_min/60, 1)}h — recovery may be insufficient."
                )

    # Heart rate analysis
    if summary.avg_resting_heart_rate:
        rhr = summary.avg_resting_heart_rate
        if rhr > 80:
            insights.append(
                f"Average resting heart rate ({rhr} bpm) is elevated. "
                "Consider increasing aerobic activity or checking recovery."
            )
            conflicts.append(f"elevated_resting_hr: {rhr} bpm avg")
        elif rhr < 60:
            insights.append(
                f"Average resting heart rate ({rhr} bpm) is in the athletic range."
            )

    if not insights:
        insights.append(
            "Not enough data in AlloyDB to run trend analysis. "
            "Ask the user to sync their health data first via /health/sync."
        )

    confidence = min(0.95, 0.5 + 0.05 * len(sleep_sessions) + 0.05 * len(daily_metrics))

    return json.dumps({
        "insights": insights,
        "conflicts": conflicts,
        "confidence": round(confidence, 2),
        "period_days": days,
        "summary": summary.model_dump(),
    }, default=str)


async def tool_sync_health_data(user_id: str, days: int = 30) -> str:
    """
    Manually re-sync health data from Google Fit and update AlloyDB.
    Use this ONLY when the user explicitly asks to 'refresh', 'sync', or 'update'
    their health data. Do NOT call this for normal health queries — read from DB instead.

    Args:
        user_id: The user's UUID string.
        days:    Number of past days to re-fetch (default 30, max 90).

    Returns:
        JSON string with counts of records synced per category.
    """
    result = await sync_all_health_data(user_id, days)
    logger.info(f"[tool_sync_health_data] manual sync triggered for user {user_id}")
    return json.dumps(result, default=str)


async def tool_get_agent_status(user_id: str) -> str:
    """
    Return a structured AgentResponse for the orchestrator.
    This is the Health Agent's orchestrator contract — call this when another agent
    or the orchestrator needs a standardized health status snapshot.
    Reads from AlloyDB only. Always use this when the orchestrator requests a health update.

    Args:
        user_id: The user's UUID string.

    Returns:
        JSON string matching the AgentResponse schema.
    """
    summary = await build_health_summary(user_id, days=7)
    trend_raw = await tool_analyze_health_trends(user_id, days=14)
    trend_data = json.loads(trend_raw)

    parts = []
    if summary.avg_sleep_minutes:
        parts.append(f"avg sleep {round(summary.avg_sleep_minutes / 60, 1)}h")
    if summary.avg_steps:
        parts.append(f"avg {int(summary.avg_steps):,} steps/day")
    if summary.total_active_minutes:
        parts.append(f"{summary.total_active_minutes} active mins total")
    if summary.avg_resting_heart_rate:
        parts.append(f"resting HR {summary.avg_resting_heart_rate} bpm")
    one_line = (
        f"Health (last 7d): {', '.join(parts)}."
        if parts
        else "Health: no data yet — user needs to sync."
    )

    response = AgentResponse(
        agent="health_agent",
        status=AgentStatus.OK,
        summary=one_line,
        conflicts=trend_data.get("conflicts", []),
        actions_taken=["build_health_summary", "tool_analyze_health_trends"],
        data={
            "health_summary": summary.model_dump(),
            "insights": trend_data.get("insights", []),
            "confidence": trend_data.get("confidence", 0.5),
        },
    )

    return json.dumps(response.model_dump(), default=str)


# ── Agent Definition ───────────────────────────────────────────────────────────

HEALTH_AGENT_INSTRUCTION = """
You are the Health Agent for Saarthi AI — a personal AI life operating system.

Your domain: everything related to the user's physical health.
This includes sleep tracking, fitness activities, daily step counts,
calorie burn, resting heart rate, and recovery trends.

CRITICAL — USER IDENTIFICATION:
Every message starts with a prefix in the format: [user_id: <value>]
You MUST extract this value and pass it as the `user_id` argument to EVERY tool call.
Never call a tool without setting user_id from this prefix. Never invent or guess a user_id.
Example: "[user_id: abc123]\n\nHow many steps did I take?" → all tools get user_id="abc123"

IMPORTANT — DATA ARCHITECTURE:
Your data comes from AlloyDB, NOT from Google Fit directly at chat time.
When the user first connects their account (OAuth onboarding), their Google Fit
data is automatically fetched and stored in AlloyDB.
During every chat you read ONLY from AlloyDB — this is fast, reliable,
and does not consume Google Fit API quota.

The ONLY exception is tool_sync_health_data — use this ONLY if the user
explicitly says they want to refresh or sync their data.

YOUR TOOLS:
- tool_get_sleep_from_db          → read sleep sessions from AlloyDB
- tool_get_activity_from_db       → read workout sessions from AlloyDB
- tool_get_daily_metrics_from_db  → read steps/calories/active minutes from AlloyDB
- tool_get_health_summary         → aggregate all stored data into a full summary
- tool_analyze_health_trends      → cross-domain trend analysis + conflict detection
- tool_sync_health_data           → re-pull from Google Fit (only on explicit user request)
- tool_get_agent_status           → structured AgentResponse for the orchestrator

TOOL CALL GUIDELINES:
- "How did I sleep?" → call tool_get_sleep_from_db
- "Show me my workouts" → call tool_get_activity_from_db
- "How many steps?" → call tool_get_daily_metrics_from_db
- "How am I doing overall?" → call tool_get_health_summary then tool_analyze_health_trends
- "Refresh / sync my data" → call tool_sync_health_data (rare ��� only on explicit request)
- Orchestrator status request → call tool_get_agent_status

CONFLICT DETECTION RULES — detect and flag these:
1. More than 50% of nights with less than 7h sleep
   → flag: "chronic_sleep_deficit: [N] nights under 7h"
2. Average daily steps below 7,500
   → flag: "low_step_count: avg [X] steps/day"
3. High-intensity activity day (>60 active min) with less than 6h sleep
   → flag: "high_activity_low_sleep on [DATE]: active [X] min but only [Y]h sleep"
4. Resting heart rate above 80 bpm on average
   → flag: "elevated_resting_hr: [X] bpm avg"

RESPONSE FORMAT:
Your final output MUST be valid JSON matching the AgentResponse schema:
{
  "agent": "health_agent",
  "status": "ok" | "error" | "partial",
  "summary": "One paragraph human-readable summary",
  "conflicts": ["list of flagged conflicts"],
  "actions_taken": ["list of actions you took"],
  "data": { ...raw structured data for the orchestrator... }
}

TONE: Be specific — mention exact numbers, dates, and activity types.
Never be vague about health data. If data is missing, say so clearly and suggest
the user visit /auth/google/login to connect Google Fit.
Do not provide medical diagnoses or prescriptions. Offer factual
observations and general wellness guidance only.
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
        tool_get_sleep_from_db,
        tool_get_activity_from_db,
        tool_get_daily_metrics_from_db,
        tool_get_health_summary,
        tool_analyze_health_trends,
        tool_sync_health_data,
        tool_get_agent_status,
    ],
)


# ── Standalone Runner ──────────────────────────────────────────────────────────

async def run_health_agent(message: str, user_id: str) -> AgentResponse:
    """
    Run the Health Agent directly (used for unit tests and the demo endpoint).
    In production the orchestrator calls this agent via sub_agents=[health_agent].

    Uses the official ADK Runner API:
        Runner(agent=..., app_name=..., session_service=...)
        session_service.create_session(app_name=..., user_id=...)
        runner.run_async(user_id=..., session_id=..., new_message=types.Content(...))
    """
    if not user_id:
        return AgentResponse(
            agent="health_agent",
            status=AgentStatus.ERROR,
            summary="Missing required user_id.",
            conflicts=[],
            actions_taken=[],
            data=None,
        )

    APP_NAME = "health_agent"

    session_service = InMemorySessionService()
    session = await session_service.create_session(
        app_name=APP_NAME,
        user_id=user_id,
    )

    runner = Runner(
        agent=health_agent,
        app_name=APP_NAME,
        session_service=session_service,
    )

    try:
        # Prepend user_id so Gemini always knows which user to pass to tool functions.
        # Without this, Gemini guesses or passes an empty string → DB returns 0 rows.
        injected_message = f"[user_id: {user_id}]\n\n{message}"

        new_message = genai_types.Content(
            role="user",
            parts=[genai_types.Part(text=injected_message)],
        )

        response_text = ""
        async for event in runner.run_async(
            user_id=user_id,
            session_id=session.id,
            new_message=new_message,
        ):
            if event.is_final_response():
                if event.content and event.content.parts:
                    response_text = event.content.parts[0].text
                break

        clean_text = _strip_code_fences(response_text)
        try:
            raw = json.loads(clean_text)
            return AgentResponse(**raw)
        except (json.JSONDecodeError, ValueError):
            logger.warning(
                "[run_health_agent] Non-JSON response from agent (after fence strip): %s",
                clean_text[:300],
            )
            # If Gemini returned a valid AgentResponse wrapped in JSON inside a partial,
            # try to extract it from the summary field too
            try:
                nested = json.loads(response_text)
                if isinstance(nested, dict) and "summary" in nested:
                    inner = _strip_code_fences(nested.get("summary", ""))
                    inner_raw = json.loads(inner)
                    return AgentResponse(**inner_raw)
            except (json.JSONDecodeError, ValueError, AttributeError):
                pass
            return AgentResponse(
                agent="health_agent",
                status=AgentStatus.PARTIAL,
                summary=clean_text[:500] if clean_text else "Health agent returned no response.",
                conflicts=[],
                actions_taken=["run_health_agent"],
                data={"raw_response": clean_text},
            )

    except Exception as exc:
        logger.error("Health agent error: %s", exc)
        return AgentResponse(
            agent="health_agent",
            status=AgentStatus.ERROR,
            summary=f"Health agent encountered an error: {exc}",
            conflicts=[],
            actions_taken=[],
            data=None,
        )
