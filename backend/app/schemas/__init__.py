from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


class ExpirationType(str, Enum):
    TEN_MINUTES = "10min"
    ONE_HOUR = "1hr"
    ONE_DAY = "1day"
    ONE_WEEK = "1week"
    NEVER = "never"


class PasteCreate(BaseModel):
    title: Optional[str] = Field(None, max_length=255)
    content: str = Field(..., min_length=1, max_length=1048576)
    language: str = Field("text", max_length=50)
    expiration: ExpirationType = ExpirationType.NEVER
    is_private: bool = False


class PasteUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=255)
    content: Optional[str] = Field(None, min_length=1, max_length=1048576)
    language: Optional[str] = Field(None, max_length=50)
    expiration: Optional[ExpirationType] = None


class PasteResponse(BaseModel):
    id: str
    share_key: str
    title: Optional[str]
    content: str
    language: str
    expiration: str
    is_private: bool
    views: int
    created_at: datetime
    updated_at: datetime
    expires_at: Optional[datetime]

    class Config:
        from_attributes = True


class PasteListResponse(BaseModel):
    pastes: List[PasteResponse]
    total: int
    page: int
    per_page: int


class StatsResponse(BaseModel):
    total_pastes: int
    active_pastes: int
    pastes_today: int
    top_languages: List[dict]
