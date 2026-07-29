"""Task 4a contract tests.

Covers the four promises the pillar contract makes:
1. /api/pillars lists all six national pillars — fisheries live, five
   registered-but-disabled — with government naming verbatim.
2. DataProvenance is structurally mandatory: no PillarResult without it, no
   empty coverage note, no invented data_kind.
3. The import boundary: nothing under app/pillars touches model SDKs or
   provider modules; inference access is app.inference.base / .registry only.
4. The mount helper: a registered module's routes appear under
   /api/pillars/{id}, answer 503 while the pillar is disabled, serve when
   enabled, and inherit the per-IP throttle (429 + Retry-After).
"""
from __future__ import annotations

import ast
from datetime import datetime, timezone
from pathlib import Path

import pytest
from pydantic import ValidationError

PILLARS_DIR = Path(__file__).resolve().parents[1] / "app" / "pillars"
ALLOWED_INFERENCE_IMPORTS = {"app.inference.base", "app.inference.registry"}
FORBIDDEN_IMPORT_PREFIXES = ("app.providers", "app.inference.gemma_hosted",
                             "app.inference.gemma_local", "google.genai",
                             "google.generativeai")

GOVERNMENT_NAMES = {
    "Sustainable Fisheries & Aquaculture",
    "Marine Transport & Trade",
    "Sustainable Ocean Tourism",
    "Ocean-Based Renewable Energy",
    "Blue Finance",
    "Marine Biotechnology",
}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _provenance(**overrides):
    from app.pillars.provenance import DataProvenance

    base = dict(source_name="fixture", source_url=None, retrieved_at=_now(),
                data_kind="sample", model_provider="mock",
                coverage_note="fixture data; covers nothing real")
    base.update(overrides)
    return DataProvenance(**base)


# -- 1. listing --------------------------------------------------------------

def test_listing_has_six_pillars_fisheries_live_rest_registered(client):
    r = client.get("/api/pillars")
    assert r.status_code == 200
    body = r.json()
    assert body["count"] == 6
    by_id = {p["pillar_id"]: p for p in body["pillars"]}
    assert set(by_id) == {"fisheries", "transport", "tourism", "energy", "finance", "biotech"}

    fisheries = by_id["fisheries"]
    assert fisheries["status"] == "live" and fisheries["enabled"] and fisheries["implemented"]
    assert "/api/analyse-catch" in fisheries["endpoints"]

    for pid in ("transport", "tourism", "energy", "finance", "biotech"):
        assert by_id[pid]["status"] == "registered", pid
        assert by_id[pid]["enabled"] is False, pid


def test_government_pillar_naming_verbatim(client):
    names = {p["pillar_name"] for p in client.get("/api/pillars").json()["pillars"]}
    assert names == GOVERNMENT_NAMES


def test_listing_route_carries_per_ip_throttle(client):
    from app.pillars import routes as pillar_routes

    limit = pillar_routes._pillars_limiter.limit
    for _ in range(limit):
        assert client.get("/api/pillars").status_code == 200
    over = client.get("/api/pillars")
    assert over.status_code == 429
    assert over.headers.get("retry-after") == "60"
    # autouse _reset_demo_state fixture clears the bucket after this test —
    # which itself proves /api/demo/reset sweeps the pillar limiter.


def test_demo_reset_clears_pillar_limiter(client):
    from app.pillars import routes as pillar_routes

    limit = pillar_routes._pillars_limiter.limit
    for _ in range(limit):
        client.get("/api/pillars")
    assert client.get("/api/pillars").status_code == 429
    client.post("/api/demo/reset")
    assert client.get("/api/pillars").status_code == 200


# -- 2. provenance is structurally mandatory ---------------------------------

def test_pillar_result_requires_provenance():
    from app.pillars.base import PillarResult

    with pytest.raises(ValidationError):
        PillarResult(pillar_id="x", generated_at=_now())  # no provenance


def test_provenance_rejects_empty_coverage_note_and_blank_provider():
    with pytest.raises(ValidationError):
        _provenance(coverage_note="")
    with pytest.raises(ValidationError):
        _provenance(model_provider="")


def test_provenance_rejects_invented_data_kind():
    with pytest.raises(ValidationError):
        _provenance(data_kind="guessed")


