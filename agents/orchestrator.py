# In agents/orchestrator.py — replace the stub run_work_agent function

# Remove this:
# async def run_work_agent(message: str, user_id: str) -> AgentResponse: ...

# Add this import at the top:
from agents.work_agent import run_work_agent
# agents/orchestrator.py
import asyncio
import logging
from db.schemas import AgentResponse, AgentStatus
from agents.finance_agent import run_finance_agent

logger = logging.getLogger(__name__)

# --- Import each agent's runner (add as teammates finish) ---
from agents.learning_agent import run_learning_agent

# Stub runners for agents not yet integrated — replace as each teammate ships
async def run_health_agent(message: str, user_id: str) -> AgentResponse:
    return AgentResponse(agent="health_agent", status=AgentStatus.PARTIAL,
        summary="Health agent not yet integrated.", conflicts=[], actions_taken=[], data=None)

async def run_social_agent(message: str, user_id: str) -> AgentResponse:
    return AgentResponse(agent="social_agent", status=AgentStatus.PARTIAL,
        summary="Social agent not yet integrated.", conflicts=[], actions_taken=[], data=None)


def _detect_cross_domain_conflicts(responses: list[AgentResponse]) -> list[str]:
    """
    Detect conflicts that span multiple agent domains.
    Each agent reports its own domain conflicts in response.conflicts.
    This function looks for conflicts BETWEEN domains.
    """
    cross: list[str] = []
    by_agent = {r.agent: r for r in responses}

    health = by_agent.get("health_agent")
    work = by_agent.get("work_agent")
    learning = by_agent.get("learning_agent")

    # Low sleep + hard training
    if health and work:
        h_data = health.data or {}
        avg_sleep = h_data.get("avg_sleep_hours", 8)
        if avg_sleep < 6 and work.data and work.data.get("high_priority_tasks", 0) > 3:
            cross.append(f"Low sleep ({avg_sleep}h avg) combined with high task load — risk of burnout.")

    # Study session conflicts with calendar
    if learning and work:
        l_conflicts = [c for c in (learning.conflicts or []) if "conflict" in c.lower()]
        if l_conflicts:
            cross.append(f"Study session blocked by work calendar: {l_conflicts[0]}")

    return cross


async def run_orchestrator(message: str, user_id: str, domains: list[str] | None = None) -> dict:
    """
    Run the relevant sub-agents in parallel and synthesize a cross-domain response.
    
    Args:
        message:  The user's natural language request.
        user_id:  The user's UUID.
        domains:  Optional list of domains to query. None = all five agents.
    
    Returns:
        dict with keys: summary, agent_responses, cross_domain_conflicts, all_conflicts, all_actions
    """
    runners = {
        "work":     run_work_agent,
        "health":   run_health_agent,
        "learning": run_learning_agent,
        "finance":  run_finance_agent,
        "social":   run_social_agent,
    }

    if domains:
        runners = {k: v for k, v in runners.items() if k in domains}

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
