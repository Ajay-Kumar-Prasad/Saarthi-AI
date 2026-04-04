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
    from db.schemas import AgentResponse, AgentStatus
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

@pytest.mark.asyncio
async def test_compute_skill_gap_missing_skills():
    """User with only Python should have a large gap for Data Engineer."""
    mock_conn = AsyncMock()
    mock_conn.close = AsyncMock()
 
    # Role requirements
    mock_conn.fetch.side_effect = [
        # get role requirements
        [
            {"skill_name": "Python",         "importance": "required"},
            {"skill_name": "SQL",            "importance": "required"},
            {"skill_name": "Apache Spark",   "importance": "required"},
            {"skill_name": "Apache Airflow", "importance": "required"},
            {"skill_name": "Docker",         "importance": "recommended"},
        ],
        # get user skills
        [
            {"skill_name": "Python", "proficiency": "intermediate"},
        ],
    ]
 
    with patch("db.learning_db.get_connection", return_value=mock_conn):
        from db.learning_db import compute_skill_gap
        result = await compute_skill_gap("test-user", "Data Engineer")
 
    assert "Python" in result["matched"]
    assert "SQL" in result["missing_required"]
    assert "Apache Spark" in result["missing_required"]
    assert result["readiness_pct"] < 50     # large gap
    assert result["gap_score"] > 50
 
 
@pytest.mark.asyncio
async def test_compute_skill_gap_no_gap():
    """User who has all skills should have readiness_pct = 100."""
    mock_conn = AsyncMock()
    mock_conn.close = AsyncMock()
 
    skills = ["Python", "SQL", "Apache Spark"]
    mock_conn.fetch.side_effect = [
        [{"skill_name": s, "importance": "required"} for s in skills],
        [{"skill_name": s, "proficiency": "advanced"} for s in skills],
    ]
 
    with patch("db.learning_db.get_connection", return_value=mock_conn):
        from db.learning_db import compute_skill_gap
        result = await compute_skill_gap("test-user", "Data Engineer")
 
    assert result["missing_required"] == []
    assert result["readiness_pct"] == 100
 
 
@pytest.mark.asyncio
async def test_tool_analyze_skill_gap_unknown_role():
    """Unknown role should return available roles list."""
    mock_conn = AsyncMock()
    mock_conn.close = AsyncMock()
    mock_conn.fetch.return_value = [
        {"role_name": "Data Engineer"},
        {"role_name": "ML Engineer"},
    ]
 
    with patch("db.learning_db.get_connection", return_value=mock_conn):
        from agents.learning_agent import tool_analyze_skill_gap
        result_str = await tool_analyze_skill_gap("test-user", "Astronaut")
        result = json.loads(result_str)
 
    assert "error" in result
    assert "available_roles" in result
 
 
# =============================================================================
# FEATURE 2 — SPACED REPETITION
# =============================================================================
 
@pytest.mark.asyncio
async def test_sm2_correct_answer_increases_interval():
    """A correct answer (quality=4) should increase the interval."""
    mock_conn = AsyncMock()
    mock_conn.close = AsyncMock()
 
    # Simulate a card with interval=1, repetitions=1, ease_factor=2.5
    mock_conn.fetchrow.side_effect = [
        # SELECT existing card
        {
            "id": "card-001",
            "ease_factor": 2.5,
            "interval_days": 1,
            "repetitions": 1,
        },
        # UPDATE result
        {
            "id": "card-001",
            "ease_factor": 2.5,
            "interval_days": 6,
            "repetitions": 2,
            "next_review_at": datetime.utcnow() + timedelta(days=6),
            "last_reviewed_at": datetime.utcnow(),
        },
    ]
 
    with patch("db.learning_db.get_connection", return_value=mock_conn):
        from db.learning_db import update_flashcard_after_review
        result = await update_flashcard_after_review("card-001", "test-user", quality=4)
 
    assert result["interval_days"] == 6
    assert result["repetitions"] == 2
 
 
