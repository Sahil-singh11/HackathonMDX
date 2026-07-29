"""Settings must not depend on the current working directory.

Regression: a relative `DATABASE_URL` in .env resolved against the launch
directory, so `uvicorn` started from `backend/` looked for `backend/storage/`
and crashed with "unable to open database file".
"""
from pathlib import Path

from app.core.config import REPO_ROOT, Settings


def test_relative_sqlite_path_is_anchored_to_repo_root():
    s = Settings(database_url="sqlite:///./storage/lamer_konekte.sqlite3")
    expected = (REPO_ROOT / "storage" / "lamer_konekte.sqlite3").resolve()
    assert s.database_url == f"sqlite:///{expected}"


def test_relative_path_without_dot_prefix_also_anchored():
    s = Settings(database_url="sqlite:///storage/other.sqlite3")
    assert s.database_url == f"sqlite:///{(REPO_ROOT / 'storage' / 'other.sqlite3').resolve()}"


def test_absolute_sqlite_path_is_left_alone():
    absolute = "sqlite:////tmp/somewhere/lamer.sqlite3"
    assert Settings(database_url=absolute).database_url == absolute


def test_in_memory_database_is_left_alone():
    assert Settings(database_url="sqlite:///:memory:").database_url == "sqlite:///:memory:"


def test_non_sqlite_url_is_left_alone():
    url = "postgresql://user@host:5432/db"
    assert Settings(database_url=url).database_url == url


def test_default_database_path_is_absolute():
    assert Path(Settings().database_url[len("sqlite:///"):]).is_absolute()
