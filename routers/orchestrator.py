from fastapi import APIRouter, HTTPException

from agents.orchestrator import run_orchestrator
from db.schemas import AgentResponse
from routers.schemas import OrchestratorRequest, StatusRequest


router = APIRouter(tags=["orchestrator"])


@router.post("/chat", response_model=AgentResponse)
async def chat(req: OrchestratorRequest):
    try:
        return await run_orchestrator(req.message, req.user_id, req.domains)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Orchestrator failed: {exc}") from exc


@router.post("/proactive/morning-briefing", response_model=AgentResponse)
async def morning_briefing(req: StatusRequest):
    try:
        return await run_orchestrator(
            "Good morning. Give me my full daily briefing across all life domains.",
            req.user_id,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Morning briefing failed: {exc}") from exc
