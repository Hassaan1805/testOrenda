from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from db import Base


def _utcnow() -> datetime:
    """Return the current time as a timezone-aware UTC datetime."""
    return datetime.now(timezone.utc)


class JournalEntry(Base):
    """A single journal entry and its AI-generated reflection.

    The reflection fields (``summary`` through ``todays_bloom``) are optional
    because an entry may be persisted before (or without) a reflection.
    """

    __tablename__ = "journal_entries"

    # Identity / metadata
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )

    # User-provided content (required)
    mood: Mapped[str] = mapped_column(String(50), nullable=False)
    journal_text: Mapped[str] = mapped_column(Text, nullable=False)

    # AI-generated reflection sections (optional)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    emotions: Mapped[str | None] = mapped_column(Text, nullable=True)
    reflection_questions: Mapped[str | None] = mapped_column(Text, nullable=True)
    encouragement: Mapped[str | None] = mapped_column(Text, nullable=True)
    small_goal: Mapped[str | None] = mapped_column(Text, nullable=True)
    todays_bloom: Mapped[str | None] = mapped_column(Text, nullable=True)

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<JournalEntry id={self.id} mood={self.mood!r} created_at={self.created_at!r}>"
