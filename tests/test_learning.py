"""
Saarthi AI — Learning Agent Tests

Run with:
    MOCK_MCP=true pytest tests/ -v

All tests use MOCK_MCP=true so they don't need real MCP servers or AlloyDB.
For AlloyDB functions, we use unittest.mock to patch get_connection.
"""

import json
import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timedelta

# ── Tool function tests (no DB required) ─────────────────────────────────────

@pytest.mark.asyncio
async def test_find_free_slot_returns_slot_when_morning_is_free():
    """If there are no events before 10am, a 6am slot should be returned."""
    import os
    os.environ["MOCK_MCP"] = "true"

    from tools.learning_tools import find_free_slot
    slot = await find_free_slot(
        user_id="test-user",
        date="2026-04-10",
        duration_minutes=60,
    )
    assert slot is not None
    assert slot["start"] < slot["end"]


@pytest.mark.asyncio
async def test_find_free_slot_avoids_mock_busy_blocks():
    """
    Mock calendar has standup 8:30-9am and deep-focus 10am-12pm.
    A 2-hour slot should start at 6am (before standup).
    """
    import os
    os.environ["MOCK_MCP"] = "true"

    from tools.learning_tools import find_free_slot
    slot = await find_free_slot(
        user_id="test-user",
        date="2026-04-10",
        duration_minutes=120,
    )
    assert slot is not None
    # Should start at 6am, well before the standup
    assert slot["start"].hour == 6


@pytest.mark.asyncio
async def test_save_learning_note_mock():
    import os
    os.environ["MOCK_MCP"] = "true"

    from tools.learning_tools import save_learning_note
    result = await save_learning_note(
        user_id="test-user",
        resource_title="Python Crash Course",
        note_content="Learned about list comprehensions.",
        tags=["python"],
    )
    assert result["saved"] is True
    assert "note_id" in result


@pytest.mark.asyncio
async def test_create_study_calendar_event_mock():
    import os
    os.environ["MOCK_MCP"] = "true"

    from tools.learning_tools import create_study_calendar_event
    result = await create_study_calendar_event(
        user_id="test-user",
        title="Study: Python Crash Course",
        start_time=datetime(2026, 4, 10, 8, 0, 0),
        duration_minutes=60,
    )
    assert "event_id" in result
    assert result["event_id"] == "mock-cal-event-001"


# ── DB layer tests (with mocked AlloyDB connection) ───────────────────────────

@pytest.fixture
def mock_conn():
    """Returns a mocked asyncpg connection."""
    conn = AsyncMock()
    conn.close = AsyncMock()
    return conn


@pytest.mark.asyncio
async def test_get_weekly_study_hours(mock_conn):
    mock_conn.fetchrow.return_value = {"hours": 4.5}

    with patch("db.learning_db.get_connection", return_value=mock_conn):
        from db.learning_db import get_weekly_study_hours
        hours = await get_weekly_study_hours("test-user")

    assert hours == 4.5


@pytest.mark.asyncio
async def test_get_study_streak_consecutive_days(mock_conn):
    today = datetime.utcnow().date()
    yesterday = today - timedelta(days=1)
    two_days_ago = today - timedelta(days=2)

    mock_conn.fetch.return_value = [
        {"study_date": today},
        {"study_date": yesterday},
        {"study_date": two_days_ago},
    ]

    with patch("db.learning_db.get_connection", return_value=mock_conn):
        from db.learning_db import get_study_streak
        streak = await get_study_streak("test-user")

    assert streak == 3


@pytest.mark.asyncio
async def test_get_study_streak_broken(mock_conn):
    today = datetime.utcnow().date()
    three_days_ago = today - timedelta(days=3)   # gap — streak is broken

    mock_conn.fetch.return_value = [
        {"study_date": today},
        {"study_date": three_days_ago},
    ]

    with patch("db.learning_db.get_connection", return_value=mock_conn):
        from db.learning_db import get_study_streak
        streak = await get_study_streak("test-user")

    assert streak == 1   # only today counts


@pytest.mark.asyncio
async def test_get_all_resources(mock_conn):
    mock_conn.fetch.return_value = [
        {
            "id": "res-001",
            "user_id": "test-user",
            "title": "Python Crash Course",
            "resource_type": "book",
            "status": "in_progress",
            "progress_pct": 45,
        }
    ]

    with patch("db.learning_db.get_connection", return_value=mock_conn):
        from db.learning_db import get_all_resources
        resources = await get_all_resources("test-user", status="in_progress")

    assert len(resources) == 1
    assert resources[0]["title"] == "Python Crash Course"


# ── Agent tool function tests ─────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_tool_get_learning_status():
    import os
    os.environ["MOCK_MCP"] = "true"

    mock_conn = AsyncMock()
    mock_conn.close = AsyncMock()
    mock_conn.fetch.return_value = []
    mock_conn.fetchrow.return_value = {"hours": 3.0}

    with patch("db.learning_db.get_connection", return_value=mock_conn):
        from agents.learning_agent import tool_get_learning_status
        result_str = await tool_get_learning_status("test-user")
        result = json.loads(result_str)

    assert "resources" in result
    assert "upcoming_sessions" in result
    assert "streak_days" in result
    assert "weekly_hours_studied" in result


@pytest.mark.asyncio
async def test_tool_add_learning_resource():
    mock_conn = AsyncMock()
    mock_conn.close = AsyncMock()
    mock_conn.fetchrow.return_value = {
        "id": "res-new-001",
        "user_id": "test-user",
        "title": "Atomic Habits",
        "resource_type": "book",
        "status": "not_started",
        "progress_pct": 0,
        "tags": ["habits", "productivity"],
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }

    with patch("db.learning_db.get_connection", return_value=mock_conn):
        from agents.learning_agent import tool_add_learning_resource
        result_str = await tool_add_learning_resource(
            user_id="test-user",
            title="Atomic Habits",
            resource_type="book",
            author="James Clear",
            tags="habits,productivity",
        )
        result = json.loads(result_str)

    assert result["created"] is True
    assert result["resource"]["title"] == "Atomic Habits"


@pytest.mark.asyncio
async def test_tool_schedule_detects_no_free_slot():
    """When the calendar is full, the tool should return conflict=True."""
    import os
    os.environ["MOCK_MCP"] = "true"

    # Override find_free_slot to return None (no slot available)
    with patch("agents.learning_agent.find_free_slot", return_value=None):
        from agents.learning_agent import tool_schedule_study_session
        result_str = await tool_schedule_study_session(
            user_id="test-user",
            resource_id="res-001",
            resource_title="Python Crash Course",
            date="2026-04-10",
            duration_minutes=60,
        )
        result = json.loads(result_str)

    assert result["conflict"] is True
    assert "No free" in result["message"]


# ── Schema contract tests ─────────────────────────────────────────────────────

def test_agent_response_schema():
    from models.schemas import AgentResponse, AgentStatus
    resp = AgentResponse(
        agent="learning_agent",
        status=AgentStatus.OK,
        summary="User is studying 2 courses and has a 5-day streak.",
        conflicts=["Study block on 2026-04-10 overlaps with standup"],
        actions_taken=["Fetched learning status from AlloyDB"],
        data={"streak_days": 5, "weekly_hours": 4.5},
    )
    assert resp.agent == "learning_agent"
    assert len(resp.conflicts) == 1
    dumped = resp.model_dump()
    assert dumped["status"] == "ok"