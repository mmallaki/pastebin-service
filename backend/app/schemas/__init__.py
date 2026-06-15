"""Pydantic schemas for API request/response validation."""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


class ExpirationType(str, Enum):
    """Allowed paste expiration durations."""
    TEN_MINUTES = "10min"
    ONE_HOUR = "1hr"
    ONE_DAY = "1day"
    ONE_WEEK = "1week"
    NEVER = "never"


class PasteCreate(BaseModel):
    """Request body for creating a new paste."""
    title: Optional[str] = Field(None, max_length=255)
    content: str = Field(..., min_length=1, max_length=1048576)  # max 1MB
    language: str = Field("text", max_length=50)
    expiration: ExpirationType = ExpirationType.NEVER


class PasteResponse(BaseModel):
    """API response shape for a single paste."""
    id: str
    share_key: str
    title: Optional[str]
    content: str
    language: str
    expiration: str
    views: int
    created_at: datetime
    updated_at: datetime
    expires_at: Optional[datetime]


class PasteListResponse(BaseModel):
    """Paginated list of pastes."""
    pastes: List[PasteResponse]
    total: int
    page: int
    per_page: int


class StatsResponse(BaseModel):
    """Paste statistics summary."""
    total_pastes: int
    active_pastes: int
    pastes_today: int
    top_languages: List[dict]
