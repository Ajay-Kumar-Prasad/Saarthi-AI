from fastapi import APIRouter, HTTPException

from agents.social_agent import run_social_agent
from db.schemas import AgentResponse
from routers.dependencies import ensure_agent_success
from routers.schemas import ChatRequest


router = APIRouter(prefix="/social", tags=["social"])


@router.post("/chat", response_model=AgentResponse)
async def social_chat(req: ChatRequest):
    try:
        return ensure_agent_success(await run_social_agent(req.message, req.user_id))
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Social endpoint failed: {exc}") from exc
