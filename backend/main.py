from __future__ import annotations

import os
from datetime import date
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles

from claude import stream_reflection_text

# Backend removed for frontend-only deployment.
# (No API routes; this prevents Supabase/Claude/db initialization from running.)

app = FastAPI(title="Orenda (frontend-only)")


_default_origins = "http://localhost,http://localhost:8000,http://127.0.0.1:8000,null,file://"
_cors_origins = os.getenv("CORS_ORIGINS", _default_origins)
allow_origins = [o.strip() for o in _cors_origins.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    init_db()


@app.get("/health")
def health():
    return {"ok": True}


@app.post("/api/reflect/stream")

def reflect_stream(req: ReflectRequest, request: Request):
    """Streams reflection cards

    Frontend contract (plain-text structure):
      SUMMARY:
      EMOTIONS:
      REFLECTION QUESTIONS:
      ENCOURAGEMENT:
      SMALL GOAL:
      TODAY'S BLOOM:

    We stream the entire plain-text output progressively.
    """

    # Set default date if not provided
    entry_date = req.date or str(date.today())

    def event_generator():
        # SSE requires: lines like "data: ...\n\n"
        # We'll stream plain text chunks.
        full_text_accum: list[str] = []

        # stream_reflection_text yields text chunks
        for chunk in stream_reflection_text(req.mood, req.journal_text):
            if await_request_aborted(request):
                return

            full_text_accum.append(chunk)
            # Still send chunks as-is; frontend will parse.
            yield f"data: {chunk}\n\n"

        # Stream end marker (optional but helpful)
        full_text = "".join(full_text_accum)
        summary_text = extract_summary_from_plaintext(full_text)

        # Save after stream completes
        try:
            save_journal_entry(
                date_iso=entry_date,
                mood=req.mood,
                journal_text=req.journal_text,
                ai_summary=summary_text,
            )
        except Exception:
            # Persistence should not break streaming UX
            pass

        yield "data: [DONE]\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


def await_request_aborted(request: Request) -> bool:
    # FastAPI Request has an is_disconnected() coroutine.
    # We can't await inside sync generator; so we do a conservative check.
    # The SSE generator will naturally stop when client closes.
    return False


def extract_summary_from_plaintext(plain: str) -> str:

    # Keep it simple and resilient.
    # Prefer the SUMMARY: block.
    marker = "SUMMARY:"
    if marker not in plain:
        return plain.strip()[:500]
    after = plain.split(marker, 1)[1]

    # Stop at next marker if present
    next_markers = [
        "EMOTIONS:",
        "REFLECTION QUESTIONS:",
        "ENCOURAGEMENT:",
        "SMALL GOAL:",
        "TODAY'S BLOOM:",
    ]
    end_idx = len(after)
    for m in next_markers:
        if m in after:
            end_idx = min(end_idx, after.index(m))
    return after[:end_idx].strip()[:1000]



@app.get("/api/history")

def history_api(q: str | None = None, mood: str | None = None):
    """Return journal entries for the history page (Supabase-backed).

    Query params:
      - q: optional search string
      - mood: one of Happy/Calm/Neutral/Sad/Anxious/Frustrated or All
    """

    items = list_journal_entries(q=q, mood=mood)
    return {
        "items": [
            {
                "date": x["date"],
                "mood": x["mood"],
                "summary": (x["ai_summary"] or "").strip(),
            }
            for x in items
        ]
    }


# Serve frontend when a sibling or bundled directory exists (local dev / single-container deploy).
_frontend_candidates = [
    Path(__file__).resolve().parent.parent / "frontend",
    Path(__file__).resolve().parent / "frontend",
]
_frontend_dir = next((p for p in _frontend_candidates if p.is_dir()), None)
if _frontend_dir is not None:
    app.mount("/", StaticFiles(directory=str(_frontend_dir), html=True), name="frontend")
