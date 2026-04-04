"""
Saarthi AI — FastAPI application entrypoint for the Health Agent.

For solo testing of just your agent, run:
    uvicorn health_agent.main:app --reload --port 8081

Then hit:
    GET  /auth/google/login?user_id=<uuid>
    GET  /auth/google/callback?code=...&state=<uuid>
    POST /health/status
    POST /health/chat
    POST /health/sync
    POST /health/trends
    POST /health/query
"""

import json
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from db.health_db import build_health_summary

from db.database import init_db
from models.schemas import AgentResponse
from agents.health_agent import run_health_agent, tool_get_agent_status, sync_all_health_data
from auth.google_oauth import router as auth_router, is_user_authenticated

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Saarthi AI — Health Agent service starting")
    await init_db()
    logger.info("AlloyDB pool ready.")
    yield
    logger.info("Saarthi AI — Health Agent shutting down")


app = FastAPI(
    title="Saarthi AI — Health Agent",
    description=(
        "Personal AI guide for your physical health. "
        "Tracks sleep, fitness, steps, and heart rate via Google Fit. "
        "Part of the Saarthi multi-agent system."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],    # tighten in production
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Google OAuth2 routes at /auth
app.include_router(auth_router)


# ── Request bodies ────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str
    user_id: str = "00000000-0000-0000-0000-000000000001"  # demo default


class StatusRequest(BaseModel):
    user_id: str = "00000000-0000-0000-0000-000000000001"
    days: int = 7


class SyncRequest(BaseModel):
    user_id: str = "00000000-0000-0000-0000-000000000001"
    days: int = 30


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    """Liveness probe for Cloud Run."""
    return {"status": "ok", "agent": "health_agent", "service": "saarthi-ai"}


@app.post("/health/chat", response_model=AgentResponse)
async def health_chat(req: ChatRequest):
    """
    Natural language interface to the Health Agent.

    Example messages:
    - "How did I sleep this week?"
    - "Show me my workouts for the last 7 days"
    - "How many steps did I take today?"
    - "What is my resting heart rate trend?"
    - "Analyze my health trends for the past two weeks"
    - "How am I doing overall health-wise?"
    """
    response = await run_health_agent(req.message, req.user_id)
    if response.status == "error":
        raise HTTPException(status_code=500, detail=response.summary)
    return response


@app.post("/health/status")
async def get_status(req: StatusRequest):
    """
    Quick status endpoint — returns the health summary without an LLM call.
    Useful for the Streamlit dashboard sidebar or the orchestrator's health check.
    """
    summary = await build_health_summary(req.user_id, days=req.days)
    return json.loads(summary.model_dump_json())


@app.post("/health/sync")
async def sync_health_data(req: SyncRequest):
    """
    Re-pull Google Fit data and update AlloyDB for this user.

    This is the ONLY endpoint that calls the Google Fit API directly.
    It is called automatically once during OAuth onboarding.
    Users can also call it manually here to refresh their stored data.

    During normal /health/chat the agent reads from AlloyDB only.
    """
    result = await sync_all_health_data(req.user_id, req.days)
    return {"status": "ok", "synced": result}


@app.post("/health/trends")
async def trends_endpoint(req: ChatRequest):
    """
    Health trend analysis endpoint.
    Example: "What are my sleep and activity trends for the past two weeks?"
    """
    return await run_health_agent(req.message, req.user_id)


@app.post("/health/query")
async def nl_query_endpoint(req: ChatRequest):
    """
    AlloyDB AI natural language query over health history.
    Example: "How many times did I work out last month?"
    """
    return await run_health_agent(req.message, req.user_id)
