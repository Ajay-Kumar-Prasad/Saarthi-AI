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

@router.post("/tasks", response_model=AgentResponse)
async def get_tasks(req: ChatRequest):
    try:
        from db.work_db import get_all_tasks

        tasks = await get_all_tasks(req.user_id)

        return AgentResponse(
            agent="work_agent",
            status="ok",
            summary=f"{len(tasks)} tasks fetched",
            actions_taken=["get_all_tasks"],
            data={
                "tasks": tasks
            }
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@router.post("/tasks/create", response_model=AgentResponse)
async def create_task_api(req: ChatRequest):
    try:
        from tools.task_mcp import create_task

        result = await create_task(
            user_id=req.user_id,
            title=req.message
        )

        return AgentResponse(
            agent="work_agent",
            status="ok",
            summary="Task created",
            actions_taken=["create_task"],
            data=result
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

