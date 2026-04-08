from db.schemas import AgentResponse, AgentStatus


async def run_social_agent(message: str, user_id: str) -> AgentResponse:
    return AgentResponse(
        agent="social_agent",
        status=AgentStatus.PARTIAL,
        summary="Social agent not implemented yet",
        conflicts=[],
        actions_taken=[],
        data=None,
    )
