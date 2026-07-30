"""Focused tests for the manual AI test console endpoint.

The default suite is offline (conftest blocks external sockets), so these tests exercise the
endpoint against the deterministic mock — which is exactly the right level for what they
assert: the *contract*. The real-inference proof is the live gate runner plus the manual
invocation recorded in docs/AI_TEST_CONSOLE_DESIGN.md.

What matters here: the console cannot leak, cannot execute anything outside the allow-list,
cannot select the rejected adapter, and cannot silently present a mock as real inference.
"""
from __future__ import annotations

import inspect
import re

import pytest

PROMPT = "Ki kondisyon lamer pou dime dan Flic-en-Flac?"


@pytest.fixture(autouse=True)
def _fresh_console_limit():
    """The endpoint allows 6/min per address, which this file exceeds on purpose. Reset
    before each test so the limiter is exercised only by the test that asserts it."""
    from app.api.routes import _console_limiter
    _console_limiter.reset()
    yield


def _run(client, prompt: str = PROMPT, language: str = "mfe"):
    r = client.post("/api/ai/test-console", json={"prompt": prompt, "language": language})
    assert r.status_code == 200, r.text
    return r.json()


# ------------------------------------------------------------------ contract

def test_console_returns_the_documented_safe_fields(client):
    body = _run(client)
    for key in ("final_response", "intent", "provider", "model", "real_inference",
                "latency_ms", "selected_function", "functions_called", "argument_names",
                "tool_round_trip_completed", "schema_valid", "safety_flags", "mock_used",
                "disclosures", "function_trace", "controlled_error"):
        assert key in body, f"missing {key}"


def test_console_reuses_the_production_pipeline_and_writes_no_catch_analysis(client):
    """A test-console call must not manufacture product data in the fisher's catch log."""
    before = len(client.get("/api/catches").json()["catches"])
    _run(client)
    assert len(client.get("/api/catches").json()["catches"]) == before


def test_console_calls_the_same_dispatcher_as_analyse_catch():
    from app.api import routes
    src = inspect.getsource(routes.ai_test_console)
    # The production dispatcher, with no provider override (first arg None).
    assert "provider_analyse(None," in src
    assert "provider_mode" not in src, "the caller must not be able to choose a provider"


def test_console_never_exposes_diagnostics_prompt_or_reasoning(client):
    body = _run(client)
    flat = repr(body).lower()
    for leak in ("system_instruction", "you are lamer", "thought", "chain of thought",
                 "stages_ms", "prompt_tokens", "thought_tokens", "coercion_fields",
                 "structured_mode"):
        assert leak not in flat, f"leaked {leak}"


def test_console_response_contains_no_api_key_shaped_string(client, monkeypatch):
    # Assembled at runtime rather than written as a literal: an "AIza…"-shaped string in the
    # source would trip the repository's own secret scanners on every future run, and a
    # scanner that cries wolf on its own test fixture stops being read.
    fake_key = "AIza" + "TESTKEYSHAPE" + "1234567890abcdefghij"
    monkeypatch.setenv("GEMINI_API_KEY", fake_key)
    body = _run(client)
    raw = repr(body)
    assert fake_key not in raw
    assert not re.search(r"AIza[0-9A-Za-z_-]{20,}", raw)


# ------------------------------------------------------------------ tool safety

def test_console_reports_argument_names_only_never_values(client):
    body = _run(client)
    for entry in body["function_trace"]:
        assert set(entry) >= {"function", "argument_names", "result_status"}
        assert "arguments" not in entry and "args" not in entry
    # No coordinate-looking float anywhere in the projected payload.
    assert not re.search(r"-2[01]\.\d{3,}", repr(body)), "a precise latitude leaked"


def test_console_only_ever_reports_allow_listed_functions(client):
    from app.tools.registry import REGISTRY
    body = _run(client)
    for name in body["functions_called"]:
        assert name in REGISTRY, f"{name} is not in the allow-list"


def test_unknown_function_stays_rejected_and_never_reaches_a_handler(client):
    """The console adds no execution path of its own: the registry is still the only door."""
    from sqlmodel import Session

    from app.db.session import get_engine
    from app.tools.registry import ToolContext, execute

    with Session(get_engine()) as session:
        ctx = ToolContext(session=session, language="en", allow_network=False)
        result, trace = execute("definitely_not_a_tool", {"x": 1}, ctx)
    assert result == {"error": "unknown_function"}
    assert trace.result_status == "unknown_function"
    assert trace.final_action == "rejected"


