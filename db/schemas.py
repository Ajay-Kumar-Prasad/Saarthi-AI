"""
Saarthi AI — Shared Pydantic schemas and contracts.
Every sub-agent must return an AgentResponse. The orchestrator
depends on this contract — do not change field names.
"""

from pydantic import BaseModel, Field
from typing import Optional, Any
from datetime import datetime
from enum import Enum


class AgentStatus(str, Enum):
    OK = "ok"
    ERROR = "error"
    PARTIAL = "partial"


class AgentResponse(BaseModel):
    """
    Standard response contract for ALL Saarthi sub-agents.
    The orchestrator reads conflicts and actions_taken to build
    cross-domain insights.
    """
    agent: str                              # e.g. "learning_agent"
    status: AgentStatus                     # ok | error | partial
    summary: str                            # human-readable result
    conflicts: list[str] = Field(default_factory=list)
    # e.g. ["Study session clashes with work deadline on Day 5"]
    actions_taken: list[str] = Field(default_factory=list)
    # e.g. ["Scheduled Python course block: Mon 8-9am"]
    data: Optional[dict[str, Any]] = None   # raw data for orchestrator


# ── Learning domain specific models ──────────────────────────────────────────

class LearningResource(BaseModel):
    id: Optional[str] = None
    user_id: str
    title: str
    resource_type: str          # "book" | "course" | "article" | "video"
    url: Optional[str] = None
    author: Optional[str] = None
    domain: str = "learning"
    status: str = "not_started" # not_started | in_progress | completed
    progress_pct: int = 0       # 0-100
    total_pages: Optional[int] = None
    current_page: Optional[int] = None
    notes: Optional[str] = None
    tags: list[str] = Field(default_factory=list)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class StudySession(BaseModel):
    id: Optional[str] = None
    user_id: str
    resource_id: str
    title: str                  # display name for calendar
    scheduled_at: datetime
    duration_minutes: int = 60
    calendar_event_id: Optional[str] = None  # Google Calendar event ID
    completed: bool = False
    notes: Optional[str] = None


class StudyGoal(BaseModel):
    id: Optional[str] = None
    user_id: str
    title: str                  # e.g. "Complete Python Bootcamp"
    resource_id: Optional[str] = None
    target_date: Optional[str] = None   # ISO date string
    weekly_hours_target: float = 5.0
    progress_pct: int = 0
    status: str = "active"      # active | paused | completed


class LearningProgress(BaseModel):
    """Snapshot returned by the agent when summarising a user's learning state."""
    active_resources: list[LearningResource]
    upcoming_sessions: list[StudySession]
    active_goals: list[StudyGoal]
    total_hours_this_week: float
    streak_days: int
    most_recent_resource: Optional[str] = None