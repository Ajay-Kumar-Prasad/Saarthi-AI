from fastapi import APIRouter, HTTPException

from agents.learning_agent import normalize_agent_response, run_learning_agent
from db.schemas import AgentResponse
from routers.dependencies import ensure_agent_success
from routers.schemas import ChatRequest, StatusRequest


router = APIRouter(prefix="/learning", tags=["learning"])


async def _run_learning_request(req: ChatRequest) -> AgentResponse:
    try:
        return ensure_agent_success(await run_learning_agent(req.message, req.user_id))
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Learning endpoint failed: {exc}") from exc


@router.post("/chat", response_model=AgentResponse)
async def learning_chat(req: ChatRequest):
    return await _run_learning_request(req)


@router.post("/status", response_model=AgentResponse)
async def learning_status(req: StatusRequest):
    from agents.learning_agent import tool_get_learning_status

    try:
        raw = await tool_get_learning_status(req.user_id)
        return normalize_agent_response(raw, "learning_agent", "tool_get_learning_status")
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Learning status failed: {exc}") from exc


@router.post("/add-resource", response_model=AgentResponse)
async def learning_add_resource(req: ChatRequest):
    return await _run_learning_request(req)


@router.post("/schedule", response_model=AgentResponse)
async def learning_schedule(req: ChatRequest):
    return await _run_learning_request(req)


@router.post("/query", response_model=AgentResponse)
async def learning_query(req: ChatRequest):
    return await _run_learning_request(req)
