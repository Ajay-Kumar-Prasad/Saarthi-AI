import json
import logging
import os
import re
import threading
from datetime import datetime
from typing import Any

from db.finance_db import get_all_expenses, insert_expense
from db.schemas import AgentResponse, AgentStatus

try:
    import google.generativeai as genai
except Exception:  # pragma: no cover
    genai = None

logger = logging.getLogger(__name__)


PROMPT_TEMPLATE = """
You are a finance assistant inside a multi-agent AI system.
Convert the user message into EXACTLY ONE tool call as raw JSON.

TOOLS:
1. save_expense         -> user mentions spending / paying / buying something
2. get_last_expense     -> user asks about last / recent expense
3. get_spending_summary -> user asks for summary / breakdown by category
4. get_weekly_spending  -> user asks weekly / total spending

Return ONLY raw JSON, no markdown, no explanation:
{{"tool": "tool_name", "args": {{}}}}

If the message has nothing to do with finance, return:
{{"tool": "none", "args": {{}}}}

User: {user_msg}
"""


def _build_response(
    status: AgentStatus,
    summary: str,
    actions_taken: list[str] | None = None,
    data: dict[str, Any] | None = None,
    conflicts: list[str] | None = None,
) -> AgentResponse:
    return AgentResponse(
        agent="finance_agent",
        status=status,
        summary=summary,
        conflicts=conflicts or [],
        actions_taken=actions_taken or [],
        data=data,
    )


def _get_sheet():
    try:
        import gspread
        from google.oauth2.service_account import Credentials
    except Exception as exc:
        logger.warning("Sheets dependencies unavailable: %s", exc)
        return None

    try:
        creds = Credentials.from_service_account_file(
            "credentials.json",
            scopes=[
                "https://www.googleapis.com/auth/spreadsheets",
                "https://www.googleapis.com/auth/drive",
            ],
        )
        return gspread.authorize(creds).open("expenses_sheet").sheet1
    except Exception as exc:
        logger.warning("Unable to initialize Google Sheet client: %s", exc)
        return None


def _safe_get_expenses(user_id: str) -> list[Any]:
    try:
        return get_all_expenses(user_id)
    except Exception as exc:
        logger.exception("Failed to fetch expenses for user_id=%s", user_id)
        return []


def _save_expense(args: dict[str, Any], user_id: str) -> tuple[str, list[str], dict[str, Any]]:
    warnings: list[str] = []
    raw_amount = args.get("amount", 0)
    category = str(args.get("category", "other") or "other").strip() or "other"
    description = str(args.get("description", "") or "").strip()

    try:
        amount = float(raw_amount)
    except (TypeError, ValueError):
        return "Invalid amount value.", ["invalid_amount"], {"raw_amount": raw_amount}

    if amount <= 0:
        return "Amount must be greater than zero.", ["invalid_amount"], {"amount": amount}

    now = datetime.utcnow()
    db_saved = False
    sheet_saved = False

    try:
        insert_expense(amount, category, description, now, user_id)
        db_saved = True
    except Exception:
        logger.exception("DB write failed for user_id=%s", user_id)
        warnings.append("db_write_failed")

    sheet = _get_sheet()
    if sheet:
        try:
            sheet.append_row([str(now), amount, category, description])
            sheet_saved = True
        except Exception as exc:
            logger.warning("Sheets write failed: %s", exc)
            warnings.append("sheets_write_failed")
    else:
        warnings.append("sheets_unavailable")

    if not db_saved and not sheet_saved:
        return "Failed to persist expense to all configured stores.", warnings, {"amount": amount, "category": category}

    return f"Saved {amount:.2f} for {category}.", warnings, {
        "amount": amount,
        "category": category,
        "description": description,
        "db_saved": db_saved,
        "sheet_saved": sheet_saved,
    }


def _get_last_expense(user_id: str) -> tuple[str, list[str], dict[str, Any]]:
    rows = _safe_get_expenses(user_id)
    if not rows:
        return "No expenses found.", [], {"count": 0}

    row = rows[0]
    try:
        message = f"Last expense: {float(row[0]):.2f} in {row[1]} on {row[3]}."
    except Exception:
        message = "Found last expense record."
    return message, [], {"last_expense": str(row)}


