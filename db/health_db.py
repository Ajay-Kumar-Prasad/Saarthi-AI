"""
tools/health_db.py
------------------
AlloyDB (PostgreSQL/asyncpg) read/write helpers for the Health Agent.

All writes use INSERT ... ON CONFLICT DO UPDATE (UPSERT) — calling these
functions repeatedly is safe. Placeholders use Postgres $1, $2, ... syntax.
"""

import json
import logging
from datetime import datetime, timezone

from db.alloydb import get_connection
from models.schemas import SleepSession, ActivitySession, DailyMetrics, HealthSummary

logger = logging.getLogger(__name__)


# ── Write helpers ─────────────────────────────────────────────────────────────

async def save_sleep_sessions(user_id: str, sessions: list[SleepSession]) -> int:
    """
    Persist a list of sleep sessions to health_sleep_logs.
    Returns the number of rows upserted.
    """
    if not sessions:
        return 0

    conn = await get_connection()
    count = 0
    try:
        for session in sessions:
            await conn.execute(
                """
                INSERT INTO health_sleep_logs
                    (user_id, date, start_time, end_time, duration_minutes, sleep_stages)
                VALUES ($1, $2::DATE, $3::TIMESTAMPTZ, $4::TIMESTAMPTZ, $5, $6::JSONB)
                ON CONFLICT (user_id, date) DO UPDATE SET
                    start_time       = EXCLUDED.start_time,
                    end_time         = EXCLUDED.end_time,
                    duration_minutes = EXCLUDED.duration_minutes,
                    sleep_stages     = EXCLUDED.sleep_stages,
                    synced_at        = NOW()
                """,
                user_id,
                session.date,
                session.start_time,
                session.end_time,
                session.duration_minutes,
                json.dumps(session.sleep_stages) if session.sleep_stages else None,
            )
            count += 1
    finally:
        await conn.close()

    logger.info(f"Saved {count} sleep sessions for user {user_id}")
    return count


async def save_activity_sessions(user_id: str, sessions: list[ActivitySession]) -> int:
    """
    Persist a list of activity sessions to health_activity_logs.
    Uses ON CONFLICT (user_id, start_time) DO UPDATE to prevent duplicates on re-sync.
    Returns the number of rows upserted.
    """
    if not sessions:
        return 0

    conn = await get_connection()
    count = 0
    try:
        for session in sessions:
            await conn.execute(
                """
                INSERT INTO health_activity_logs
                    (user_id, date, activity_type, start_time, end_time,
                     duration_minutes, calories_burned, steps, distance_meters, avg_heart_rate)
                VALUES ($1, $2::DATE, $3, $4::TIMESTAMPTZ, $5::TIMESTAMPTZ,
                        $6, $7, $8, $9, $10)
                ON CONFLICT (user_id, start_time) DO UPDATE SET
                    date             = EXCLUDED.date,
                    activity_type    = EXCLUDED.activity_type,
                    end_time         = EXCLUDED.end_time,
                    duration_minutes = EXCLUDED.duration_minutes,
                    calories_burned  = EXCLUDED.calories_burned,
                    steps            = EXCLUDED.steps,
                    distance_meters  = EXCLUDED.distance_meters,
                    avg_heart_rate   = EXCLUDED.avg_heart_rate
                """,
                user_id,
                session.date,
                session.activity_type,
                session.start_time,
                session.end_time,
                session.duration_minutes,
                session.calories_burned,
                session.steps,
                session.distance_meters,
                session.avg_heart_rate,
            )
            count += 1
    finally:
        await conn.close()

    logger.info(f"Upserted {count} activity sessions for user {user_id}")
    return count


async def save_daily_metrics(user_id: str, metrics: list[DailyMetrics]) -> int:
    """
    Persist daily aggregate metrics to health_daily_metrics.
    Uses ON CONFLICT DO UPDATE so re-fetching is always safe.
    Returns the number of rows inserted/updated.
    """
    if not metrics:
        return 0

    conn = await get_connection()
    count = 0
    try:
        for m in metrics:
            # Convert date string to date object if needed
            if isinstance(m.date, str):
                date_obj = datetime.strptime(m.date, "%Y-%m-%d").date()
            else:
                date_obj = m.date
            await conn.execute(
                """
                INSERT INTO health_daily_metrics
                    (user_id, date, total_steps, total_calories, active_minutes, resting_heart_rate)
                VALUES ($1, $2::DATE, $3, $4, $5, $6)
                ON CONFLICT (user_id, date) DO UPDATE SET
                    total_steps        = EXCLUDED.total_steps,
                    total_calories     = EXCLUDED.total_calories,
                    active_minutes     = EXCLUDED.active_minutes,
                    resting_heart_rate = COALESCE(EXCLUDED.resting_heart_rate,
                                                  health_daily_metrics.resting_heart_rate),
                    synced_at          = NOW()
                """,
                user_id,
                date_obj,
                m.total_steps,
                m.total_calories,
                m.active_minutes,
                m.resting_heart_rate,
            )
            count += 1
    finally:
        await conn.close()

    logger.info(f"Saved daily metrics for {count} days for user {user_id}")
    return count


