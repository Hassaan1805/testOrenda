from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from gemini import generate_reflection, stream_reflection_text
import crud
from db import get_db, init_db
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


@app.get("/api/history", response_model=list[JournalEntryOut])
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


@app.post("/api/reflect/stream")
def reflect_stream(request: ReflectRequest, db: Session = Depends(get_db)):
    """Stream reflection from Gemini based on mood and journal text, and save to database."""
    REFLECTION_MARKERS = [
        'SUMMARY:',
        'EMOTIONS:',
        'REFLECTION QUESTIONS:',
        'ENCOURAGEMENT:',
        'SMALL GOAL:',
        "TODAY'S BLOOM:"
    ]
    
    def generate_and_save():
        """Generator that streams reflection and saves entry to database."""
        full_text = ""
        try:
            for chunk in stream_reflection_text(request.mood, request.journal_text):
                full_text += chunk
                yield chunk
        except Exception as e:
            print(f"Error during reflection streaming: {e}")
            # Still try to save even if streaming fails
            pass
        
        # Parse reflection sections and save to database
        sections = {}
        try:
            for i, marker in enumerate(REFLECTION_MARKERS):
                next_markers = REFLECTION_MARKERS[i + 1:]
                start_idx = full_text.find(marker)
                if start_idx != -1:
                    start_idx += len(marker)
                    end_idx = len(full_text)
                    for next_marker in next_markers:
                        next_idx = full_text.find(next_marker, start_idx)
                        if next_idx != -1:
                            end_idx = min(end_idx, next_idx)
                    sections[marker] = full_text[start_idx:end_idx].strip()
        except Exception as e:
            print(f"Error parsing reflection sections: {e}")
        
        # Save entry to database (even if reflection parsing fails)
        try:
            crud.create_entry(
                db,
                mood=request.mood,
                journal_text=request.journal_text,
                summary=sections.get("SUMMARY:"),
                emotions=sections.get("EMOTIONS:"),
                reflection_questions=sections.get("REFLECTION QUESTIONS:"),
                encouragement=sections.get("ENCOURAGEMENT:"),
                small_goal=sections.get("SMALL GOAL:"),
                todays_bloom=sections.get("TODAY'S BLOOM:")
            )
            print(f"Successfully saved journal entry for mood: {request.mood}")
        except Exception as e:
            print(f"Error saving to database: {e}")
    
    return StreamingResponse(
        generate_and_save(),
        media_type="text/event-stream"
    )


# Serve frontend when a sibling or bundled directory exists (local dev / single-container deploy).
_frontend_candidates = [
    Path(__file__).resolve().parent.parent / "frontend",
    Path(__file__).resolve().parent / "frontend",
]
_frontend_dir = next((p for p in _frontend_candidates if p.is_dir()), None)
if _frontend_dir is not None:
    app.mount("/", StaticFiles(directory=str(_frontend_dir), html=True), name="frontend")
