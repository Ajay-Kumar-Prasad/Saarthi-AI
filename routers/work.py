from fastapi import APIRouter, HTTPException

from agents.work_agent import run_work_agent
from db.schemas import AgentResponse
from routers.dependencies import ensure_agent_success
from routers.schemas import ChatRequest


router = APIRouter(prefix="/work", tags=["work"])


@router.post("/chat", response_model=AgentResponse)
async def work_chat(req: ChatRequest):
    try:
        return ensure_agent_success(await run_work_agent(req.message, req.user_id))
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Work endpoint failed: {exc}") from exc
