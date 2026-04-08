from contextlib import asynccontextmanager
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from agents.finance_agent import run_finance_agent, sync_gmail_expenses
from agents.health_agent import run_health_agent, sync_all_health_data
from agents.learning_agent import normalize_agent_response, run_learning_agent
from agents.orchestrator import run_orchestrator
from agents.social_agent import run_social_agent
from agents.work_agent import run_work_agent
from auth.google_oauth import router as auth_router
from db.finance_db import get_all_expenses
from db.health_db import build_health_summary
from db.schemas import AgentResponse

load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(
    title="Saarthi AI",
    description="Multi-agent personal intelligence system.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(auth_router)


class ChatRequest(BaseModel):
    message: str
    user_id: str = "00000000-0000-0000-0000-000000000001"


class StatusRequest(BaseModel):
    user_id: str = "00000000-0000-0000-0000-000000000001"
    days: int = 7


class SyncRequest(BaseModel):
    user_id: str = "00000000-0000-0000-0000-000000000001"
    days: int = 30


class OrchestratorRequest(BaseModel):
    message: str
    user_id: str = "00000000-0000-0000-0000-000000000001"
    domains: Optional[list[str]] = None


@app.get("/health")
def health():
    return {"status": "ok", "service": "saarthi-ai"}


@app.post("/chat")
async def chat(req: OrchestratorRequest):
    return await run_orchestrator(req.message, req.user_id, req.domains)


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


@app.post("/work/chat", response_model=AgentResponse)
async def work_chat(req: ChatRequest):
    return await run_work_agent(req.message, req.user_id)


@app.post("/health/chat", response_model=AgentResponse)
async def health_chat(req: ChatRequest):
    response = await run_health_agent(req.message, req.user_id)
    if response.status == "error":
        raise HTTPException(status_code=500, detail=response.summary)
    return response


@app.post("/health/status")
async def health_status(req: StatusRequest):
    summary = await build_health_summary(req.user_id, days=req.days)
    return summary.model_dump()


@app.post("/health/sync")
async def health_sync(req: SyncRequest):
    result = await sync_all_health_data(req.user_id, req.days)
    return {"status": "ok", "synced": result}


@app.post("/health/trends")
async def health_trends(req: ChatRequest):
    return await run_health_agent(req.message, req.user_id)


@app.post("/health/query")
async def health_query(req: ChatRequest):
    return await run_health_agent(req.message, req.user_id)


@app.post("/agent/finance")
async def finance_chat(req: ChatRequest):
    result = await run_finance_agent(req.message, req.user_id)
    return {"reply": result.summary}


@app.get("/finance/expenses")
def finance_expenses(user_id: str | None = None):
    rows = get_all_expenses(user_id)
    expenses = [
        {
            "id": i,
            "amount": float(r[0]),
            "category": r[1],
            "description": r[2],
            "date": r[3].isoformat() if hasattr(r[3], "isoformat") else str(r[3]),
        }
        for i, r in enumerate(rows)
    ]
    return {"expenses": expenses}


@app.get("/finance/summary")
def finance_summary(user_id: str | None = None):
    rows = get_all_expenses(user_id)
    totals: dict[str, float] = {}
    for amount, category, *_ in rows:
        totals[category] = totals.get(category, 0.0) + float(amount)
    summary = [{"category": k, "total": v} for k, v in totals.items()]
    return {"summary": summary}


@app.post("/sync-gmail")
def sync_gmail():
    sync_gmail_expenses()
    return {"message": "Gmail sync started"}


@app.post("/social/chat", response_model=AgentResponse)
async def social_chat(req: ChatRequest):
    return await run_social_agent(req.message, req.user_id)


@app.post("/proactive/morning-briefing")
async def morning_briefing(req: StatusRequest):
    return await run_orchestrator(
        "Good morning. Give me my full daily briefing across all life domains.",
        req.user_id,
    )
