from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import get_settings


class Base(DeclarativeBase):
    """All database models inherit from this class."""
    pass


settings = get_settings()

# SQLite needs check_same_thread=False because FastAPI uses multiple threads
connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}

engine = create_engine(
    settings.database_url,
    connect_args=connect_args,
    echo=settings.is_development,  # logs SQL queries in dev mode, useful for learning
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
)


def get_db() -> Generator[Session, None, None]:
    """
    Dependency injected into every route that needs database access.
    Opens a session, yields it, then closes it — even if an error occurs.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
