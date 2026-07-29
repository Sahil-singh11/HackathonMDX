"""Provider registry: selection, health checks, fallback policy.

Single source of truth for which inference backend serves a request.

Selection is config-driven:

    INFERENCE_PROVIDER = auto | gemma_hosted | gemma_local | mock

`PROVIDER_MODE` (hosted | local | mock) remains a working alias — it is what the
frontend's `provider_mode` form field and existing deployments speak — and maps
onto the same canonical names. When both are set, INFERENCE_PROVIDER wins.

`auto` prefers gemma_local, then gemma_hosted, then the deterministic mock as
the disclosed last resort (per decision D1 there is no Gemini-model path in
this codebase to fall back to). Every skip is recorded as a FallbackEvent so
the caller can disclose it — providers never fail silently.

Task 1a note: the live analyse route still goes through
`app.providers.dispatcher` unchanged (decision D3 — zero behaviour change).
This registry is exercised by the contract test suite now and becomes the
runtime path when `auto` turns real in Task 1c.
"""
from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass

from app.core.config import get_settings
from app.core.limitations import MOCK_DISCLOSURE
from app.inference import gemma_hosted
from app.inference.base import InferenceProvider, ProviderHealth
from app.inference.gemma_local import GemmaLocalProvider
from app.providers import capabilities, mock
from app.providers.base import ProviderResult
from app.schemas.analysis import FunctionTraceEntry
from app.tools import registry as tool_registry
from app.tools.registry import ToolContext

log = logging.getLogger(__name__)

AUTO = "auto"
GEMMA_HOSTED = "gemma_hosted"
GEMMA_LOCAL = "gemma_local"
MOCK = "mock"
CANONICAL = (GEMMA_HOSTED, GEMMA_LOCAL, MOCK)

# PROVIDER_MODE alias -> canonical registry name.
_ALIASES = {
    "hosted": GEMMA_HOSTED,
    "local": GEMMA_LOCAL,
    "mock": MOCK,
    GEMMA_HOSTED: GEMMA_HOSTED,
    GEMMA_LOCAL: GEMMA_LOCAL,
    AUTO: AUTO,
}

AUTO_ORDER = (GEMMA_LOCAL, GEMMA_HOSTED, MOCK)


@dataclass
class FallbackEvent:
    """One provider skipped during selection — raw material for a disclosure."""

    skipped: str
    reason: str


class GemmaHostedProvider:
    """Hosted Gemma 4 (`gemma-4-26b-a4b-it`) behind the Protocol.

    Thin adapter over `app.inference.gemma_hosted` — analysis behaviour is the
    moved module's, unchanged.
    """

    name = GEMMA_HOSTED

    def analyse_catch_image(self, image_jpeg: bytes | None, note: str | None, language: str,
                            candidates: list[dict], ctx: ToolContext) -> ProviderResult:
        return gemma_hosted.analyse(image_jpeg, note, language, candidates, ctx)

    def chat(self, prompt: str, language: str = "en",
             system_instruction: str | None = None,
             timeout_seconds: int | None = None) -> str:
        settings = get_settings()
        if not settings.hosted_available:
            raise gemma_hosted.HostedUnavailable("GEMINI_API_KEY not configured")
        from google import genai
        from google.genai import types

        from app.prompts.system import SYSTEM_INSTRUCTION
        # None keeps the fisheries default — the pre-Task-4b behaviour, pinned
        # by test_hosted_chat_default_instruction_is_unchanged.
        instruction = SYSTEM_INSTRUCTION if system_instruction is None else system_instruction
        # None keeps the deployment-wide ceiling; a route may carry its own.
        seconds = settings.gemma_timeout_seconds if timeout_seconds is None else timeout_seconds
        client = genai.Client(api_key=settings.gemini_api_key)
        response = client.models.generate_content(
            model=settings.gemma_model,
            contents=f"Preferred language: {language}\n\n{prompt}",
            config=types.GenerateContentConfig(
                system_instruction=instruction, temperature=0.2,
                http_options=types.HttpOptions(timeout=seconds * 1000)))
        return (response.text or "").strip()

    def call_tools(self, name: str, args: dict, ctx: ToolContext) -> tuple[dict, FunctionTraceEntry]:
        return tool_registry.execute(name, args, ctx)

    def health_check(self) -> ProviderHealth:
        caps = capabilities.hosted_capabilities()
        return ProviderHealth(name=self.name, available=caps.readiness == "ready",
                              real_inference=True, simulated=False,
                              detail=caps.readiness)


