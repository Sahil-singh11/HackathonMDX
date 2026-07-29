from __future__ import annotations

from dataclasses import dataclass, field

from app.schemas.analysis import FunctionTraceEntry


@dataclass
class ProviderResult:
    intent: str = "identify_catch"
    species_id: str | None = None
    visible_characteristics: list[str] = field(default_factory=list)
    confidence_label: str = "low"
    estimated_size_unverified_cm: float | None = None
    reply: str = ""
    reply_morisyen: str = ""
    recommended_next_step: str = "confirm_species"
    function_trace: list[FunctionTraceEntry] = field(default_factory=list)
    provider_name: str = ""
    model: str = ""
    mode: str = "mock"
    real_inference: bool = False
    latency_ms: int = 0
    disclosures: list[str] = field(default_factory=list)
