from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=REPO_ROOT / ".env", env_file_encoding="utf-8", extra="ignore")

    gemini_api_key: str = ""
    gemma_model: str = "gemma-4-26b-a4b-it"
    gemma_provider: str = "google"
    gemma_timeout_seconds: int = 60
    provider_mode: str = "mock"  # hosted | local | mock; hosted requires a key
    # Canonical provider selection (auto | gemma_hosted | gemma_local | mock).
    # Empty means "derive from provider_mode", which stays a working alias.
    inference_provider: str = ""

    database_url: str = f"sqlite:///{REPO_ROOT / 'storage' / 'lamer_konekte.sqlite3'}"
    upload_max_bytes: int = 8 * 1024 * 1024
    media_retention: str = "delete_after_analysis"
    log_level: str = "INFO"

    marine_api_base: str = "https://marine-api.open-meteo.com/v1/marine"
    marine_cache_minutes: int = 30
    marine_prewarm_on_startup: bool = True  # off in tests (conftest.py) — no network in the suite
    demo_mode: bool = False

    # Comma-separated pillar ids allowed to serve live pillar routes. A pillar
    # is "live" only when implemented AND listed here, so merging a new pillar
    # module never silently exposes it (Task 4a).
    #
    # Transport ships implemented-but-disabled ON PURPOSE: the default deployment
    # has no AIS feed, and an endpoint that answers 503 with an explanation is
    # more honest than one that answers 200 with fixture data nobody asked for.
    # Enable with PILLARS_ENABLED=fisheries,transport.
    pillars_enabled: str = "fisheries"

    # -- Marine Transport & Trade pillar (Task 4b) --------------------------
    # Rolling AIS window. Both bounds are enforced on every write: a collector
    # left running overnight must not grow the SQLite file without bound.
    transport_ais_retention_minutes: int = 180
    transport_ais_max_rows: int = 5000
    # How far ahead the arrivals brief looks. Deterministic filter, not a model
    # parameter — the model never decides which vessels are in the window.
    transport_arrivals_window_hours: int = 24
    # Live aisstream.io collector. OFF by default and off in tests: it opens a
    # long-lived WebSocket, which is exactly the startup trap 4acff21 fixed for
    # one-shot fetches, in a worse form. Turning it on is an explicit act.
    ais_collector_enabled: bool = False
    aisstream_api_key: str = ""

    data_dir: Path = REPO_ROOT / "data"
    storage_dir: Path = REPO_ROOT / "storage"

    @field_validator("database_url")
    @classmethod
    def _anchor_relative_sqlite_path(cls, value: str) -> str:
        """Resolve relative SQLite paths against the repo root.

        Without this, `sqlite:///./storage/app.db` depends on the working
        directory: uvicorn is launched from `backend/`, so it would look for
        `backend/storage/` and fail with "unable to open database file".
        """
        prefix = "sqlite:///"
        if not value.startswith(prefix):
            return value
        path = value[len(prefix):]
        if not path or path == ":memory:" or path.startswith("/"):
            return value
        return f"{prefix}{(REPO_ROOT / path).resolve()}"

    @property
    def hosted_available(self) -> bool:
        return bool(self.gemini_api_key)


@lru_cache
def get_settings() -> Settings:
    s = Settings()
    s.storage_dir.mkdir(parents=True, exist_ok=True)
    # The database may live outside storage_dir if DATABASE_URL was overridden.
    if s.database_url.startswith("sqlite:///"):
        db_path = Path(s.database_url[len("sqlite:///"):])
        if str(db_path) != ":memory:":
            db_path.parent.mkdir(parents=True, exist_ok=True)
    return s
