"""
Pydantic models for the Health Agent.

AgentResponse is the shared orchestrator contract — all agents on the team
return this same shape so the orchestrator can aggregate responses uniformly.
"""

from enum import Enum
from datetime import date, datetime
from typing import Any
from pydantic import BaseModel, Field


# ── Shared Orchestrator Contract ───────────────────────────────────────────────

class AgentStatus(str, Enum):
    OK      = "ok"
    ERROR   = "error"
    PARTIAL = "partial"


class AgentResponse(BaseModel):
    """
    Standardized response schema shared across all agents (health, work, finance, etc.).
    The orchestrator aggregates these to detect conflicts and synthesize a final response.
    Matches the schema used by the Learning Agent and other Saarthi agents.
    """
    agent: str = "health_agent"
    status: AgentStatus = AgentStatus.OK
    summary: str = ""                                        # one-line human-readable summary
    conflicts: list[str] = Field(default_factory=list)      # cross-domain conflict flags
    actions_taken: list[str] = Field(default_factory=list)  # tools / steps the agent ran
    data: dict[str, Any] | None = None                      # raw structured data


# ── Internal Tool Data Models ─────────────────────────────────────────────────

class SleepSession(BaseModel):
    date: str                                    # YYYY-MM-DD
    start_time: str                              # ISO 8601
    end_time: str                                # ISO 8601
    duration_minutes: int
    sleep_stages: dict[str, int] | None = None  # light/deep/rem/awake in minutes

class ActivitySession(BaseModel):
    date: date
    activity_type: str
    start_time: datetime
    end_time: datetime
    duration_minutes: int
    calories_burned: float | None = None
    steps: int | None = None
    distance_meters: float | None = None
    avg_heart_rate: float | None = None

class DailyMetrics(BaseModel):
    date: str
    total_steps: int | None = None
    total_calories: float | None = None
    active_minutes: int | None = None
    resting_heart_rate: float | None = None

class HealthSummary(BaseModel):
    user_id: str
    date: date
    total_steps: int | None = None
    total_calories: float | None = None
    active_minutes: int | None = None
    sleep_duration_min: int | None = None
