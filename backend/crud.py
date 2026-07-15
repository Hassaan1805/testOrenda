"""Reusable CRUD helpers for :class:`models.JournalEntry`.

These functions operate purely through the SQLAlchemy ORM (no raw SQL) and take
an explicit :class:`~sqlalchemy.orm.Session`, so FastAPI endpoints can obtain a
session via :func:`db.get_db` and call these directly.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from models import JournalEntry


def create_entry(
    db: Session,
    *,
    mood: str,
    journal_text: str,
    summary: str | None = None,
    emotions: str | None = None,
    reflection_questions: str | None = None,
    encouragement: str | None = None,
    small_goal: str | None = None,
    todays_bloom: str | None = None,
) -> JournalEntry:
    """Create and persist a new journal entry, returning the saved instance."""
    entry = JournalEntry(
        mood=mood,
        journal_text=journal_text,
        summary=summary,
        emotions=emotions,
        reflection_questions=reflection_questions,
        encouragement=encouragement,
        small_goal=small_goal,
        todays_bloom=todays_bloom,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


def get_entry(db: Session, entry_id: int) -> JournalEntry | None:
    """Return the entry with ``entry_id``, or ``None`` if it does not exist."""
    return db.get(JournalEntry, entry_id)


def get_all_entries(db: Session) -> list[JournalEntry]:
    """Return all entries sorted by newest first (most recent ``created_at``)."""
    stmt = select(JournalEntry).order_by(
        JournalEntry.created_at.desc(), JournalEntry.id.desc()
    )
    return list(db.scalars(stmt).all())


def update_entry(
    db: Session,
    entry_id: int,
    *,
    mood: str | None = None,
    journal_text: str | None = None,
    summary: str | None = None,
    emotions: str | None = None,
    reflection_questions: str | None = None,
    encouragement: str | None = None,
    small_goal: str | None = None,
    todays_bloom: str | None = None,
) -> JournalEntry | None:
    """Update the given fields on an entry.

    Only arguments explicitly passed (i.e. not ``None``) are applied, so callers
    can perform partial updates. Returns the updated entry, or ``None`` if no
    entry with ``entry_id`` exists.
    """
    entry = db.get(JournalEntry, entry_id)
    if entry is None:
        return None

    if mood is not None:
        entry.mood = mood
    if journal_text is not None:
        entry.journal_text = journal_text
    if summary is not None:
        entry.summary = summary
    if emotions is not None:
        entry.emotions = emotions
    if reflection_questions is not None:
        entry.reflection_questions = reflection_questions
    if encouragement is not None:
        entry.encouragement = encouragement
    if small_goal is not None:
        entry.small_goal = small_goal
    if todays_bloom is not None:
        entry.todays_bloom = todays_bloom

    db.commit()
    db.refresh(entry)
    return entry


def delete_entry(db: Session, entry_id: int) -> bool:
    """Delete the entry with ``entry_id``.

    Returns ``True`` if an entry was deleted, ``False`` if none was found.
    """
    entry = db.get(JournalEntry, entry_id)
    if entry is None:
        return False

    db.delete(entry)
    db.commit()
    return True
