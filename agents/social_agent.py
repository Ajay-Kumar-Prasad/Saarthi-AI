import logging
from typing import Any

from db.schemas import AgentResponse, AgentStatus

logger = logging.getLogger(__name__)


def _build_response(
    status: AgentStatus,
    summary: str,
    actions_taken: list[str] | None = None,
    data: dict[str, Any] | None = None,
    conflicts: list[str] | None = None,
) -> AgentResponse:
    return AgentResponse(
        agent="social_agent",
        status=status,
        summary=summary,
        conflicts=conflicts or [],
        actions_taken=actions_taken or [],
        data=data,
    )


def _validate_inputs(message: str, user_id: str) -> AgentResponse | None:
    if not isinstance(user_id, str) or not user_id.strip():
        return _build_response(AgentStatus.ERROR, "Missing required user_id.")
    if not isinstance(message, str) or not message.strip():
        return _build_response(AgentStatus.ERROR, "Missing required message.")
    return None


async def run_social_agent(message: str, user_id: str) -> AgentResponse:
    invalid = _validate_inputs(message, user_id)
    if invalid:
        return invalid

    try:
        from db.social_db import get_all_interactions
        interactions = await get_all_interactions(user_id)
        total = len(interactions)
        
        logger.info("Social agent called for user_id=%s, interactions=%s", user_id.strip(), total)
        return _build_response(
            AgentStatus.OK,
            f"{total} interactions found",
            actions_taken=["get_all_interactions"],
            data={
                "raw": {
                    "interactions": interactions
                },
                "insight": f"{total} interactions found"
            },
        )
    except Exception as exc:
        logger.exception("Social agent execution failed user_id=%s", user_id)
        return _build_response(AgentStatus.ERROR, f"Social agent error: {exc}")
