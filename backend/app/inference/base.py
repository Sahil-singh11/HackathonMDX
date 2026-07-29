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

    def chat(self, prompt: str, language: str = "en",
             system_instruction: str | None = None) -> str:
        """Plain-text exchange (offline-assistant workstream). No tools.

        `system_instruction` is OPTIONAL and defaults to None, which means "use
        this provider's default instruction" — for the hosted provider that is
        the fisheries `SYSTEM_INSTRUCTION`, unchanged. Passing None must remain
        byte-for-byte identical to the pre-Task-4b behaviour; a contract test
        pins that.

        It exists because the default instruction is fisheries-scoped and orders
        structured output, so a non-fisheries caller gets a refusal in a JSON
        envelope rather than prose. Measured 30 Jul 2026: asked for a port
        arrivals brief, the live hosted model replied "I am an analysis engine
        for fishers, not a port officer." Every non-fisheries pillar hits this.
        See DECISION_LOG entry 17 — this signature was frozen at S1 and the
        change is recorded there.

        Callers passing an instruction own its safety rules. The honesty
        obligations do not transfer: a pillar that swaps the instruction is
        still responsible for validating what comes back (the transport pillar
        keeps a grounding guard that rejects refusals, structured envelopes and
        invented identifiers).
        """
        ...

    def call_tools(self, name: str, args: dict, ctx: ToolContext) -> tuple[dict, FunctionTraceEntry]:
        """Execute ONE allow-listed tool through the central registry. Providers
        never dispatch tools themselves; this always routes through
        `app.tools.registry.execute` (validation, redaction, tracing)."""
        ...

    def health_check(self) -> ProviderHealth:
        """Cheap, network-free readiness signal used by `auto` selection."""
        ...
