from fastapi import APIRouter

from agents.finance_agent import run_finance_agent, sync_gmail_expenses
from db.finance_db import get_all_expenses
from db.schemas import AgentResponse
from routers.dependencies import ensure_agent_success
from routers.schemas import ChatRequest


router = APIRouter(tags=["finance"])


@router.post("/agent/finance", response_model=AgentResponse)
async def finance_chat(req: ChatRequest):
    return ensure_agent_success(await run_finance_agent(req.message, req.user_id))


@router.get("/finance/expenses")
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


@router.get("/finance/summary")
def finance_summary(user_id: str | None = None):
    rows = get_all_expenses(user_id)
    totals: dict[str, float] = {}
    for amount, category, *_ in rows:
        totals[category] = totals.get(category, 0.0) + float(amount)
    summary = [{"category": k, "total": v} for k, v in totals.items()]
    return {"summary": summary}


@router.post("/sync-gmail")
def sync_gmail():
    sync_gmail_expenses()
    return {"message": "Gmail sync started"}