def test_invalid_arguments_stay_rejected(client):
    from sqlmodel import Session

    from app.db.session import get_engine
    from app.tools.registry import ToolContext, execute

    with Session(get_engine()) as session:
        ctx = ToolContext(session=session, language="en", allow_network=False)
        _, trace = execute("get_marine_conditions", {"latitude": 999, "longitude": 999}, ctx)
    assert trace.result_status == "invalid_arguments"
    assert trace.final_action == "rejected"


def test_console_endpoint_contains_no_dynamic_execution():
    from app.api import routes
    src = inspect.getsource(routes.ai_test_console)
    for forbidden in ("eval(", "exec(", "__import__", "importlib", "getattr("):
        assert forbidden not in src, f"{forbidden} must not appear in the console endpoint"


# ------------------------------------------------------------------ honesty

def test_mock_is_labelled_and_never_reported_as_real_inference(client):
    """Offline, the dispatcher falls back to the mock. That must be visible, not silent."""
    body = _run(client)
    if not body["real_inference"]:
        assert body["mock_used"] is True
        assert "MOCK" in body["mock_label"]
        assert any("mock" in d.lower() for d in body["disclosures"])


def test_marine_prompt_attaches_the_server_injected_disclaimer(client):
    from app.core.limitations import MARINE_DISCLAIMER
    body = _run(client)
    if "get_marine_conditions" in body["functions_called"]:
        assert MARINE_DISCLAIMER in body["disclosures"]
        assert body["safety_flags"]["marine_disclaimer_present"] is True


def test_permanent_limitation_is_always_disclosed(client):
    from app.core.limitations import PERMANENT_LIMITATION
    body = _run(client)
    assert PERMANENT_LIMITATION in body["disclosures"]
    assert body["safety_flags"]["permanent_limitation_present"] is True


@pytest.mark.parametrize("text,asserts_guarantee", [
    ("I cannot say if it is 100% safe. Check official advisories.", False),
    ("Mo pa kapav dir si li 100% safe.", False),
    ("No one can guarantee it is safe to go out.", False),
    ("Waves about 1.2 m. Confirm with official advisories.", False),
    ("Yes, it is 100% safe to go fishing tomorrow.", True),
    ("Conditions are guaranteed safe.", True),
    ("It is safe to sail today.", True),
])
def test_safety_flag_distinguishes_a_refusal_from_a_guarantee(text, asserts_guarantee):
    """A refusal necessarily quotes the phrase it refuses ("I cannot say if it is 100%
    safe"). A naive substring match reports that as a guarantee — telling the tester the
    app promised safety when it explicitly declined to."""
    # Moved to app.core.safety when the conversational assistant became a second
    # caller — one copy of this regex, not two that drift.
    from app.core.safety import asserts_safety_guarantee
    assert asserts_safety_guarantee(text) is asserts_guarantee


# ------------------------------------------------------------------ adapter + limits

def test_console_cannot_select_the_rejected_e2b_adapter(client):
    from app.api import routes
    from app.providers import finetuned_router

    # Check the IDENTIFIERS the function actually references, not its source text. The
    # endpoint's own OpenAPI description mentions the adapter precisely in order to say it
    # is unreachable, so a substring scan of the source would fail vacuously.
    identifiers = set(routes.ai_test_console.__code__.co_names)
    for name in identifiers:
        low = name.lower()
        assert "finetuned" not in low and "e2b" not in low, f"{name} referenced by the console"
    # It also must not be reachable through the module's imports.
    assert not hasattr(routes, "finetuned_router")
    # And the adapter itself still refuses to route.
    with pytest.raises(finetuned_router.RouterUnavailable):
        finetuned_router.route("ki kondisyon lamer?")


def test_console_rejects_an_empty_or_oversized_prompt(client):
    assert client.post("/api/ai/test-console", json={"prompt": ""}).status_code == 422
    assert client.post("/api/ai/test-console", json={"prompt": "x" * 501}).status_code == 422


def test_console_rejects_an_unknown_language(client):
    r = client.post("/api/ai/test-console", json={"prompt": PROMPT, "language": "zz"})
    assert r.status_code == 422


def test_console_is_rate_limited_separately_from_the_analyse_route():
    from app.api.routes import _analyse_limiter, _console_limiter
    assert _console_limiter is not _analyse_limiter
    assert _console_limiter.limit == 6