def test_subclassed_result_still_requires_provenance():
    from app.pillars.base import PillarResult

    class TransportBrief(PillarResult):
        headline: str

    with pytest.raises(ValidationError):
        TransportBrief(pillar_id="transport", generated_at=_now(), headline="x")
    ok = TransportBrief(pillar_id="transport", generated_at=_now(),
                        headline="x", provenance=_provenance())
    assert ok.provenance.data_kind == "sample"


# -- 3. import boundary ------------------------------------------------------

def test_pillars_import_boundary():
    offenders: list[tuple[str, str]] = []
    for py in sorted(PILLARS_DIR.rglob("*.py")):
        tree = ast.parse(py.read_text(encoding="utf-8"), filename=str(py))
        for node in ast.walk(tree):
            modules: list[str] = []
            if isinstance(node, ast.Import):
                modules = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                modules = [node.module]
            for mod in modules:
                if mod.startswith("app.inference") and mod not in ALLOWED_INFERENCE_IMPORTS:
                    offenders.append((py.name, mod))
                if mod.startswith(FORBIDDEN_IMPORT_PREFIXES):
                    offenders.append((py.name, mod))
    assert not offenders, (
        "pillar files must reach models only via app.inference.base/registry; "
        f"forbidden imports found: {offenders}"
    )


# -- 4. protocol + mounting --------------------------------------------------

def _dummy_pillar_module():
    from app.pillars.base import (PillarModule, PillarResult, RawBundle,
                                  SourceDescriptor)

    class DummyResult(PillarResult):
        headline: str

    class DummyPillar:
        pillar_id = "dummy"
        pillar_name = "Dummy Pillar"
        result_schema = DummyResult

        def sources(self):
            return [SourceDescriptor(name="fixture", status="none")]

        async def fetch(self, params: dict) -> RawBundle:
            return RawBundle(pillar_id="dummy",
                             source=SourceDescriptor(name="fixture", status="none"),
                             retrieved_at=_now(), data_kind="sample",
                             coverage_note="fixture data", payload={})

        async def analyse(self, bundle: RawBundle):
            return DummyResult(pillar_id="dummy", generated_at=_now(),
                               provenance=_provenance(), headline="ok")

    assert isinstance(DummyPillar(), PillarModule)
    return DummyPillar()


def _fresh_pillar_app(enabled: set[str], limit: int):
    """A fresh FastAPI app with an isolated registry + limiter, so mount
    behaviour is tested without touching the app-wide singletons."""
    from fastapi import APIRouter, FastAPI
    from fastapi.testclient import TestClient

    from app.core.ratelimit import InMemoryRateLimiter
    from app.pillars.registry import PillarDescriptor, PillarRegistry
    from app.pillars.routes import build_pillar_router

    registry = PillarRegistry(enabled_ids=lambda: enabled)
    registry.register_descriptor(PillarDescriptor(pillar_id="dummy", pillar_name="Dummy Pillar"))
    sub = APIRouter()

    @sub.get("/ping")
    def ping() -> dict:
        return {"pong": True}

    registry.register_module(_dummy_pillar_module(), router=sub)
    app = FastAPI()
    app.include_router(build_pillar_router(registry=registry,
                                           limiter=InMemoryRateLimiter(limit=limit, window_seconds=60.0)))
    return TestClient(app)


def test_registering_module_requires_descriptor_and_protocol():
    from app.pillars.registry import PillarRegistry

    registry = PillarRegistry(enabled_ids=lambda: set())
    with pytest.raises(ValueError):
        registry.register_module(_dummy_pillar_module())  # no descriptor declared

    class NotAPillar:
        pillar_id = "nope"

    with pytest.raises(TypeError):
        registry.register_module(NotAPillar())  # type: ignore[arg-type]


def test_mounted_pillar_route_disabled_answers_503():
    c = _fresh_pillar_app(enabled=set(), limit=5)
    listing = {p["pillar_id"]: p for p in c.get("/api/pillars").json()["pillars"]}
    assert listing["dummy"]["implemented"] and not listing["dummy"]["enabled"]
    r = c.get("/api/pillars/dummy/ping")
    assert r.status_code == 503


def test_mounted_pillar_route_enabled_serves_and_throttles():
    c = _fresh_pillar_app(enabled={"dummy"}, limit=2)
    assert c.get("/api/pillars/dummy/ping").json() == {"pong": True}
    assert c.get("/api/pillars/dummy/ping").status_code == 200
    over = c.get("/api/pillars/dummy/ping")
    assert over.status_code == 429
    assert over.headers.get("retry-after") == "60"
