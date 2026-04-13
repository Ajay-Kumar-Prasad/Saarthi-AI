"""
Proof-of-logic analytics for agent reasoning.

Builds a compact, data-backed signal summary across domains over a validated
time window so orchestrator/agents can reason with concrete facts.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from db.alloydb import get_connection

logger = logging.getLogger(__name__)

DEFAULT_WINDOW_DAYS = 7
MAX_WINDOW_DAYS = 90


def _validate_user_id(user_id: str) -> str:
    if not isinstance(user_id, str) or not user_id.strip():
        raise ValueError("user_id is required.")
    return user_id.strip()


def _normalize_window_days(days: int) -> int:
    if not isinstance(days, int):
        return DEFAULT_WINDOW_DAYS
    if days < 1:
        return 1
    return min(days, MAX_WINDOW_DAYS)


def _time_window(days: int) -> tuple[datetime, datetime, int]:
    safe_days = _normalize_window_days(days)
    end_ts = datetime.now(timezone.utc)
    start_ts = end_ts - timedelta(days=safe_days)
    return start_ts, end_ts, safe_days


def _safe_ratio(numerator: float, denominator: float) -> float:
    if denominator <= 0:
        return 0.0
    return round(numerator / denominator, 4)


async def _fetch_health_snapshot(conn, user_id: str, start_ts: datetime, end_ts: datetime) -> dict[str, Any]:
    row = await conn.fetchrow(
        """
        SELECT
            COUNT(*)                                         AS days_with_metrics,
            COALESCE(AVG(total_steps), 0)                    AS avg_steps,
            COALESCE(AVG(active_minutes), 0)                 AS avg_active_minutes,
            COALESCE(AVG(resting_heart_rate), 0)             AS avg_resting_hr
        FROM health_daily_metrics
        WHERE user_id = $1
          AND date >= $2::date
          AND date <= $3::date
        """,
        user_id,
        start_ts,
        end_ts,
    )
    data = dict(row) if row else {}
    return {
        "days_with_metrics": int(data.get("days_with_metrics", 0) or 0),
        "avg_steps": float(data.get("avg_steps", 0) or 0),
        "avg_active_minutes": float(data.get("avg_active_minutes", 0) or 0),
        "avg_resting_hr": float(data.get("avg_resting_hr", 0) or 0),
    }


async def _fetch_learning_snapshot(conn, user_id: str, start_ts: datetime, end_ts: datetime) -> dict[str, Any]:
    row = await conn.fetchrow(
        """
        SELECT
            COUNT(*) FILTER (WHERE completed = true)                          AS completed_sessions,
            COALESCE(SUM(duration_minutes) FILTER (WHERE completed = true),0) AS completed_minutes,
            COUNT(*) FILTER (WHERE completed = false)                         AS pending_sessions
        FROM study_sessions
        WHERE user_id = $1
          AND scheduled_at >= $2
          AND scheduled_at <= $3
        """,
        user_id,
        start_ts,
        end_ts,
    )
    data = dict(row) if row else {}
    completed_minutes = int(data.get("completed_minutes", 0) or 0)
    return {
        "completed_sessions": int(data.get("completed_sessions", 0) or 0),
        "completed_minutes": completed_minutes,
        "completed_hours": round(completed_minutes / 60.0, 2),
        "pending_sessions": int(data.get("pending_sessions", 0) or 0),
    }


async def _fetch_finance_snapshot(conn, user_id: str, start_ts: datetime, end_ts: datetime) -> dict[str, Any]:
    row = await conn.fetchrow(
        """
        SELECT
            COUNT(*)                              AS expense_count,
            COALESCE(SUM(amount), 0)              AS total_spent,
            COALESCE(AVG(amount), 0)              AS avg_expense
        FROM expenses
        WHERE user_id = $1
          AND date >= $2
          AND date <= $3
        """,
        user_id,
        start_ts,
        end_ts,
    )
    data = dict(row) if row else {}
    return {
        "expense_count": int(data.get("expense_count", 0) or 0),
        "total_spent": float(data.get("total_spent", 0) or 0),
        "avg_expense": float(data.get("avg_expense", 0) or 0),
    }


def _derive_reasoning_signals(
    window_days: int,
    health: dict[str, Any],
    learning: dict[str, Any],
    finance: dict[str, Any],
) -> dict[str, Any]:
    completed_hours = float(learning.get("completed_hours", 0.0))
    avg_steps = float(health.get("avg_steps", 0.0))
    total_spent = float(finance.get("total_spent", 0.0))

    signals = {
        "study_hours_per_day": round(completed_hours / max(window_days, 1), 2),
        "active_days_ratio": _safe_ratio(float(health.get("days_with_metrics", 0)), float(window_days)),
        "spend_per_day": round(total_spent / max(window_days, 1), 2),
        "wellness_flag": "good" if avg_steps >= 7500 else "watch",
        "focus_flag": "strong" if completed_hours >= max(3, window_days * 0.5) else "low",
    }

    recommendations: list[str] = []
    if avg_steps < 7500:
        recommendations.append("Increase daily movement; target at least 7,500 steps.")
    if completed_hours < max(3, window_days * 0.5):
        recommendations.append("Protect learning blocks; current learning time is below target.")
    if total_spent > window_days * 800:
        recommendations.append("Review recent discretionary spending; trend is elevated for the period.")
    if not recommendations:
        recommendations.append("Current cross-domain trends look stable. Maintain consistency.")

    return {"signals": signals, "recommendations": recommendations}


async def build_proof_of_logic(user_id: str, days: int = DEFAULT_WINDOW_DAYS) -> dict[str, Any]:
    """
    Returns a structured, agent-friendly analytical snapshot.
    """
    try:
        safe_user_id = _validate_user_id(user_id)
        start_ts, end_ts, window_days = _time_window(days)
    except ValueError as exc:
        return {
            "status": "error",
            "error": str(exc),
            "window": None,
            "domains": {},
            "reasoning": {},
        }

    conn = await get_connection()
    try:
        health = await _fetch_health_snapshot(conn, safe_user_id, start_ts, end_ts)
        learning = await _fetch_learning_snapshot(conn, safe_user_id, start_ts, end_ts)
        finance = await _fetch_finance_snapshot(conn, safe_user_id, start_ts, end_ts)

        domains = {"health": health, "learning": learning, "finance": finance}
        reasoning = _derive_reasoning_signals(window_days, health, learning, finance)

        if all(
            not any(float(v) > 0 for v in domain.values() if isinstance(v, (int, float)))
            for domain in domains.values()
        ):
            return {
                "status": "partial",
                "error": "No data found in selected time window.",
                "window": {
                    "days": window_days,
                    "start_ts": start_ts.isoformat(),
                    "end_ts": end_ts.isoformat(),
                },
                "domains": domains,
                "reasoning": reasoning,
            }

        return {
            "status": "ok",
            "error": None,
            "window": {
                "days": window_days,
                "start_ts": start_ts.isoformat(),
                "end_ts": end_ts.isoformat(),
            },
            "domains": domains,
            "reasoning": reasoning,
        }
    except Exception as exc:
        logger.exception("build_proof_of_logic failed user_id=%s", safe_user_id)
        return {
            "status": "error",
            "error": f"Failed to build proof-of-logic: {exc}",
            "window": {
                "days": window_days,
                "start_ts": start_ts.isoformat(),
                "end_ts": end_ts.isoformat(),
            },
            "domains": {},
            "reasoning": {},
        }
    finally:
        await conn.close()
