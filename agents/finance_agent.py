# agents/finance_agent.py
import os
import re
import json
import threading
import logging
from datetime import datetime

try:
    import google.generativeai as genai
except Exception:  # pragma: no cover
    genai = None
from db.finance_db import insert_expense, get_all_expenses
from db.schemas import AgentResponse, AgentStatus

logger = logging.getLogger(__name__)


# ── Google Sheets ─────────────────────────────────────────────────────────────
def _get_sheet():
    import gspread
    from google.oauth2.service_account import Credentials
    creds = Credentials.from_service_account_file(
        "credentials.json",
        scopes=[
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ],
    )
    return gspread.authorize(creds).open("expenses_sheet").sheet1


# ── Tool functions (all accept user_id) ───────────────────────────────────────
def _save_expense(amount, category, description="", user_id=None):
    now = datetime.now()
    try:
        insert_expense(amount, category, description, now, user_id)
    except Exception as e:
        logger.exception("DB write failed in finance tool")
    try:
        _get_sheet().append_row([str(now), amount, category, description])
    except Exception as e:
        logger.warning("Sheets write failed: %s", e)
    return f"✅ Saved ₹{amount} for {category}"


def _get_last_expense(user_id=None):
    rows = get_all_expenses(user_id)
    if not rows:
        return "No expenses found."
    r = rows[0]
    return f"🧾 Last: ₹{r[0]} on {r[2]} ({r[3].strftime('%d %b')})"


def _get_spending_summary(user_id=None):
    rows = get_all_expenses(user_id)
    if not rows:
        return "No data."
    summary = {}
    for amount, category, *_ in rows:
        summary[category] = summary.get(category, 0) + float(amount)
    return "📊 Summary:\n" + "\n".join(f"- {k}: ₹{v}" for k, v in summary.items())


def _get_weekly_spending(user_id=None):
    rows = get_all_expenses(user_id)
    total = sum(float(r[0]) for r in rows)
    msg = f"📅 Total spending: ₹{total}"
    if total > 3000:
        msg += "\n⚠️ High spending!"
    return msg


# ── Gmail sync ────────────────────────────────────────────────────────────────
def sync_gmail_expenses():
    def _run():
        try:
            from tools.gmail_mcp import read_messages_and_save
            read_messages_and_save(_get_sheet())
        except Exception as e:
            logger.exception("Gmail sync error")
    threading.Thread(target=_run, daemon=True).start()


# ── Prompt ────────────────────────────────────────────────────────────────────
PROMPT_TEMPLATE = """
You are a finance assistant inside a multi-agent AI system.
Convert the user message into EXACTLY ONE tool call as raw JSON.

TOOLS:
1. save_expense         → user mentions spending / paying / buying something
2. get_last_expense     → user asks about last / recent expense
3. get_spending_summary → user asks for summary / breakdown by category
4. get_weekly_spending  → user asks weekly / total spending

Return ONLY raw JSON, no markdown, no explanation:
{{"tool": "tool_name", "args": {{}}}}

If the message has nothing to do with finance, return:
{{"tool": "none", "args": {{}}}}

User: {user_msg}
"""


# ── Orchestrator entry point ───────────────────────────────────────────────────
async def run_finance_agent(message: str, user_id: str) -> AgentResponse:
    try:
        if genai is None:
            return AgentResponse(
                agent="finance_agent",
                status=AgentStatus.ERROR,
                summary="google-generativeai dependency is missing. Install required dependencies.",
                conflicts=[],
                actions_taken=[],
                data=None,
            )
        genai.configure(api_key=os.environ["GEMINI_API_KEY"])
        model = genai.GenerativeModel("gemini-2.5-flash")

        response = model.generate_content(PROMPT_TEMPLATE.format(user_msg=message))
        clean = re.sub(r"```json|```", "", response.text.strip()).strip()

        try:
            action = json.loads(clean)
        except json.JSONDecodeError:
            return AgentResponse(
                agent="finance_agent",
                status=AgentStatus.PARTIAL,
                summary="No finance action needed.",
                conflicts=[], actions_taken=[], data=None,
            )

        tool_name = action.get("tool")

        # Non-finance message — bow out gracefully
        if tool_name == "none" or not tool_name:
            return AgentResponse(
                agent="finance_agent",
                status=AgentStatus.PARTIAL,
                summary="No finance action needed.",
                conflicts=[], actions_taken=[], data=None,
            )

        # Build tool map with user_id in closure
        tool_map = {
            "save_expense": lambda a: _save_expense(
                a.get("amount", 0), a.get("category", "other"),
                a.get("description", ""), user_id,
            ),
            "get_last_expense":      lambda _: _get_last_expense(user_id),
            "get_spending_summary":  lambda _: _get_spending_summary(user_id),
            "get_weekly_spending":   lambda _: _get_weekly_spending(user_id),
        }

        tool_fn = tool_map.get(tool_name)
        if not tool_fn:
            return AgentResponse(
                agent="finance_agent",
                status=AgentStatus.PARTIAL,
                summary=f"Unknown finance tool: {tool_name}",
                conflicts=[], actions_taken=[], data=None,
            )

        result = tool_fn(action.get("args", {}))

        return AgentResponse(
            agent="finance_agent",
            status=AgentStatus.OK,
            summary=result,
            conflicts=[],
            actions_taken=[tool_name],
            data={"tool": tool_name, "args": action.get("args", {})},
        )

    except KeyError:
        return AgentResponse(
            agent="finance_agent",
            status=AgentStatus.ERROR,
            summary="GEMINI_API_KEY is not configured.",
            conflicts=[],
            actions_taken=[],
            data=None,
        )
    except Exception as e:
        logger.exception("Finance agent failed")
        return AgentResponse(
            agent="finance_agent",
            status=AgentStatus.ERROR,
            summary=f"Finance agent error: {e}",
            conflicts=[], actions_taken=[], data=None,
        )