async def update_resting_heart_rate(user_id: str, hr_data: list[dict]) -> None:
    """
    Upsert resting_heart_rate into health_daily_metrics from heart rate fetch results.
    """
    if not hr_data:
        return

    conn = await get_connection()
    try:
        for entry in hr_data:
            await conn.execute(
                """
                INSERT INTO health_daily_metrics (user_id, date, resting_heart_rate)
                VALUES ($1, $2::DATE, $3)
                ON CONFLICT (user_id, date) DO UPDATE SET
                    resting_heart_rate = EXCLUDED.resting_heart_rate,
                    synced_at          = NOW()
                """,
                user_id,
                entry["date"],
                entry["resting_heart_rate"],
            )
    finally:
        await conn.close()


# ── Read helpers ──────────────────────────────────────────────────────────────

async def get_sleep_summary_from_db(user_id: str, days: int = 7) -> list[SleepSession]:
    """Read sleep sessions from AlloyDB for the last `days` days."""
    conn = await get_connection()
    try:
        rows = await conn.fetch(
            """
            SELECT date, start_time, end_time, duration_minutes, sleep_stages
            FROM health_sleep_logs
            WHERE user_id = $1
              AND date::DATE >= CURRENT_DATE - ($2 * INTERVAL '1 day')
            ORDER BY date DESC
            """,
            user_id,
            days,
        )
    finally:
        await conn.close()

    return [
        SleepSession(
            date=str(row["date"]),
            start_time=row["start_time"].isoformat() if row["start_time"] else None,
            end_time=row["end_time"].isoformat() if row["end_time"] else None,
            duration_minutes=row["duration_minutes"],
            sleep_stages=json.loads(row["sleep_stages"]) if row["sleep_stages"] else None,
        )
        for row in rows
    ]


async def get_activity_summary_from_db(
    user_id: str, days: int = 7
) -> list[ActivitySession]:
    """Read activity sessions from AlloyDB for the last `days` days."""
    conn = await get_connection()
    try:
        rows = await conn.fetch(
            """
            SELECT date, activity_type, start_time, end_time, duration_minutes,
                   calories_burned, steps, distance_meters, avg_heart_rate
            FROM health_activity_logs
            WHERE user_id = $1
              AND date::DATE >= CURRENT_DATE - ($2 * INTERVAL '1 day')
            ORDER BY date DESC
            """,
            user_id,
            days,
        )
    finally:
        await conn.close()

    return [
        ActivitySession(
            date=str(row["date"]),
            activity_type=row["activity_type"],
            start_time=row["start_time"].isoformat() if row["start_time"] else None,
            end_time=row["end_time"].isoformat() if row["end_time"] else None,
            duration_minutes=row["duration_minutes"],
            calories_burned=row["calories_burned"],
            steps=row["steps"],
            distance_meters=row["distance_meters"],
            avg_heart_rate=row["avg_heart_rate"],
        )
        for row in rows
    ]


async def get_daily_metrics_from_db(user_id: str, days: int = 7) -> list[DailyMetrics]:
    """Read daily metrics from DB for the last `days` days."""
    conn = await get_connection()
    try:
        rows = await conn.fetch(
            """
            SELECT date, total_steps, total_calories, active_minutes, resting_heart_rate
            FROM health_daily_metrics
            WHERE user_id = $1
              AND date::DATE >= CURRENT_DATE - ($2 * INTERVAL '1 day')
            ORDER BY date DESC
            """,
            user_id,
            days,
        )
        logger.info(f"Fetched daily metrics for {len(rows)} days for user {user_id}")
    finally:
        await conn.close()

    return [
        DailyMetrics(
            date=str(row["date"]),
            total_steps=row["total_steps"],
            total_calories=row["total_calories"],
            active_minutes=row["active_minutes"],
            resting_heart_rate=row["resting_heart_rate"],
        )
        for row in rows
    ]


async def build_health_summary(user_id: str, days: int = 7) -> HealthSummary:
    """
    Aggregate all health data from AlloyDB into a single HealthSummary object.
    Computes averages for sleep, steps, and heart rate across the period.
    """
    sleep_sessions   = await get_sleep_summary_from_db(user_id, days)
    activity_sessions = await get_activity_summary_from_db(user_id, days)
    daily_metrics    = await get_daily_metrics_from_db(user_id, days)

    avg_sleep = (
        round(sum(s.duration_minutes for s in sleep_sessions) / len(sleep_sessions), 1)
        if sleep_sessions else None
    )
    steps_list  = [m.total_steps for m in daily_metrics if m.total_steps is not None]
    avg_steps   = round(sum(steps_list) / len(steps_list), 0) if steps_list else None

    hr_list  = [m.resting_heart_rate for m in daily_metrics if m.resting_heart_rate is not None]
    avg_rhr  = round(sum(hr_list) / len(hr_list), 1) if hr_list else None

    active_mins_list = [m.active_minutes for m in daily_metrics if m.active_minutes is not None]
    total_active     = sum(active_mins_list) if active_mins_list else None

    return HealthSummary(
        user_id=user_id,
        period_days=days,
        sleep_sessions=sleep_sessions,
        activity_sessions=activity_sessions,
        daily_metrics=daily_metrics,
        avg_sleep_minutes=avg_sleep,
        avg_steps=avg_steps,
        avg_resting_heart_rate=avg_rhr,
        total_active_minutes=total_active,
    )
