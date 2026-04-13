from fastapi import APIRouter

from agents.learning_agent import normalize_agent_response, run_learning_agent
from db.schemas import AgentResponse
from routers.dependencies import ensure_agent_success
from routers.schemas import ChatRequest, StatusRequest


router = APIRouter(prefix="/learning", tags=["learning"])


@router.post("/chat", response_model=AgentResponse)
async def learning_chat(req: ChatRequest):
    return ensure_agent_success(await run_learning_agent(req.message, req.user_id))


@router.post("/status", response_model=AgentResponse)
async def learning_status(req: StatusRequest):
    from agents.learning_agent import tool_get_learning_status

    raw = await tool_get_learning_status(req.user_id)
    return normalize_agent_response(raw, "learning_agent", "tool_get_learning_status")


@router.post("/add-resource", response_model=AgentResponse)
async def learning_add_resource(req: ChatRequest):
    return ensure_agent_success(await run_learning_agent(req.message, req.user_id))


@router.post("/schedule", response_model=AgentResponse)
async def learning_schedule(req: ChatRequest):
    return ensure_agent_success(await run_learning_agent(req.message, req.user_id))


@router.post("/query", response_model=AgentResponse)
async def learning_query(req: ChatRequest):
    return ensure_agent_success(await run_learning_agent(req.message, req.user_id))
