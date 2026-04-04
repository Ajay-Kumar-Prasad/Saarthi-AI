"""
Shared SQLite database connection for the personal assistant system.
All agents share personal_assistant.db — each agent owns its own prefixed tables.
Tables are created with IF NOT EXISTS so multiple agents can coexist safely.
"""

import os
import aiosqlite
from pathlib import Path

# Shared DB path — configurable via env so all agents point to the same file
DATABASE_PATH = os.getenv("DATABASE_PATH", "./personal_assistant.db")


def _get_db_path():
    db_url = os.getenv("DATABASE_URL", "")
    if db_url and db_url.startswith("postgresql"):
        # If you want to use Postgres instead of local SQLite, set DATABASE_URL.
        # This code path currently prefers local SQLite for compatibility.
        # Keep DATABASE_PATH for local dev.
        return DATABASE_PATH
    return DATABASE_PATH


async def get_db() -> aiosqlite.Connection:
    """Return an open async SQLite connection. Caller is responsible for closing."""
    path = _get_db_path()
    db = await aiosqlite.connect(path)
    db.row_factory = aiosqlite.Row
    await db.execute("PRAGMA journal_mode=WAL")
    await db.execute("PRAGMA foreign_keys=ON")
    return db


async def init_db() -> None:
    """
    Create all health-agent tables (IF NOT EXISTS).
    Called once at FastAPI startup — safe to call even if tables already exist
    from a previous run or from another agent's migration.
    """
    db = await get_db()
    try:
        await db.executescript(HEALTH_SCHEMA_SQL)
        await db.commit()
    finally:
        await db.close()


# ── Health Agent Schema ────────────────────────────────────────────────────────
# Table names are prefixed with `health_` so other agents (work_, finance_, etc.)
# can safely add their own tables without collisions.

HEALTH_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS health_tokens (
    user_id          TEXT PRIMARY KEY,
    access_token     TEXT NOT NULL,
    refresh_token    TEXT NOT NULL,
    token_expiry     TEXT NOT NULL,          -- ISO 8601 datetime
    scopes           TEXT NOT NULL,          -- space-separated scope string
    created_at       TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at       TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS health_sleep_logs (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id          TEXT NOT NULL,
    date             TEXT NOT NULL,          -- YYYY-MM-DD (local date of sleep start)
    start_time       TEXT NOT NULL,          -- ISO 8601
    end_time         TEXT NOT NULL,          -- ISO 8601
    duration_minutes INTEGER NOT NULL,
    sleep_stages     TEXT,                   -- JSON: {light, deep, rem, awake} in minutes
    data_source      TEXT NOT NULL DEFAULT 'google_fit',
    fetched_at       TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(user_id, date)                    -- one record per user per night
);

CREATE TABLE IF NOT EXISTS health_activity_logs (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id          TEXT NOT NULL,
    date             TEXT NOT NULL,          -- YYYY-MM-DD
    activity_type    TEXT NOT NULL,          -- e.g. "running", "walking", "cycling"
    start_time       TEXT NOT NULL,          -- ISO 8601
    end_time         TEXT NOT NULL,          -- ISO 8601
    duration_minutes INTEGER NOT NULL,
    calories_burned  REAL,
    steps            INTEGER,
    distance_meters  REAL,
    avg_heart_rate   REAL,
    data_source      TEXT NOT NULL DEFAULT 'google_fit',
    fetched_at       TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS health_daily_metrics (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id          TEXT NOT NULL,
    date             TEXT NOT NULL,          -- YYYY-MM-DD
    total_steps      INTEGER,
    total_calories   REAL,
    active_minutes   INTEGER,
    resting_heart_rate REAL,
    data_source      TEXT NOT NULL DEFAULT 'google_fit',
    fetched_at       TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(user_id, date)
);
"""
