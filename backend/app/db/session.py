from collections.abc import Iterator

from sqlmodel import Session, SQLModel, create_engine

from app.core.config import get_settings

_engine = None


def get_engine():
    global _engine
    if _engine is None:
        settings = get_settings()
        _engine = create_engine(settings.database_url, connect_args={"check_same_thread": False})
    return _engine


def init_db() -> None:
    from app.models import entities  # noqa: F401 - register tables

    engine = get_engine()
    SQLModel.metadata.create_all(engine)
    ensure_catchrecord_analysis_provider(engine)


def ensure_catchrecord_analysis_provider(engine) -> None:
    """Idempotent additive migration: `catchrecord.analysis_provider`.

    `create_all` creates missing TABLES but never alters existing ones, so a
    database written before Task 1a lacks the column. The table schema is
    inspected first and the ALTER runs only when the column is absent — safe to
    call on every startup, on a fresh clone, and repeatedly.
    """
    from sqlalchemy import text

    with engine.connect() as conn:
        cols = {row[1] for row in conn.exec_driver_sql("PRAGMA table_info(catchrecord)")}
        if not cols:  # table does not exist yet (create_all handles fresh DBs)
            return
        if "analysis_provider" not in cols:
            conn.execute(text("ALTER TABLE catchrecord ADD COLUMN analysis_provider VARCHAR"))
            conn.commit()


def get_session() -> Iterator[Session]:
    with Session(get_engine()) as session:
        yield session
