from fastapi import HTTPException

from db.schemas import AgentResponse, AgentStatus


def ensure_agent_success(response: AgentResponse) -> AgentResponse:
    if response.status == AgentStatus.ERROR:
        raise HTTPException(status_code=500, detail=response.summary)
    return response
