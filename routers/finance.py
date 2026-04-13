from fastapi import APIRouter, HTTPException, Query
from fastapi.concurrency import run_in_threadpool

from agents.finance_agent import run_finance_agent, sync_gmail_expenses
from db.finance_db import get_all_expenses
from db.schemas import AgentResponse, AgentStatus
from routers.dependencies import ensure_agent_success
from routers.schemas import ChatRequest


router = APIRouter(tags=["finance"])


@router.post("/agent/finance", response_model=AgentResponse)
async def finance_chat(req: ChatRequest):
    try:
        return ensure_agent_success(await run_finance_agent(req.message, req.user_id))
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Finance chat failed: {exc}") from exc


@router.get("/finance/expenses", response_model=AgentResponse)
async def finance_expenses(user_id: str | None = Query(default=None, min_length=1)):
    try:
        rows = await run_in_threadpool(get_all_expenses, user_id)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to fetch expenses: {exc}") from exc
    expenses = [
        {
            "id": i,
            "amount": float(r[0]),
            "category": r[1],
            "description": r[2],
            "expense_date": r[3].isoformat() if hasattr(r[3], "isoformat") else str(r[3]),
        }
        for i, r in enumerate(rows)
    ]
    return AgentResponse(
        agent="finance_agent",
        status=AgentStatus.OK,
        summary=f"Fetched {len(expenses)} expense record(s).",
        conflicts=[],
        actions_taken=["get_all_expenses"],
        data={"expenses": expenses},
    )


@router.get("/finance/summary", response_model=AgentResponse)
async def finance_summary(user_id: str | None = Query(default=None, min_length=1)):
    try:
        rows = await run_in_threadpool(get_all_expenses, user_id)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to fetch finance summary: {exc}") from exc
    totals: dict[str, float] = {}
    for amount, category, *_ in rows:
        totals[category] = totals.get(category, 0.0) + float(amount)
    summary = [{"category": k, "total": v} for k, v in totals.items()]
    return AgentResponse(
        agent="finance_agent",
        status=AgentStatus.OK,
        summary=f"Computed spending summary across {len(summary)} categorie(s).",
        conflicts=[],
        actions_taken=["get_all_expenses", "summarize_expenses"],
        data={"summary": summary},
    )


@router.post("/sync-gmail", response_model=AgentResponse)
async def sync_gmail():
    try:
        await run_in_threadpool(sync_gmail_expenses)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to start Gmail sync: {exc}") from exc
    return AgentResponse(
        agent="finance_agent",
        status=AgentStatus.OK,
        summary="Gmail sync started.",
        conflicts=[],
        actions_taken=["sync_gmail_expenses"],
        data=None,
    )
