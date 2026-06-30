import os
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker
from app.models import Base

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./candidatefusion.db")
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def _schema_is_current() -> bool:
    """Return False if the DB uses the old schema (missing full_name column)."""
    try:
        inspector = inspect(engine)
        if not inspector.has_table("candidate"):
            return True  # fresh DB, create_all will handle it
        cols = {c["name"] for c in inspector.get_columns("candidate")}
        return "full_name" in cols and "candidate_id" in cols
    except Exception:
        return False


def init_db() -> None:
    if not _schema_is_current():
        # Old schema detected — drop and recreate (dev only; production would use Alembic)
        Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


init_db()
