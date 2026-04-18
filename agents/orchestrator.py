import asyncio
import logging
from time import perf_counter
from typing import Any, Awaitable, Callable

from agents.finance_agent import run_finance_agent
from agents.health_agent import run_health_agent
from agents.learning_agent import run_learning_agent
from agents.social_agent import run_social_agent
from agents.work_agent import run_work_agent
from db.schemas import AgentResponse, AgentStatus

logger = logging.getLogger(__name__)


AgentRunner = Callable[[str, str], Awaitable[AgentResponse]]


DOMAIN_KEYWORDS: dict[str, set[str]] = {
    "work": {"work", "meeting", "calendar", "task", "email", "deadline"},
    "health": {"health", "sleep", "steps", "workout", "heart", "fitness"},
    "learning": {"learn", "study", "course", "book", "skill", "flashcard"},
    "finance": {"finance", "expense", "spend", "budget", "money", "payment"},
    "social": {"social", "friend", "family", "relationship", "event"},
}


def _normalize_response(name: str, result: Any) -> AgentResponse:
    if isinstance(result, AgentResponse):
        return result

    if isinstance(result, dict):
        try:
            return AgentResponse(**result)
        except Exception:
            logger.warning("Agent %s returned dict not matching AgentResponse.", name)

    return AgentResponse(
        agent=f"{name}_agent",
        status=AgentStatus.PARTIAL,
        summary=f"{name} agent returned an unexpected response format.",
        conflicts=[],
        actions_taken=[],
        data={"raw_result": str(result)},
    )


async def _run_agent(name: str, runner: AgentRunner, message: str, user_id: str) -> AgentResponse:
    start = perf_counter()
    logger.info("Starting %s agent execution", name)
    try:
        raw = await runner(message, user_id)
        response = _normalize_response(name, raw)
        logger.info(
            "Completed %s agent status=%s duration_ms=%d",
            name,
            response.status,
            int((perf_counter() - start) * 1000),
        )
        return response
    except Exception as exc:
        logger.exception("Agent %s failed during execution", name)
        return AgentResponse(
            agent=f"{name}_agent",
            status=AgentStatus.ERROR,
            summary=f"{name} agent failed: {exc}",
            conflicts=[],
            actions_taken=[],
            data=None,
        )


def _resolve_domains(message: str, requested_domains: list[str] | None, valid_domains: set[str]) -> set[str]:
    if requested_domains:
        requested = {d.strip().lower() for d in requested_domains if d and d.strip()}
        unknown = sorted(requested - valid_domains)
        if unknown:
            logger.warning("Ignoring unknown orchestrator domains: %s", unknown)
        return requested & valid_domains

    lowered = (message or "").lower()
    inferred = {
        domain
        for domain, keywords in DOMAIN_KEYWORDS.items()
        if any(keyword in lowered for keyword in keywords)
    }
    return inferred or valid_domains


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


def _domain_runners() -> dict[str, AgentRunner]:
    return {
        "work": run_work_agent,
        "health": run_health_agent,
        "learning": run_learning_agent,
        "finance": run_finance_agent,
        "social": run_social_agent,
    }


async def run_orchestrator(
    message: str, user_id: str, domains: list[str] | None = None
) -> AgentResponse:
    if not isinstance(message, str) or not message.strip():
        return AgentResponse(
            agent="orchestrator",
            status=AgentStatus.ERROR,
            summary="Message is required.",
            conflicts=[],
            actions_taken=[],
            data=None,
        )
    if not isinstance(user_id, str) or not user_id.strip():
        return AgentResponse(
            agent="orchestrator",
            status=AgentStatus.ERROR,
            summary="user_id is required.",
            conflicts=[],
            actions_taken=[],
            data=None,
        )

    message = message.strip()
    user_id = user_id.strip()
    all_runners = _domain_runners()
    selected_domains = _resolve_domains(message, domains, set(all_runners.keys()))
    if not selected_domains:
        return AgentResponse(
            agent="orchestrator",
            status=AgentStatus.PARTIAL,
            summary="No valid domains requested.",
            conflicts=[],
            actions_taken=[],
            data={
                "agent_responses": [],
                "cross_domain_conflicts": [],
                "all_conflicts": [],
                "all_actions": [],
                "domains_ran": [],
            },
        )

    runners = {k: v for k, v in all_runners.items() if k in selected_domains}
    logger.info("Orchestrator executing domains=%s user_id=%s", sorted(runners.keys()), user_id)
    responses = await asyncio.gather(
        *[_run_agent(name, runner, message, user_id) for name, runner in runners.items()]
    )

    cross_conflicts = _detect_cross_domain_conflicts(responses)
    all_conflicts = cross_conflicts + [c for r in responses for c in (r.conflicts or [])]
    all_actions = [a for r in responses for a in (r.actions_taken or [])]

    summaries = [r.summary for r in responses if r.status != AgentStatus.ERROR and r.summary]
    combined_summary = " | ".join(summaries) if summaries else "All agents checked."

    any_error = any(r.status == AgentStatus.ERROR for r in responses)
    status = AgentStatus.PARTIAL if any_error else AgentStatus.OK
    return AgentResponse(
        agent="orchestrator",
        status=status,
        summary=combined_summary,
        conflicts=all_conflicts,
        actions_taken=all_actions,
        data={
            "agent_responses": [r.model_dump() for r in responses],
            "cross_domain_conflicts": cross_conflicts,
            "all_conflicts": all_conflicts,
            "all_actions": all_actions,
            "domains_ran": sorted(runners.keys()),
        },
    )
