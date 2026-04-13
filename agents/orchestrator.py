import asyncio
import logging
from typing import Any

from agents.finance_agent import run_finance_agent
from agents.health_agent import run_health_agent
from agents.learning_agent import run_learning_agent
from agents.social_agent import run_social_agent
from agents.work_agent import run_work_agent
from db.schemas import AgentResponse, AgentStatus

logger = logging.getLogger(__name__)


def _detect_cross_domain_conflicts(responses: list[AgentResponse]) -> list[str]:
    cross: list[str] = []
    by_agent = {r.agent: r for r in responses}

    health = by_agent.get("health_agent")
    work = by_agent.get("work_agent")
    learning = by_agent.get("learning_agent")

    # Low sleep + hard training
    if health and work:
        h_data = health.data or {}
        avg_sleep = h_data.get("avg_sleep_hours")
        if avg_sleep is None and isinstance(h_data.get("health_summary"), dict):
            sleep_min = h_data["health_summary"].get("avg_sleep_minutes")
            avg_sleep = (float(sleep_min) / 60.0) if sleep_min else None
        if (avg_sleep or 8) < 6 and work.data and work.data.get("high_priority_tasks", 0) > 3:
            cross.append(f"Low sleep ({avg_sleep}h avg) combined with high task load — risk of burnout.")

    if learning and work:
        l_conflicts = [c for c in (learning.conflicts or []) if "conflict" in c.lower()]
        if l_conflicts:
            cross.append(f"Study session blocked by work calendar: {l_conflicts[0]}")

    return cross


def _domain_runners() -> dict[str, Any]:
    return {
        "work": run_work_agent,
        "health": run_health_agent,
        "learning": run_learning_agent,
        "finance": run_finance_agent,
        "social": run_social_agent,
    }


async def run_orchestrator(message: str, user_id: str, domains: list[str] | None = None) -> dict:
    runners = _domain_runners()

    if domains:
        requested = {d.strip().lower() for d in domains}
        unknown = sorted(requested - set(runners.keys()))
        if unknown:
            logger.warning("Ignoring unknown orchestrator domains: %s", unknown)
        runners = {k: v for k, v in runners.items() if k in requested}
        if not runners:
            return {
                "summary": "No valid domains requested.",
                "agent_responses": [],
                "cross_domain_conflicts": [],
                "all_conflicts": [],
                "all_actions": [],
            }

    tasks = {name: fn(message, user_id) for name, fn in runners.items()}
    results = await asyncio.gather(*tasks.values(), return_exceptions=True)
    responses: list[AgentResponse] = []

    for name, result in zip(tasks.keys(), results):
        if isinstance(result, Exception):
            logger.error("Agent %s raised exception: %s", name, result)
            responses.append(AgentResponse(
                agent=f"{name}_agent", status=AgentStatus.ERROR,
                summary=f"{name} agent failed: {result}",
                conflicts=[], actions_taken=[], data=None,
            ))
        else:
            responses.append(result)

    cross_conflicts = _detect_cross_domain_conflicts(responses)
    all_conflicts = cross_conflicts + [c for r in responses for c in (r.conflicts or [])]
    all_actions = [a for r in responses for a in (r.actions_taken or [])]

    summaries = [r.summary for r in responses if r.status != AgentStatus.ERROR and r.summary]
    combined_summary = " | ".join(summaries) if summaries else "All agents checked."

    return {
        "summary": combined_summary,
        "agent_responses": [r.model_dump() for r in responses],
        "cross_domain_conflicts": cross_conflicts,
        "all_conflicts": all_conflicts,
        "all_actions": all_actions,
    }
