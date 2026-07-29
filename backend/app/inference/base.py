"""Provider Protocol — the contract every inference implementation must satisfy.

Interface frozen at Task 1a (sync point S1). Workstream 3's agent work codes
against this Protocol with mocks; Workstream 1 fills in real providers behind
it. Changing a signature after S1 requires a decision-log entry.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from app.providers.base import ProviderResult
from app.schemas.analysis import FunctionTraceEntry
from app.tools.registry import ToolContext


@dataclass
class ProviderHealth:
    """Result of a health check. `available` means a request could be served by
    THIS provider right now; `simulated` marks providers whose output is not
    real model inference and must always be disclosed as such."""

    name: str
    available: bool
    real_inference: bool
    simulated: bool
    detail: str = ""


@runtime_checkable
class InferenceProvider(Protocol):
    """One inference backend (hosted Gemma, local Gemma, deterministic mock).

    Implementations raise on failure — selection, fallback and fallback
    *disclosure* are the registry's job, never silently handled inside a
    provider. Every implementation must pass the shared contract test suite
    (`tests/test_provider_contract.py`).
    """

    name: str

    def analyse_catch_image(self, image_jpeg: bytes | None, note: str | None, language: str,
                            candidates: list[dict], ctx: ToolContext) -> ProviderResult:
        """Full catch analysis. Emits a ProviderResult that maps 1:1 onto the
        FROZEN AnalyseCatchResponse schema — no provider may extend it."""
        ...

    def chat(self, prompt: str, language: str = "en") -> str:
        """Plain-text exchange (offline-assistant workstream). No tools."""
        ...

    def call_tools(self, name: str, args: dict, ctx: ToolContext) -> tuple[dict, FunctionTraceEntry]:
        """Execute ONE allow-listed tool through the central registry. Providers
        never dispatch tools themselves; this always routes through
        `app.tools.registry.execute` (validation, redaction, tracing)."""
        ...

    def health_check(self) -> ProviderHealth:
        """Cheap, network-free readiness signal used by `auto` selection."""
        ...
