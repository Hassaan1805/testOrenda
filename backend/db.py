from __future__ import annotations

import os
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------
# SQLite database file. Defaults to ``orenda.db`` in the working directory but
# can be overridden with ORENDA_DB_PATH (e.g. a mounted volume in Docker).
_DB_PATH = os.getenv("ORENDA_DB_PATH", "orenda.db")
DATABASE_URL = f"sqlite:///{_DB_PATH}"

# ``check_same_thread=False`` lets the SQLite connection be shared across
# threads, which is required for FastAPI's threaded request handling.
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    future=True,
)

# ---------------------------------------------------------------------------
# Session factory
# ---------------------------------------------------------------------------
SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
    future=True,
)


# ---------------------------------------------------------------------------
# Declarative base
# ---------------------------------------------------------------------------
class Base(DeclarativeBase):
    """Declarative base class shared by all ORM models."""


def init_db() -> None:
    """Create all tables defined on ``Base`` if they do not already exist.

    Importing :mod:`models` here (rather than at module top level) avoids a
    circular import, since ``models`` imports :data:`Base` from this module.
    """
    import models  # noqa: F401  (ensures models are registered on Base.metadata)

    Base.metadata.create_all(bind=engine)


def get_db() -> Generator[Session, None, None]:
    """Yield a database session and guarantee it is closed afterwards.

    Suitable for use as a FastAPI dependency::

        @app.get("/entries")
        def list_entries(db: Session = Depends(get_db)):
            return get_all_entries(db)
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
