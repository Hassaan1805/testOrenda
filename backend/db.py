from __future__ import annotations
from supabase import create_client
import os
import re
from typing import Optional, List, Dict, Any

from supabase import Client, create_client

# Supabase integration is optional.
# If env vars are missing (local dev / failing container env), we fall back to a no-op mode
# so the frontend can still load and reflections can still work.

supabase: Client | None = None

_client: Client | None = None



def _get_client() -> Client:
    global _client
    if _client is not None:
        return _client

    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        raise RuntimeError("Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY in environment")

    _client = create_client(url, key)
    return _client


def init_db() -> None:
    """Initialize persistence.

    Supabase is optional. If credentials are missing, we skip initialization
    so the frontend can still load and SSE reflection can still work.
    """
    # If we already built a client, init with it.
    try:
        client = _get_client()
    except RuntimeError:
        return

    # Verify Supabase connectivity (table is created via Supabase SQL editor).
    client.table("journal_entries").select("id").limit(1).execute()



def save_journal_entry(
    *,
    date_iso: str,
    mood: str,
    journal_text: str,
    ai_summary: str,
) -> None:
    """Persist a journal entry.

    If Supabase is not configured, this becomes a no-op (so the frontend can load).
    """
    if supabase is None:
        return

    supabase.table("journal_entries").insert(
        {
            "date": date_iso,
            "mood": mood,
            "journal_text": journal_text,
            "ai_summary": ai_summary,
        }
    ).execute()




def _sanitize_search(q: str) -> str:
    # PostgREST .or_() uses commas as separators — strip characters that break the filter.
    return re.sub(r"[,()]", " ", q).strip()


def list_journal_entries(
    *,
    q: str | None = None,
    mood: str | None = None,
) -> list[dict[str, Any]]:
    """List journal entries.

    If Supabase is not configured, returns an empty list.
    """
    if supabase is None:
        return []

    query = supabase.table("journal_entries").select("*").order("date", desc=True).limit(30)

    if mood and mood != "All":
        query = query.eq("mood", mood)

    if q:
        # PostgREST .or_() uses commas as separators — ensure the query is safe-ish.
        q2 = _sanitize_search(q)
        query = query.or_(
            f"journal_text.ilike.%{q2}%,ai_summary.ilike.%{q2}%,mood.ilike.%{q2}%,date.ilike.%{q2}%"
        )

    res = query.execute()
    return res.data or []

