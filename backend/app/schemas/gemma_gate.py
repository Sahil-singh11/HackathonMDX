"""Step-1 gate schemas: the structured shape the live Gemma gates validate.

Kept separate from the FROZEN app contract in `app.schemas.analysis` so gate work
never rewrites the shared API. `SpeciesSuggestion` is reused from that contract so
the two cannot drift.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.schemas.analysis import Confidence, Intent, NextStep, SpeciesSuggestion


class GemmaStructuredAnalysis(BaseModel):
    """The Step-1 expected output schema.

    `species_confirmation_required` and `measured_size_required` are pinned to True:
    the model cannot lower them, because a fisher must always confirm the species and
    an image-derived size is never a measurement.
    """

    intent: Intent = "identify_catch"
    species_suggestion: SpeciesSuggestion = Field(default_factory=SpeciesSuggestion)
    visible_characteristics: list[str] = Field(default_factory=list)
    confidence_label: Confidence = "low"
    species_confirmation_required: Literal[True] = True
    estimated_size_unverified_cm: float | None = None
    measured_size_required: Literal[True] = True
    reply: str = ""
    reply_morisyen: str = ""
    recommended_next_step: NextStep = "confirm_species"
    requested_function: str | None = None
    limitations: list[str] = Field(default_factory=list)

    @field_validator("requested_function")
    @classmethod
    def _allow_listed(cls, value: str | None) -> str | None:
        if value is None:
            return None
        from app.tools.registry import REGISTRY

        if value not in REGISTRY:
            raise ValueError(f"requested_function is not allow-listed: {value!r}")
        return value


def coerce_to_schema(parsed: dict | None, allowed_ids: set[str]) -> GemmaStructuredAnalysis | None:
    """Apply the server-side invariants to raw model output, then validate.

    This is the single source of truth used by both the live gate runner and the
    hosted integration tests, so they cannot drift. The model may not lower
    `species_confirmation_required`/`measured_size_required`, may not name a
    species outside the supplied shortlist, and may not name a function outside
    the allow-list. Out-of-enum values fall back to the safest option rather than
    raising, which is what keeps a bad generation from becoming a 500.

    Returns None when the input is not a usable object — the caller then emits the
    safe uncertain response.
    """
    from app.tools.registry import REGISTRY

    if not isinstance(parsed, dict):
        return None
    data = dict(parsed)
    data["species_confirmation_required"] = True
    data["measured_size_required"] = True

    sug = data.get("species_suggestion")
    if not isinstance(sug, dict):
        sug = {}
    if sug.get("species_id") not in allowed_ids:
        sug = {"species_id": None, "morisyen": sug.get("morisyen"),
               "english": sug.get("english"), "scientific": sug.get("scientific")}
    data["species_suggestion"] = {k: (str(v) if v is not None else None) for k, v in sug.items()
                                  if k in ("species_id", "morisyen", "english", "scientific")}

    if data.get("requested_function") not in REGISTRY:
        data["requested_function"] = None
    if data.get("intent") not in ("identify_catch", "weather_query", "log_catch", "make_declaration", "other"):
        data["intent"] = "other"
    if data.get("confidence_label") not in ("low", "medium", "high"):
        data["confidence_label"] = "low"
    if data.get("recommended_next_step") not in ("confirm_species", "retake_photo", "enter_measurement", "none"):
        data["recommended_next_step"] = "confirm_species"

    vc = data.get("visible_characteristics")
    data["visible_characteristics"] = [str(x) for x in vc][:8] if isinstance(vc, list) else []
    lim = data.get("limitations")
    data["limitations"] = [str(x) for x in lim][:8] if isinstance(lim, list) else []

    try:
        est = data.get("estimated_size_unverified_cm")
        data["estimated_size_unverified_cm"] = float(est) if est is not None else None
    except (TypeError, ValueError):
        data["estimated_size_unverified_cm"] = None
    data["reply"] = str(data.get("reply") or "")[:1200]
    data["reply_morisyen"] = str(data.get("reply_morisyen") or "")[:1200]

    known = set(GemmaStructuredAnalysis.model_fields)
    data = {k: v for k, v in data.items() if k in known}
    try:
        return GemmaStructuredAnalysis(**data)
    except Exception:  # noqa: BLE001 — a validation failure is a result, not a crash
        return None


class ProviderCapabilities(BaseModel):
    """Readiness surface every provider must expose (real or simulated)."""

    provider_name: str
    model_name: str
    real_inference: bool
    simulated: bool = False
    supports_text: bool = False
    supports_image: bool = False
    supports_structured_output: bool = False
    supports_function_calling: bool = False
    timeout_seconds: int = 0
    last_latency_ms: int | None = None
    readiness: Literal["ready", "not_configured", "unavailable", "simulated"] = "unavailable"
    disclosure: str | None = None
