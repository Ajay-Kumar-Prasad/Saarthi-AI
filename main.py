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

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from agents.learning_agent import run_learning_agent, learning_agent
from models.schemas import AgentResponse

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


# ── Request bodies ────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str
    user_id: str = "00000000-0000-0000-0000-000000000001"  # demo default


class StatusRequest(BaseModel):
    user_id: str = "00000000-0000-0000-0000-000000000001"


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


@app.post("/learning/status")
async def get_status(req: StatusRequest):
    """
    Quick status endpoint — returns the learning snapshot without an
    LLM call. Useful for the Streamlit dashboard sidebar.
    """
    from agents.learning_agent import tool_get_learning_status
    import json
    raw = await tool_get_learning_status(req.user_id)
    return json.loads(raw)


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