"""
Saarthi AI — FastAPI application entrypoint.

This file is Member 4's responsibility to wire up fully.
As the Learning Agent owner, you contribute:
  - /learning/* routes (defined here)
  - The /chat endpoint calls the full orchestrator (defined by Member 2)

For solo testing of just your agent, run:
    uvicorn main:app --reload --port 8080

Then hit:
    POST /learning/status
    POST /learning/add-resource
    POST /learning/schedule
    POST /learning/query
"""

import json

from agents.health_agent import run_health_agent, sync_all_health_data
from db.health_db import build_health_summary
from dotenv import load_dotenv
load_dotenv()
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from agents.learning_agent import run_learning_agent, learning_agent, normalize_agent_response
from db.schemas import AgentResponse
from auth.google_oauth import router as auth_router, is_user_authenticated


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Saarthi AI — Learning Agent service starting")
    yield
    logger.info("Saarthi AI — shutting down")


app = FastAPI(
    title="Saarthi AI — Learning Agent",
    description="Personal AI guide for your learning journey. "
                "Part of the Saarthi multi-agent system.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],    # tighten in production
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(auth_router)


# ── Request bodies ────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str
    user_id: str = "00000000-0000-0000-0000-000000000001"  # demo default


class StatusRequest(BaseModel):
    user_id: str = "00000000-0000-0000-0000-000000000001"

class SyncRequest(BaseModel):
    user_id: str = "00000000-0000-0000-0000-000000000001"
    days: int = 30

# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    """Liveness probe for Cloud Run."""
    return {"status": "ok", "agent": "learning_agent", "service": "saarthi-ai"}


@app.post("/learning/chat", response_model=AgentResponse)
async def learning_chat(req: ChatRequest):
    """
    Natural language interface to the Learning Agent.

    Example messages:
    - "What am I currently studying?"
    - "Add 'Atomic Habits' to my reading list"
    - "Schedule 1 hour of study for Python Crash Course tomorrow"
    - "I finished chapter 9, I'm now on page 280"
    - "How many hours have I studied this week?"
    - "Save this note: learned about list comprehensions today"
    """
    response = await run_learning_agent(req.message, req.user_id)
    if response.status == "error":
        raise HTTPException(status_code=500, detail=response.summary)
    return response


@app.post("/learning/status", response_model=AgentResponse)
async def get_status(req: StatusRequest):
    """
    Quick status endpoint — returns the learning snapshot without an
    LLM call. Useful for the Streamlit dashboard sidebar.
    """
    from agents.learning_agent import tool_get_learning_status
    raw = await tool_get_learning_status(req.user_id)
    return normalize_agent_response(raw, "learning_agent", "tool_get_learning_status")


@app.post("/learning/add-resource")
async def add_resource_endpoint(req: ChatRequest):
    """
    Convenience endpoint: pass a natural language request to add a resource.
    The Learning Agent interprets it and calls the correct tool.

    Example message: "Add 'Deep Work' by Cal Newport to my book list"
    """
    return await run_learning_agent(req.message, req.user_id)


@app.post("/learning/schedule")
async def schedule_endpoint(req: ChatRequest):
    """
    Natural language scheduling.
    Example: "Schedule 90 minutes of Python study for next Monday"
    """
    return await run_learning_agent(req.message, req.user_id)


@app.post("/learning/query")
async def nl_query_endpoint(req: ChatRequest):
    """
    AlloyDB AI natural language query over learning history.
    Example: "How many books have I completed this year?"
    """
    return await run_learning_agent(req.message, req.user_id)


# main.py
from dotenv import load_dotenv
load_dotenv()

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional

from agents.orchestrator import run_orchestrator
from agents.learning_agent import run_learning_agent, normalize_agent_response
from db.schemas import AgentResponse

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Saarthi AI — starting up")
    yield
    logger.info("Saarthi AI — shutting down")


app = FastAPI(
    title="Saarthi AI",
    description="सारथी — Multi-agent personal intelligence system.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Shared request bodies ─────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str
    user_id: str = "00000000-0000-0000-0000-000000000001"

class StatusRequest(BaseModel):
    user_id: str = "00000000-0000-0000-0000-000000000001"

class OrchestratorRequest(BaseModel):
    message: str
    user_id: str = "00000000-0000-0000-0000-000000000001"
    domains: Optional[list[str]] = None   # ["learning","health"] or None = all


# ── Health check ──────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok", "service": "saarthi-ai"}


# ── Orchestrator (main chat endpoint) ─────────────────────────────────────────

@app.post("/chat")
async def chat(req: OrchestratorRequest):
    """
    Full multi-agent orchestration. Pass domains=["learning","health"] to
    query only specific agents. Default queries all five.
    """
    return await run_orchestrator(req.message, req.user_id, req.domains)


# ── Learning agent routes ─────────────────────────────────────────────────────

@app.post("/learning/chat", response_model=AgentResponse)
async def learning_chat(req: ChatRequest):
    response = await run_learning_agent(req.message, req.user_id)
    if response.status == "error":
        raise HTTPException(status_code=500, detail=response.summary)
    return response

@app.post("/learning/status", response_model=AgentResponse)
async def learning_status(req: StatusRequest):
    from agents.learning_agent import tool_get_learning_status
    raw = await tool_get_learning_status(req.user_id)
    return normalize_agent_response(raw, "learning_agent", "tool_get_learning_status")

@app.post("/learning/add-resource", response_model=AgentResponse)
async def learning_add_resource(req: ChatRequest):
    return await run_learning_agent(req.message, req.user_id)

@app.post("/learning/schedule", response_model=AgentResponse)
async def learning_schedule(req: ChatRequest):
    return await run_learning_agent(req.message, req.user_id)

@app.post("/learning/query", response_model=AgentResponse)
async def learning_query(req: ChatRequest):
    return await run_learning_agent(req.message, req.user_id)


# ── Work agent routes (Hariharan adds these) ──────────────────────────────────

@app.post("/work/chat", response_model=AgentResponse)
async def work_chat(req: ChatRequest):
    from agents.work_agent import run_work_agent
    return await run_work_agent(req.message, req.user_id)


# ── Health agent routes (Joshna adds these) ───────────────────────────────────

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


# ── Finance agent routes (Shubham adds these) ─────────────────────────────────

@app.post("/finance/chat", response_model=AgentResponse)
async def finance_chat(req: ChatRequest):
    from agents.finance_agent import run_finance_agent
    return await run_finance_agent(req.message, req.user_id)


# ── Social agent routes (Team adds these) ─────────────────────────────────────

@app.post("/social/chat", response_model=AgentResponse)
async def social_chat(req: ChatRequest):
    from agents.social_agent import run_social_agent
    return await run_social_agent(req.message, req.user_id)


# ── Proactive morning briefing (Cloud Scheduler hits this) ────────────────────

@app.post("/proactive/morning-briefing")
async def morning_briefing(req: StatusRequest):
    return await run_orchestrator(
        "Good morning. Give me my full daily briefing across all life domains.",
        req.user_id,
    )


# ── Privacy / GDPR ────────────────────────────────────────────────────────────

@app.delete("/user/{user_id}/all-data")
async def erase_user_data(user_id: str):
    from db.alloydb import get_connection
    conn = await get_connection()
    try:
        tables = ["life_logs", "study_sessions", "study_goals", "learning_resources",
                  "flashcards", "learning_paths", "learning_path_steps",
                  "user_skills", "goals"]
        for table in tables:
            await conn.execute(f"DELETE FROM {table} WHERE user_id = $1", user_id)
        return {"erased": True, "user_id": user_id, "tables": tables}
    finally:
        await conn.close()