@pytest.mark.asyncio
async def test_sm2_wrong_answer_resets_interval():
    """A wrong answer (quality=1) should reset interval to 1 day."""
    mock_conn = AsyncMock()
    mock_conn.close = AsyncMock()
 
    mock_conn.fetchrow.side_effect = [
        # Existing card with high interval
        {
            "id": "card-002",
            "ease_factor": 2.5,
            "interval_days": 14,
            "repetitions": 4,
        },
        # After reset
        {
            "id": "card-002",
            "ease_factor": 2.5,
            "interval_days": 1,
            "repetitions": 0,
            "next_review_at": datetime.utcnow() + timedelta(days=1),
            "last_reviewed_at": datetime.utcnow(),
        },
    ]
 
    with patch("db.learning_db.get_connection", return_value=mock_conn):
        from db.learning_db import update_flashcard_after_review
        result = await update_flashcard_after_review("card-002", "test-user", quality=1)
 
    assert result["interval_days"] == 1
    assert result["repetitions"] == 0
 
 
@pytest.mark.asyncio
async def test_tool_flashcard_due_action():
    """Due action should return list of due flashcards and stats."""
    mock_conn = AsyncMock()
    mock_conn.close = AsyncMock()
    mock_conn.fetch.return_value = [
        {
            "id": "card-001",
            "question": "What is a list comprehension?",
            "answer": "[x for x in range(10)]",
            "resource_title": "Python Crash Course",
            "next_review_at": datetime.utcnow() - timedelta(hours=1),
        }
    ]
    mock_conn.fetchrow.return_value = {
        "total_cards": 5,
        "due_now": 1,
        "reviewed_at_least_once": 3,
        "avg_ease_factor": 2.4,
        "max_streak": 4,
    }
 
    with patch("db.learning_db.get_connection", return_value=mock_conn):
        from agents.learning_agent import tool_schedule_flashcard_review
        result_str = await tool_schedule_flashcard_review("test-user", action="due")
        result = json.loads(result_str)
 
    assert result["action"] == "due"
    assert result["due_count"] == 1
    assert len(result["cards"]) == 1
 
 
# =============================================================================
# FEATURE 3 — COURSE RECOMMENDATIONS
# =============================================================================
 
@pytest.mark.asyncio
async def test_tool_recommend_resources_returns_context():
    """Recommendation tool should return structured context for the agent to reason over."""
    mock_conn = AsyncMock()
    mock_conn.close = AsyncMock()
    mock_conn.fetch.side_effect = [
        # completed resources
        [{"title": "Python Crash Course", "tags": ["python"]}],
        # in_progress
        [{"title": "GCP Certificate", "progress_pct": 60, "tags": ["cloud"]}],
        # goals
        [{"title": "Get GCP certified", "target_date": None, "weekly_hours_target": 8}],
        # skills
        [{"skill_name": "Python", "proficiency": "intermediate"}],
        # compute_skill_gap requirements
        [
            {"skill_name": "Python", "importance": "required"},
            {"skill_name": "SQL", "importance": "required"},
        ],
        # compute_skill_gap user skills
        [{"skill_name": "Python", "proficiency": "intermediate"}],
    ]
 
    with patch("db.learning_db.get_connection", return_value=mock_conn):
        from agents.learning_agent import tool_recommend_resources
        result_str = await tool_recommend_resources("test-user", goal="become a data engineer")
        result = json.loads(result_str)
 
    assert "recommendation_context" in result
    assert "instruction_for_agent" in result
    ctx = result["recommendation_context"]
    assert len(ctx["completed_resources"]) == 1
    assert ctx["user_goal"] == "become a data engineer"
 
 
# =============================================================================
# FEATURE 4 — LEARNING PATHS
# =============================================================================
 
