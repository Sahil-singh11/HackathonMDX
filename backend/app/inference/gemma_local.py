"""Local (edge) Gemma provider — honest stub until Task 1c.

'local' may only ever be reported after a real model load. No model is bundled
and none is loaded here, so every inference entry point raises
`LocalUnavailable` and the health check reports unavailable. Task 1c replaces
the internals with an OpenAI-compatible client for a locally served Gemma 4
E2B; the honesty contract (never simulate edge inference) stays.
"""
from __future__ import annotations

from app.inference.base import ProviderHealth
from app.providers.base import ProviderResult
from app.providers.local import LOCAL_MODEL_LOADED, LocalUnavailable
from app.schemas.analysis import FunctionTraceEntry
from app.tools import registry as tool_registry
from app.tools.registry import ToolContext

NAME = "gemma_local"


class GemmaLocalProvider:
    name = NAME

    def analyse_catch_image(self, image_jpeg: bytes | None, note: str | None, language: str,
                            candidates: list[dict], ctx: ToolContext) -> ProviderResult:
        raise LocalUnavailable(
            "No local Gemma model is loaded. Edge inference is only reported after a real local model run.")

    def chat(self, prompt: str, language: str = "en") -> str:
        raise LocalUnavailable(
            "No local Gemma model is loaded. Edge inference is only reported after a real local model run.")

    def call_tools(self, name: str, args: dict, ctx: ToolContext) -> tuple[dict, FunctionTraceEntry]:
        # Tools are deterministic local code, not model inference — they work
        # regardless of which model (if any) is loaded.
        return tool_registry.execute(name, args, ctx)

    def health_check(self) -> ProviderHealth:
        return ProviderHealth(
            name=self.name, available=bool(LOCAL_MODEL_LOADED), real_inference=bool(LOCAL_MODEL_LOADED),
            simulated=False,
            detail="no local model loaded" if not LOCAL_MODEL_LOADED else "local model loaded")
