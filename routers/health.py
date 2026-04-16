from fastapi import APIRouter, HTTPException

from agents.health_agent import run_health_agent, sync_all_health_data
from db.health_db import get_health_summary
from db.schemas import AgentResponse, AgentStatus
from routers.dependencies import ensure_agent_success
from routers.schemas import ChatRequest, StatusRequest, SyncRequest


router = APIRouter(prefix="/health", tags=["health"])


@router.post("/chat", response_model=AgentResponse)
async def health_chat(req: ChatRequest):
    try:
        return ensure_agent_success(await run_health_agent(req.message, req.user_id))
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Health chat failed: {exc}") from exc


@router.post("/status", response_model=AgentResponse)
async def health_status(req: StatusRequest):
    try:
        summary = await get_health_summary(req.user_id)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to fetch health status: {exc}") from exc
    return AgentResponse(
        agent="health_agent",
        status=AgentStatus.OK,
        summary=f"Health summary generated.",
        conflicts=[],
        actions_taken=["get_health_summary"],
        data={"summary": summary},
    )


@router.post("/sync", response_model=AgentResponse)
async def health_sync(req: SyncRequest):
    try:
        result = await sync_all_health_data(req.user_id, req.days)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to sync health data: {exc}") from exc
    return AgentResponse(
        agent="health_agent",
        status=AgentStatus.OK,
        summary=f"Health sync completed for {req.days} day(s).",
        conflicts=[],
        actions_taken=["sync_all_health_data"],
        data={"synced": result},
    )


@router.post("/trends", response_model=AgentResponse)
async def health_trends(req: ChatRequest):
    try:
        return ensure_agent_success(await run_health_agent(req.message, req.user_id))
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Health trends failed: {exc}") from exc


@router.post("/query", response_model=AgentResponse)
async def health_query(req: ChatRequest):
    try:
        return ensure_agent_success(await run_health_agent(req.message, req.user_id))
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Health query failed: {exc}") from exc