def _get_spending_summary(user_id: str) -> tuple[str, list[str], dict[str, Any]]:
    rows = _safe_get_expenses(user_id)
    if not rows:
        return "No expense data available.", [], {"summary": {}}

    totals: dict[str, float] = {}
    for amount, category, *_ in rows:
        totals[str(category)] = totals.get(str(category), 0.0) + float(amount)
    summary_line = ", ".join(f"{k}: {v:.2f}" for k, v in totals.items())
    return f"Spending summary: {summary_line}.", [], {"summary": totals}


def _get_weekly_spending(user_id: str) -> tuple[str, list[str], dict[str, Any]]:
    rows = _safe_get_expenses(user_id)
    total = sum(float(r[0]) for r in rows) if rows else 0.0
    warnings = ["high_spending"] if total > 3000 else []
    message = f"Total spending: {total:.2f}."
    if warnings:
        message += " Spending is higher than threshold."
    return message, warnings, {"total_spending": total, "threshold": 3000}


def sync_gmail_expenses() -> None:
    def _run() -> None:
        try:
            from tools.gmail_mcp import read_messages_and_save
        except Exception as exc:
            logger.warning("Gmail MCP dependency unavailable: %s", exc)
            return

        sheet = _get_sheet()
        if not sheet:
            logger.warning("Skipping Gmail sync because Google Sheet is unavailable.")
            return

        try:
            read_messages_and_save(sheet)
            logger.info("Gmail expense sync completed.")
        except Exception:
            logger.exception("Gmail sync failed")

    threading.Thread(target=_run, daemon=True).start()


def _run_selected_tool(tool_name: str, args: dict[str, Any], user_id: str) -> tuple[str, list[str], dict[str, Any]]:
    tool_map = {
        "save_expense": _save_expense,
        "get_last_expense": lambda _args, uid: _get_last_expense(uid),
        "get_spending_summary": lambda _args, uid: _get_spending_summary(uid),
        "get_weekly_spending": lambda _args, uid: _get_weekly_spending(uid),
    }
    handler = tool_map.get(tool_name)
    if not handler:
        return f"Unknown finance tool: {tool_name}", ["unknown_tool"], {"tool": tool_name}
    return handler(args, user_id)


def _classify_intent_with_llm(message: str) -> dict[str, Any]:
    if genai is None:
        raise RuntimeError("google-generativeai dependency is missing.")

    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not configured.")

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-2.5-flash")
    response = model.generate_content(PROMPT_TEMPLATE.format(user_msg=message))
    raw_text = (response.text or "").strip()
    clean_text = re.sub(r"```json|```", "", raw_text).strip()
    return json.loads(clean_text)


async def run_finance_agent(message: str, user_id: str) -> AgentResponse:
    if not isinstance(message, str) or not message.strip():
        return _build_response(AgentStatus.ERROR, "Message is required.")
    if not isinstance(user_id, str) or not user_id.strip():
        return _build_response(AgentStatus.ERROR, "user_id is required.")

    try:
        action = _classify_intent_with_llm(message.strip())
    except json.JSONDecodeError:
        logger.warning("Finance LLM output was not valid JSON.")
        return _build_response(AgentStatus.PARTIAL, "No finance action needed.")
    except Exception as exc:
        logger.exception("Finance intent classification failed")
        return _build_response(AgentStatus.ERROR, f"Finance intent classification failed: {exc}")

    tool_name = str(action.get("tool", "")).strip()
    args = action.get("args", {})
    if not isinstance(args, dict):
        args = {}

    if tool_name in {"", "none"}:
        return _build_response(AgentStatus.PARTIAL, "No finance action needed.", data={"tool": "none"})

    try:
        summary, warnings, result_data = _run_selected_tool(tool_name, args, user_id.strip())
    except Exception as exc:
        logger.exception("Finance tool execution crashed for tool=%s", tool_name)
        return _build_response(AgentStatus.ERROR, f"Finance tool execution failed: {exc}", actions_taken=[tool_name])

    status = AgentStatus.PARTIAL if warnings else AgentStatus.OK
    return _build_response(
        status=status,
        summary=summary,
        actions_taken=[tool_name],
        conflicts=warnings,
        data={"tool": tool_name, "args": args, "result": result_data},
    )