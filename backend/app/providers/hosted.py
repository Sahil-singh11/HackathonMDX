"""Compatibility shim — the hosted Gemma provider moved to `app.inference.gemma_hosted`.

Task 1a of the inference-provider migration relocated the implementation without
changing behaviour. This module forwards every attribute lookup (public and
private) to the new location so existing import sites — the dispatcher, the
evaluation harness, gate scripts and tests — keep working unmodified, and so a
monkeypatch applied on either module path is observed by callers of both.

New code should import `app.inference.gemma_hosted` directly.
"""
from __future__ import annotations

from app.inference import gemma_hosted as _impl


def __getattr__(name: str):
    return getattr(_impl, name)


def __dir__():
    return sorted(set(dir(_impl)))
