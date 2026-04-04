"""
Saarthi AI — Shared Pydantic schemas.

AgentResponse is the integration CONTRACT between all agents and the orchestrator.
Every agent (health, learning, finance, work, social) MUST return this exact shape.
The orchestrator reads .conflicts to build cross-domain insights.

Contract (do not change field names without team sign-off):
    {
        "agent":        str,        # agent name e.g. "health_agent"
        "status":       str,        # "ok" | "error" | "partial"
        "summary":      str,        # one human-readable paragraph
        "conflicts":    list[str],  # cross-domain conflict strings
        "actions_taken":list[str],  # tools / steps the agent executed
        "data":         dict | None # raw structured payload for orchestrator
    }
"""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


# ── Agent contract ────────────────────────────────────────────────────────────

class AgentStatus(str, Enum):
    OK      = "ok"
    ERROR   = "error"
    PARTIAL = "partial"


class AgentResponse(BaseModel):
    """
    The single response contract every agent MUST return.
    Field names are frozen — changing them breaks orchestrator integration.
    """
    agent:         str                  = Field(..., description="Agent identifier e.g. 'health_agent'")
    status:        AgentStatus          = Field(..., description="ok | error | partial")
    summary:       str                  = Field(..., description="Human-readable one-paragraph summary")
    conflicts:     list[str]            = Field(default_factory=list, description="Cross-domain conflict strings")
    actions_taken: list[str]            = Field(default_factory=list, description="Tools / steps executed")
    data:          dict[str, Any] | None = Field(default=None, description="Raw structured payload for orchestrator")


# ── Health domain schemas ─────────────────────────────────────────────────────

class SleepSession(BaseModel):
    date:             str
    start_time:       str
    end_time:         str
    duration_minutes: float
    sleep_stages:     dict[str, int] | None = None   # {"light": 120, "deep": 60, "rem": 90, "awake": 15}


class ActivitySession(BaseModel):
    date:             str
    activity_type:    str
    start_time:       str
    end_time:         str
    duration_minutes: float
    calories_burned:  float | None = None
    steps:            int   | None = None
    distance_meters:  float | None = None
    avg_heart_rate:   int   | None = None


class DailyMetrics(BaseModel):
    date:               str
    total_steps:        int   | None = None
    total_calories:     float | None = None
    active_minutes:     int   | None = None
    resting_heart_rate: int   | None = None


class HealthSummary(BaseModel):
    user_id:                str
    period_days:            int
    sleep_sessions:         list[SleepSession]    = Field(default_factory=list)
    activity_sessions:      list[ActivitySession] = Field(default_factory=list)
    daily_metrics:          list[DailyMetrics]    = Field(default_factory=list)
    avg_sleep_minutes:      float | None = None
    avg_steps:              float | None = None
    avg_resting_heart_rate: float | None = None
    total_active_minutes:   int   | None = None

