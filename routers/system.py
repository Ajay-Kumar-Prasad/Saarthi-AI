from fastapi import APIRouter

from db.schemas import AgentResponse, AgentStatus


router = APIRouter(tags=["system"])


@router.get("/health", response_model=AgentResponse)
def health_check():
    return AgentResponse(
        agent="system",
        status=AgentStatus.OK,
        summary="Service is healthy.",
        conflicts=[],
        actions_taken=["health_check"],
        data={"service": "saarthi-ai"},
    )
