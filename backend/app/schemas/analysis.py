"""FROZEN API contract (see docs/ARCHITECTURE.md). Changes require a decision-log entry."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

Intent = Literal["identify_catch", "weather_query", "log_catch", "make_declaration", "other"]
QualityStatus = Literal["acceptable", "poor", "invalid"]
Confidence = Literal["low", "medium", "high"]
NextStep = Literal["confirm_species", "retake_photo", "enter_measurement", "none"]
ProviderMode = Literal["hosted", "local", "mock"]
LegalStatus = Literal["pending_confirmation", "allowed", "closed_season", "below_minimum_size", "unknown"]


class ImageQuality(BaseModel):
    status: QualityStatus = "invalid"
    blur_score: float = 0.0
    brightness: float = 0.0
    warnings: list[str] = Field(default_factory=list)


class SpeciesSuggestion(BaseModel):
    species_id: str | None = None
    morisyen: str | None = None
    english: str | None = None
    scientific: str | None = None


class LegalCheck(BaseModel):
    status: LegalStatus = "pending_confirmation"
    rule: str | None = None
    source_id: str | None = None
    verification_status: str | None = None
    note: str | None = None


class FunctionTraceEntry(BaseModel):
    function: str
    argument_names: list[str] = Field(default_factory=list)
    result_status: str = "ok"
    duration_ms: int = 0
    final_action: str = ""


class ProviderInfo(BaseModel):
    mode: ProviderMode = "mock"
    provider_name: str = ""
    model: str = ""
    real_inference: bool = False
    latency_ms: int = 0


class AnalyseCatchResponse(BaseModel):
    analysis_id: str
    intent: Intent = "identify_catch"
    image_quality: ImageQuality = Field(default_factory=ImageQuality)
    species_suggestion: SpeciesSuggestion = Field(default_factory=SpeciesSuggestion)
    visible_characteristics: list[str] = Field(default_factory=list)
    confidence_label: Confidence = "low"
    species_confirmation_required: bool = True
    estimated_size_unverified_cm: float | None = None
    measured_size_required: bool = True
    legal_check: LegalCheck = Field(default_factory=LegalCheck)
    reply: str = ""
    reply_morisyen: str = ""
    recommended_next_step: NextStep = "confirm_species"
    function_trace: list[FunctionTraceEntry] = Field(default_factory=list)
    provider: ProviderInfo = Field(default_factory=ProviderInfo)
    limitations: list[str] = Field(default_factory=list)


class ConfirmRequest(BaseModel):
    confirmed_species_id: str
    measured_length_cm: float | None = None
    count: int = 1
    capture_date: str | None = None  # YYYY-MM-DD; defaults to current (demo) date
    latitude: float | None = None
    longitude: float | None = None
    fishing_area: str = ""


class ConfirmResponse(BaseModel):
    catch_record_id: str
    species_id: str
    legal_check: LegalCheck
    measured_length_cm: float | None
    count: int
    capture_date: str
    limitations: list[str] = Field(default_factory=list)
