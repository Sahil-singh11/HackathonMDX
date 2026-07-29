"""Provider readiness/capability surface.

Every provider declares what it can actually do, whether its output is real
inference or simulated, and how ready it is right now. Mock mode stays available
as a fallback but is always labelled `simulated=True`, `real_inference=False`.
"""
from __future__ import annotations

from app.core.config import get_settings
from app.core.limitations import MOCK_DISCLOSURE
from app.schemas.gemma_gate import ProviderCapabilities

# Updated by the hosted provider after each real call. Never contains request content.
_last_hosted_latency_ms: int | None = None


def record_hosted_latency(latency_ms: int) -> None:
    global _last_hosted_latency_ms
    _last_hosted_latency_ms = latency_ms


def hosted_capabilities() -> ProviderCapabilities:
    s = get_settings()
    configured = s.hosted_available
    return ProviderCapabilities(
        provider_name="google-genai",
        model_name=s.gemma_model,
        real_inference=configured,
        simulated=False,
        supports_text=True,
        supports_image=True,
        supports_structured_output=True,
        supports_function_calling=True,
        timeout_seconds=s.gemma_timeout_seconds,
        last_latency_ms=_last_hosted_latency_ms,
        readiness="ready" if configured else "not_configured",
        disclosure=None if configured else "GEMINI_API_KEY is not configured; hosted calls fall back to the mock.",
    )


def local_capabilities() -> ProviderCapabilities:
    from app.providers.local import LOCAL_MODEL_LOADED

    return ProviderCapabilities(
        provider_name="local-gemma",
        model_name=get_settings().gemma_model if LOCAL_MODEL_LOADED else "none",
        real_inference=LOCAL_MODEL_LOADED,
        simulated=False,
        supports_text=LOCAL_MODEL_LOADED,
        supports_image=LOCAL_MODEL_LOADED,
        supports_structured_output=LOCAL_MODEL_LOADED,
        supports_function_calling=False,
        timeout_seconds=get_settings().gemma_timeout_seconds,
        readiness="ready" if LOCAL_MODEL_LOADED else "unavailable",
        disclosure=None if LOCAL_MODEL_LOADED else "No local Gemma model is loaded; edge mode is not reported.",
    )


def mock_capabilities() -> ProviderCapabilities:
    return ProviderCapabilities(
        provider_name="deterministic-mock",
        model_name="none",
        real_inference=False,
        simulated=True,
        supports_text=True,
        supports_image=False,  # it hashes the image; it does not see it
        supports_structured_output=True,
        supports_function_calling=True,  # via the same allow-listed registry
        timeout_seconds=0,
        readiness="simulated",
        disclosure=MOCK_DISCLOSURE,
    )


def all_capabilities() -> dict[str, ProviderCapabilities]:
    return {
        "hosted": hosted_capabilities(),
        "local": local_capabilities(),
        "mock": mock_capabilities(),
    }
