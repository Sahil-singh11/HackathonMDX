from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=REPO_ROOT / ".env", env_file_encoding="utf-8", extra="ignore")

    gemini_api_key: str = ""
    gemma_model: str = "gemma-4-26b-a4b-it"
    gemma_provider: str = "google"
    gemma_timeout_seconds: int = 60
    provider_mode: str = "mock"  # hosted | local | mock; hosted requires a key

    database_url: str = f"sqlite:///{REPO_ROOT / 'storage' / 'lamer_konekte.sqlite3'}"
    upload_max_bytes: int = 8 * 1024 * 1024
    media_retention: str = "delete_after_analysis"
    log_level: str = "INFO"

    marine_api_base: str = "https://marine-api.open-meteo.com/v1/marine"
    marine_cache_minutes: int = 30
    demo_mode: bool = False

    data_dir: Path = REPO_ROOT / "data"
    storage_dir: Path = REPO_ROOT / "storage"

    @property
    def hosted_available(self) -> bool:
        return bool(self.gemini_api_key)


@lru_cache
def get_settings() -> Settings:
    s = Settings()
    s.storage_dir.mkdir(parents=True, exist_ok=True)
    return s
