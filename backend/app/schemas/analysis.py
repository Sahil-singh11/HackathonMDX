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


# ---------------------------------------------------------------- manual AI test console
#
# A deliberately NARROW projection of ProviderResult for the Technical Proof console.
# It exists so the console can show schema/tool/mock status without widening
# AnalyseCatchResponse, whose contract must not carry engineering telemetry.
#
# Nothing here can hold a secret, a prompt, model prose beyond the final user-facing
# reply, chain of thought, or an argument VALUE (hence argument_names, not arguments).

class ConsoleRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=500,
                        description="Free-text prompt in Morisyen or English. No image.")
    language: Literal["en", "mfe"] = "mfe"


class ConsoleError(BaseModel):
    kind: Literal["transient", "behavioural"]
    message: str


class ConsoleResponse(BaseModel):
    final_response: str = ""
    reply_morisyen: str = ""
    intent: str = ""
    provider: str = ""
    model: str = ""
    real_inference: bool = False
    latency_ms: int = 0
    selected_function: str | None = None
    functions_called: list[str] = Field(default_factory=list)
    argument_names: list[str] = Field(default_factory=list)
    tool_round_trip_completed: bool = False
    schema_valid: bool = False
    safety_flags: dict[str, bool] = Field(default_factory=dict)
    mock_used: bool = False
    mock_label: str = ""
    disclosures: list[str] = Field(default_factory=list)
    function_trace: list[FunctionTraceEntry] = Field(default_factory=list)
    controlled_error: ConsoleError | None = None