@pytest.mark.asyncio
async def test_create_learning_path():
    """Creating a path should return path container + steps."""
    mock_conn = AsyncMock()
    mock_conn.close = AsyncMock()
 
    # get_available_roles
    mock_conn.fetch.side_effect = [
        [{"role_name": "Data Engineer"}],          # available roles
        # compute_skill_gap calls
        [{"skill_name": "SQL", "importance": "required"}],
        [{"skill_name": "Python", "proficiency": "intermediate"}],
        # get user resources
        [
            {
                "id": "res-001", "title": "Python Crash Course",
                "resource_type": "book", "status": "in_progress",
                "progress_pct": 45, "tags": ["python"],
            }
        ],
    ]
 
    # create_learning_path fetchrow
    mock_conn.fetchrow.side_effect = [
        {
            "id": "path-001",
            "user_id": "test-user",
            "title": "Road to Data Engineer",
            "target_role": "Data Engineer",
            "status": "active",
            "estimated_weeks": 2,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        },
        # add_path_step fetchrow
        {
            "id": "step-001",
            "path_id": "path-001",
            "resource_id": "res-001",
            "step_order": 1,
            "title": "Python Crash Course",
            "why_this": "Covers skills needed for Data Engineer.",
            "status": "pending",
            "estimated_hours": 4,
        },
    ]
 
    with patch("db.learning_db.get_connection", return_value=mock_conn):
        from agents.learning_agent import tool_create_learning_path
        result_str = await tool_create_learning_path(
            user_id="test-user",
            action="create",
            title="Road to Data Engineer",
            target_role="Data Engineer",
        )
        result = json.loads(result_str)
 
    assert result["action"] == "created"
    assert "path" in result
    assert result["total_steps"] >= 1
 
 
@pytest.mark.asyncio
async def test_update_path_step_to_completed():
    """Marking a step as completed should update its status."""
    mock_conn = AsyncMock()
    mock_conn.close = AsyncMock()
 
    # update_path_step_status
    mock_conn.fetchrow.side_effect = [
        {
            "id": "step-001",
            "path_id": "path-001",
            "step_order": 1,
            "status": "completed",
            "completed_at": datetime.utcnow(),
        },
        # get_learning_path — path row
        {
            "id": "path-001",
            "user_id": "test-user",
            "title": "Road to Data Engineer",
            "status": "active",
            "estimated_weeks": 4,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "target_role": "Data Engineer",
            "description": "test",
        },
    ]
    # get_learning_path — steps fetch
    mock_conn.fetch.return_value = [
        {
            "id": "step-001", "path_id": "path-001",
            "step_order": 1, "title": "Python Crash Course",
            "status": "completed", "why_this": "test",
            "estimated_hours": 10, "completed_at": datetime.utcnow(),
            "resource_title": "Python Crash Course",
            "resource_status": "in_progress",
            "progress_pct": 45, "resource_type": "book", "url": None,
        }
    ]
 
    with patch("db.learning_db.get_connection", return_value=mock_conn):
        from agents.learning_agent import tool_create_learning_path
        result_str = await tool_create_learning_path(
            user_id="test-user",
            action="update_step",
            path_id="path-001",
            step_order=1,
            step_status="completed",
        )
        result = json.loads(result_str)
 
    assert result["action"] == "step_updated"
    assert result["step"]["status"] == "completed"


@pytest.mark.asyncio
async def test_tool_update_progress_rejects_invalid_percent():
    from agents.learning_agent import tool_update_progress
    result_str = await tool_update_progress(
        user_id="test-user",
        resource_id="res-001",
        progress_pct=120,
    )
    result = json.loads(result_str)
    assert "error" in result
    assert "progress_pct" in result["error"]


@pytest.mark.asyncio
async def test_create_flashcard_unauthorized_resource(mock_conn):
    mock_conn.close = AsyncMock()
    # ownership check fails -> no insert
    mock_conn.fetchrow.return_value = None
    with patch("db.learning_db.get_connection", return_value=mock_conn):
        from db.learning_db import create_flashcard
        card = await create_flashcard(
            user_id="test-user",
            resource_id="res-other-user",
            question="Q?",
            answer="A",
        )
    assert card == {}


@pytest.mark.asyncio
async def test_tool_schedule_flashcard_review_missing_data():
    from agents.learning_agent import tool_schedule_flashcard_review
    result_str = await tool_schedule_flashcard_review(
        user_id="test-user",
        action="create",
        resource_id="",
        question="",
        answer="",
    )
    result = json.loads(result_str)
    assert "error" in result
