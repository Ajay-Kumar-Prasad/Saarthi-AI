from fastapi import APIRouter

from agents.social_agent import run_social_agent
from db.schemas import AgentResponse
from routers.dependencies import ensure_agent_success
from routers.schemas import ChatRequest


router = APIRouter(prefix="/social", tags=["social"])


@router.post("/chat", response_model=AgentResponse)
async def social_chat(req: ChatRequest):
    return ensure_agent_success(await run_social_agent(req.message, req.user_id))
