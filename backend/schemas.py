from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class ReflectRequest(BaseModel):
    date: Optional[str] = None  # ISO yyyy-mm-dd
    mood: str
    journal_text: str


class JournalEntryOut(BaseModel):
    """Serialized journal entry returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    mood: str
    journal_text: str
    summary: Optional[str] = None
    emotions: Optional[str] = None
    reflection_questions: Optional[str] = None
    encouragement: Optional[str] = None
    small_goal: Optional[str] = None
    todays_bloom: Optional[str] = None
