"""Database entities. Minimal metadata only — no API keys, no raw media,
no model reasoning. Temporary media lives on disk briefly and is deleted."""
from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from sqlmodel import Field, SQLModel


def _uuid() -> str:
    return str(uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


class FisherProfile(SQLModel, table=True):
    id: str = Field(default_factory=_uuid, primary_key=True)
    display_name: str = ""
    preferred_language: str = "mfe"
    fishing_area: str = ""
    created_at: datetime = Field(default_factory=_now)


class Species(SQLModel, table=True):
    species_id: str = Field(primary_key=True)
    scientific: str
    english: str
    morisyen: str = ""
    morisyen_status: str = "provisional"
    habitat: str = ""
    keywords: str = ""  # comma-separated
    characteristics: str = ""  # pipe-separated


class SpeciesRule(SQLModel, table=True):
    rule_id: str = Field(primary_key=True)
    species_id: str = Field(index=True)
    rule_type: str  # seasonal_closure | minimum_size | historical_note
    closed_from: str | None = None  # MM-DD
    closed_to: str | None = None
    minimum_length_cm: float | None = None
    source_id: str | None = None
    source_title: str | None = None
    source_url: str | None = None
    effective_date: str | None = None
    verification_date: str | None = None
    verification_status: str = "unavailable"  # provisional | verified | unavailable | historical_note
    note: str = ""


class CatchAnalysis(SQLModel, table=True):
    analysis_id: str = Field(default_factory=_uuid, primary_key=True)
    created_at: datetime = Field(default_factory=_now)
    intent: str = "identify_catch"
    language: str = "en"
    image_quality_status: str = "acceptable"
    blur_score: float = 0.0
    brightness: float = 0.0
    suggested_species_id: str | None = None
    confidence_label: str = "low"
    estimated_size_unverified_cm: float | None = None
    provider_mode: str = "mock"
    provider_model: str = ""
    real_inference: bool = False
    latency_ms: int = 0
    confirmed: bool = False
    image_sha256: str | None = None  # dedupe only; the image itself is deleted


class CatchRecord(SQLModel, table=True):
    id: str = Field(default_factory=_uuid, primary_key=True)
    analysis_id: str | None = Field(default=None, index=True)
    species_id: str
    measured_length_cm: float | None = None
    count: int = 1
    capture_date: str = ""  # YYYY-MM-DD
    fishing_area: str = ""
    latitude_rounded: float | None = None  # 2 dp only — precise coords never stored
    longitude_rounded: float | None = None
    legal_status: str = "unknown"  # allowed | closed_season | below_minimum_size | unknown
    legal_rule_id: str | None = None
    legal_note: str = ""
    created_at: datetime = Field(default_factory=_now)


class LedgerEntry(SQLModel, table=True):
    """Append-only hash chain over confirmed catch records.

    Each entry commits to the record's content AND to the previous entry, so
    editing or deleting any historical record breaks every link after it. This
    proves a record is UNALTERED SINCE IT WAS LOGGED — it says nothing about
    whether the original claim was true. Kept in its own table so the chain is
    independent of CatchRecord and needs no migration of existing rows.
    """
    seq: int | None = Field(default=None, primary_key=True)  # 1-based, monotonic
    record_id: str = Field(index=True)
    payload_sha256: str = ""  # hash of the canonical record content
    prev_hash: str = ""       # previous entry_hash; GENESIS_HASH for the first entry
    entry_hash: str = ""      # sha256 over seq|record_id|payload_sha256|prev_hash
    created_at: datetime = Field(default_factory=_now)


class MarineForecastCache(SQLModel, table=True):
    id: str = Field(default_factory=_uuid, primary_key=True)
    location_key: str = Field(index=True)  # rounded lat,lon
    fetched_at: datetime = Field(default_factory=_now)
    payload_json: str = "{}"
    source: str = "open-meteo"


class Declaration(SQLModel, table=True):
    id: str = Field(default_factory=_uuid, primary_key=True)
    created_at: datetime = Field(default_factory=_now)
    fisher_name: str = ""
    fishing_area: str = ""
    period_start: str = ""
    period_end: str = ""
    catches_json: str = "[]"
    status: str = "draft"  # draft | mock_submitted
    mock_receipt_id: str | None = None


class SyncQueueItem(SQLModel, table=True):
    id: str = Field(default_factory=_uuid, primary_key=True)
    created_at: datetime = Field(default_factory=_now)
    kind: str = "catch_record"
    payload_json: str = "{}"
    status: str = "queued"  # queued | processed | failed


class ToolTrace(SQLModel, table=True):
    id: str = Field(default_factory=_uuid, primary_key=True)
    analysis_id: str | None = Field(default=None, index=True)
    created_at: datetime = Field(default_factory=_now)
    function_name: str = ""
    argument_names: str = ""  # names only — values may contain user data
    result_status: str = ""
    duration_ms: int = 0
    final_action: str = ""


class DemoSetting(SQLModel, table=True):
    key: str = Field(primary_key=True)
    value: str = ""
    updated_at: datetime = Field(default_factory=_now)
