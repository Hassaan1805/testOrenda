from __future__ import annotations

import os
from collections.abc import Iterator
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

import crud
from db import SessionLocal, get_db, init_db
from gemini import GeminiError, stream_reflection_text
from schemas import JournalEntryOut, ReflectRequest

app = FastAPI(title="Orenda")


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
def health() -> dict[str, bool]:
    return {"ok": True}


_REFLECTION_MARKERS = [
    "SUMMARY:",
    "EMOTIONS:",
    "REFLECTION QUESTIONS:",
    "ENCOURAGEMENT:",
    "SMALL GOAL:",
    "TODAY'S BLOOM:",
]


def _parse_reflection_sections(text: str) -> dict[str, str]:
    """Split the model's labeled plain-text output into its section values.

    Mirrors the marker-based parser used by the frontend so persisted columns
    match what the user sees.
    """
    sections: dict[str, str] = {}
    for i, marker in enumerate(_REFLECTION_MARKERS):
        idx = text.find(marker)
        if idx == -1:
            continue
        start = idx + len(marker)
        end = len(text)
        for nxt in _REFLECTION_MARKERS[i + 1 :]:
            nidx = text.find(nxt, start)
            if nidx != -1:
                end = min(end, nidx)
        value = text[start:end].strip()
        if value:
            sections[marker] = value
    return sections


@app.post("/api/reflect/stream")
def reflect_stream(req: ReflectRequest) -> StreamingResponse:
    """Stream a plain-text reflection as SSE, then persist the journal entry.

    Yields ``data: <chunk>`` events (newlines collapsed so each SSE frame stays
    single-line), followed by a ``data: [DONE]`` sentinel. Falls back to the
    built-in mock stream when no ``GEMINI_API_KEY`` is configured.
    """

    # Prime the stream so an auth/config failure surfaces as a normal HTTP error
    # (before the streaming response starts), letting the frontend fall back to
    # its placeholder reflection instead of rendering a broken stream.
    stream = stream_reflection_text(req.mood, req.journal_text)
    try:
        first_chunk = next(stream, None)
    except GeminiError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    def _sse(chunk: str) -> str:
        return f"data: {chunk.replace(chr(13), '').replace(chr(10), ' ')}\n\n"

    def event_stream() -> Iterator[str]:
        chunks: list[str] = []
        if first_chunk:
            chunks.append(first_chunk)
            yield _sse(first_chunk)
        try:
            for chunk in stream:
                if not chunk:
                    continue
                chunks.append(chunk)
                yield _sse(chunk)
        except GeminiError as exc:
            yield f"data: [ERROR] {exc}\n\n"
            return

        full_text = "".join(chunks)
        sections = _parse_reflection_sections(full_text)

        db = SessionLocal()
        try:
            crud.create_entry(
                db,
                mood=req.mood,
                journal_text=req.journal_text,
                summary=sections.get("SUMMARY:"),
                emotions=sections.get("EMOTIONS:"),
                reflection_questions=sections.get("REFLECTION QUESTIONS:"),
                encouragement=sections.get("ENCOURAGEMENT:"),
                small_goal=sections.get("SMALL GOAL:"),
                todays_bloom=sections.get("TODAY'S BLOOM:"),
            )
        except Exception:
            # Persistence must not break the streaming UX.
            db.rollback()
        finally:
            db.close()

        yield "data: [DONE]\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@app.get("/history", response_model=list[JournalEntryOut])
def get_history(db: Session = Depends(get_db)) -> list[JournalEntryOut]:
    """Return all journal entries, newest first."""
    return crud.get_all_entries(db)


@app.get("/entry/{entry_id}", response_model=JournalEntryOut)
def get_entry(entry_id: int, db: Session = Depends(get_db)) -> JournalEntryOut:
    """Return a single journal entry by id (404 if it does not exist)."""
    entry = crud.get_entry(db, entry_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="Journal entry not found")
    return entry


@app.delete("/entry/{entry_id}")
def delete_entry(entry_id: int, db: Session = Depends(get_db)) -> dict[str, bool]:
    """Delete a journal entry by id (404 if it does not exist)."""
    deleted = crud.delete_entry(db, entry_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Journal entry not found")
    return {"ok": True}


# Serve frontend when a sibling or bundled directory exists (local dev / single-container deploy).
_frontend_candidates = [
    Path(__file__).resolve().parent.parent / "frontend",
    Path(__file__).resolve().parent / "frontend",
]
_frontend_dir = next((p for p in _frontend_candidates if p.is_dir()), None)
if _frontend_dir is not None:
    app.mount("/", StaticFiles(directory=str(_frontend_dir), html=True), name="frontend")
