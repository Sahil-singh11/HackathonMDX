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

    # Extra browser origins for the shared-backend team mode. Loopback is always
    # allowed, so this is only needed for a deployed front-end origin.
    cors_extra_origins: str = ""

    marine_api_base: str = "https://marine-api.open-meteo.com/v1/marine"
    marine_cache_minutes: int = 30
    marine_prewarm_on_startup: bool = True  # off in tests (conftest.py) — no network in the suite
    # Warms app.pillars.narrative_cache for energy/tourism/transport at startup,
    # same fire-and-forget contract as marine_prewarm_on_startup (never blocks
    # /health). Off in tests (conftest.py) — the suite must make zero external
    # network/model calls.
    narrative_prewarm_on_startup: bool = True
    # DEMO_MODE=true: pillar narrative calls (energy/tourism/transport) serve
    # ONLY from app.pillars.narrative_cache and never call a model — see
    # narrative_cache.demo_mode_active(). For when venue wifi cannot be trusted:
    # pre-warm the cache beforehand (prewarm_pillar_narratives), then flip this
    # on so nothing in the rest of the demo depends on connectivity (Task 3).
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
    # Route-local model timeout for the narrative step (decision log 18).
    #
    # Set to 90 s, TESTED, and reverted to 60 s on the evidence. The hypothesis
    # was that the narrative needed longer than the deployment-wide ceiling; a
    # live call with the shortened ~4-sentence brief timed out at 90 s too
    # (92.3 s wall). A longer ceiling bought nothing and cost every caller an
    # extra 30 s of waiting before the same deterministic fallback, so it is
    # net-harmful and the value goes back down.
    #
    # The knob stays because the mechanism is right — the analyse path already
    # carries per-route timeouts (45 s tools / 60 s text / 75 s image) — and
    # whoever diagnoses this next should change one number, not re-plumb it.
    # Do not raise it again without evidence that latency is the actual cause;
    # four live calls have produced 503, refusal, timeout@60, timeout@90.
    transport_narrative_timeout_seconds: int = 60
    # Live aisstream.io collector — DORMANT FORWARD DECLARATIONS.
    #
    # The collector is deliberately UNIMPLEMENTED, not merely disabled. A
    # coverage probe on 30 Jul 2026 (backend/scripts/ais_coverage_probe.py)
    # found the global aisstream feed flowing but ZERO messages for the
    # Mauritius region across a 120 s Port Louis box and a 120 s Mascarene
    # box — a regional receiver gap, not a key or service fault. There is
    # nothing for a collector to collect, and a half-built long-lived
    # WebSocket is a startup hazard (the 4acff21 trap in a worse form) bought
    # for no data.
    #
    # These two settings exist so activation is a small, reviewable change the
    # day coverage appears: set the key, flip the flag, re-run the probe.
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

    @property
    def cors_extra_origins_list(self) -> list[str]:
        """Additional browser origins allowed to call this deployment.

        Loopback origins are always allowed (see main.py), so this is only for deployed
        front-ends — e.g. a preview URL — added without editing code. Comma-separated.
        """
        return [o.strip() for o in self.cors_extra_origins.split(",") if o.strip()]


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
