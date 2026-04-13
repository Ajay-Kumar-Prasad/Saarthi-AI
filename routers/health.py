from fastapi import APIRouter

from agents.health_agent import run_health_agent, sync_all_health_data
from db.health_db import build_health_summary
from db.schemas import AgentResponse
from routers.dependencies import ensure_agent_success
from routers.schemas import ChatRequest, StatusRequest, SyncRequest


router = APIRouter(prefix="/health", tags=["health"])


@router.post("/chat", response_model=AgentResponse)
async def health_chat(req: ChatRequest):
    return ensure_agent_success(await run_health_agent(req.message, req.user_id))


@router.post("/status")
async def health_status(req: StatusRequest):
    summary = await build_health_summary(req.user_id, days=req.days)
    return summary.model_dump()


@router.post("/sync")
async def health_sync(req: SyncRequest):
    result = await sync_all_health_data(req.user_id, req.days)
    return {"status": "ok", "synced": result}


@router.post("/trends", response_model=AgentResponse)
async def health_trends(req: ChatRequest):
    return ensure_agent_success(await run_health_agent(req.message, req.user_id))


@router.post("/query", response_model=AgentResponse)
async def health_query(req: ChatRequest):
    return ensure_agent_success(await run_health_agent(req.message, req.user_id))
