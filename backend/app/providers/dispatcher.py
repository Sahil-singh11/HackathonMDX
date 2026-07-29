"""Provider selection + honest fallback.

hosted -> mock on failure (visible FALLBACK_DISCLOSURE); local only if a model
is actually loaded; mock always works offline.
"""
from __future__ import annotations

import logging

from app.core.config import get_settings
from app.core.limitations import FALLBACK_DISCLOSURE
from app.providers import hosted, local, mock
from app.providers.base import ProviderResult
from app.tools.registry import ToolContext

log = logging.getLogger(__name__)


def analyse(requested_mode: str | None, image_jpeg: bytes | None, image_sha: str | None,
            note: str | None, language: str, candidates: list[dict], ctx: ToolContext) -> ProviderResult:
    settings = get_settings()
    mode = requested_mode or settings.provider_mode

    if mode == "hosted":
        try:
            return hosted.analyse(image_jpeg, note, language, candidates, ctx)
        except Exception as e:  # noqa: BLE001 — any hosted failure falls back with disclosure
            log.warning("hosted provider unavailable (%s); falling back to mock", type(e).__name__)
            res = mock.analyse(image_sha, note, language, candidates, ctx)
            res.disclosures.insert(0, FALLBACK_DISCLOSURE)
            return res

    if mode == "local":
        try:
            return local.analyse(image_jpeg, note, language, candidates, ctx)
        except local.LocalUnavailable as e:
            log.warning("local provider unavailable: %s", e)
            res = mock.analyse(image_sha, note, language, candidates, ctx)
            res.disclosures.insert(0, "Local Gemma model not loaded; deterministic mock used instead.")
            return res

    return mock.analyse(image_sha, note, language, candidates, ctx)
