from typing import Optional

from pydantic import BaseModel, Field

from core.config import get_settings

_settings = get_settings()


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    user_id: str = _settings.default_user_id


class StatusRequest(BaseModel):
    user_id: str = _settings.default_user_id
    days: int = Field(default=7, ge=1, le=90)


class SyncRequest(BaseModel):
    user_id: str = _settings.default_user_id
    days: int = Field(default=30, ge=1, le=90)


class OrchestratorRequest(BaseModel):
    message: str = Field(..., min_length=1)
    user_id: str = _settings.default_user_id
    domains: Optional[list[str]] = None
