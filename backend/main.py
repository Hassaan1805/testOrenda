from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

import crud
from db import get_db, init_db
from schemas import JournalEntryOut

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
