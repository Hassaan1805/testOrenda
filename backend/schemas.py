from __future__ import annotations

from typing import Optional
from pydantic import BaseModel


class ReflectRequest(BaseModel):
    date: Optional[str] = None  # ISO yyyy-mm-dd
    mood: str
    journal_text: str

