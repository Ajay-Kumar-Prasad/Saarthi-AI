from fastapi import APIRouter

from agents.orchestrator import run_orchestrator
from routers.schemas import OrchestratorRequest, StatusRequest


router = APIRouter(tags=["orchestrator"])


@router.post("/chat")
async def chat(req: OrchestratorRequest):
    return await run_orchestrator(req.message, req.user_id, req.domains)


@router.post("/proactive/morning-briefing")
async def morning_briefing(req: StatusRequest):
    return await run_orchestrator(
        "Good morning. Give me my full daily briefing across all life domains.",
        req.user_id,
    )