class MockProvider:
    """Deterministic offline mock as a first-class provider (decision D2).

    Always available, fully offline, and every result carries MOCK_DISCLOSURE —
    it can never be mistaken for model inference.
    """

    name = MOCK

    def analyse_catch_image(self, image_jpeg: bytes | None, note: str | None, language: str,
                            candidates: list[dict], ctx: ToolContext) -> ProviderResult:
        image_sha = hashlib.sha256(image_jpeg).hexdigest() if image_jpeg else None
        return mock.analyse(image_sha, note, language, candidates, ctx)

    def chat(self, prompt: str, language: str = "en",
             system_instruction: str | None = None,
             timeout_seconds: int | None = None) -> str:
        # Instruction and timeout are accepted and ignored: the mock does no inference,
        # so honouring it would imply a scoping that never happened. What it
        # must never do is drop the disclosure.
        if language == "mfe":
            return f"(MOCK) {MOCK_DISCLOSURE} Mo kapav ed twa ar lapes, lamer ek deklarasion."
        return f"(MOCK) {MOCK_DISCLOSURE} I can help with catches, sea conditions and declarations."

    def call_tools(self, name: str, args: dict, ctx: ToolContext) -> tuple[dict, FunctionTraceEntry]:
        return tool_registry.execute(name, args, ctx)

    def health_check(self) -> ProviderHealth:
        return ProviderHealth(name=self.name, available=True, real_inference=False,
                              simulated=True, detail="deterministic mock — always available, always disclosed")


_PROVIDERS: dict[str, InferenceProvider] = {
    GEMMA_HOSTED: GemmaHostedProvider(),
    GEMMA_LOCAL: GemmaLocalProvider(),
    MOCK: MockProvider(),
}


def get_provider(name: str) -> InferenceProvider:
    if name not in _PROVIDERS:
        raise KeyError(f"unknown inference provider: {name!r} (known: {sorted(_PROVIDERS)})")
    return _PROVIDERS[name]


def resolve_name(explicit: str | None = None) -> str:
    """Canonical provider name for a request.

    Precedence: explicit request value -> INFERENCE_PROVIDER -> PROVIDER_MODE
    alias. Unknown values raise rather than guess.
    """
    settings = get_settings()
    raw = explicit or settings.inference_provider or settings.provider_mode
    resolved = _ALIASES.get(raw)
    if resolved is None:
        raise KeyError(f"unknown inference provider: {raw!r} (known: {sorted(set(_ALIASES))})")
    return resolved


def select(name: str | None = None) -> tuple[InferenceProvider, list[FallbackEvent]]:
    """Resolve a provider, applying the `auto` policy when asked.

    Returns the chosen provider plus every FallbackEvent the caller must
    disclose. A named (non-auto) provider is returned as-is even when
    unhealthy — per-request failure handling stays with the caller, exactly as
    the dispatcher does today.
    """
    resolved = resolve_name(name)
    if resolved != AUTO:
        return get_provider(resolved), []

    events: list[FallbackEvent] = []
    for candidate in AUTO_ORDER:
        provider = get_provider(candidate)
        health = provider.health_check()
        if health.available:
            return provider, events
        events.append(FallbackEvent(skipped=candidate, reason=health.detail or "unavailable"))
        log.info("auto selection skipped %s: %s", candidate, health.detail)
    # Unreachable in practice — mock is always available — but never silent.
    return get_provider(MOCK), events
