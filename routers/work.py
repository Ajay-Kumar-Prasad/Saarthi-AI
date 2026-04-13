from fastapi import APIRouter

from agents.work_agent import run_work_agent
from db.schemas import AgentResponse
from routers.dependencies import ensure_agent_success
from routers.schemas import ChatRequest


router = APIRouter(prefix="/work", tags=["work"])


@router.post("/chat", response_model=AgentResponse)
async def work_chat(req: ChatRequest):
    return ensure_agent_success(await run_work_agent(req.message, req.user_id))
