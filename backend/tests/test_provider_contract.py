"""Contract test suite — every inference provider must pass these.

Written at Task 1a (sync point S1); this is the suite the brief requires
"before the second implementation". Transport is mocked throughout: the fake
google-genai client below satisfies exactly the response surface the provider
reads (`candidates`, `text`, `parsed`, `usage_metadata`), so no test here
touches the network — the conftest socket guard enforces it.

Contract, per provider:
  1. Protocol conformance (all four methods, name attribute).
  2. `analyse_catch_image` output maps onto the FROZEN AnalyseCatchResponse.
  3. Unparseable model output degrades to the explicit low-confidence
     "unidentified" response — never an invented identification.
  4. Transport failure RAISES (selection/fallback/disclosure belong to the
     caller, never silently inside a provider).
  5. `health_check` tells the truth about availability and simulation.
"""
from __future__ import annotations

import pytest
from sqlmodel import Session

from app.core.config import get_settings
from app.db.session import get_engine, init_db
from app.inference import gemma_hosted, registry
from app.inference.base import InferenceProvider, ProviderHealth
from app.providers.local import LocalUnavailable
from app.schemas.analysis import AnalyseCatchResponse, ProviderInfo
from app.services.species.retrieval import candidates_for, public_candidate
from app.tools.registry import ToolContext

VALID_PAYLOAD = ('{"intent": "identify_catch", "species_suggestion": {"species_id": "octopus_cyanea", '
                 '"morisyen": "ourite", "english": "Day octopus", "scientific": "Octopus cyanea"}, '
                 '"visible_characteristics": ["bulbous mantle"], "confidence_label": "medium", '
                 '"species_confirmation_required": true, "estimated_size_unverified_cm": null, '
                 '"measured_size_required": true, "reply": "This may be a day octopus. Please confirm.", '
                 '"reply_morisyen": "Kitfwa enn ourite. Silvouple konfirm.", '
                 '"recommended_next_step": "confirm_species", "requested_function": null, "limitations": []}')


class _FakeResponse:
    """Minimal google-genai response: exactly the attributes the provider reads."""

    def __init__(self, text: str):
        self.candidates: list = []
        self.text = text
        self.parsed = None
        self.usage_metadata = None


class _FakeModels:
    def __init__(self, text: str, raise_exc: Exception | None = None):
        self._text = text
        self._raise = raise_exc
        self.calls = 0

    def generate_content(self, *, model, contents, config):
        self.calls += 1
        if self._raise is not None:
            raise self._raise
        return _FakeResponse(self._text)


class _FakeClient:
    def __init__(self, text: str = VALID_PAYLOAD, raise_exc: Exception | None = None):
        self.models = _FakeModels(text, raise_exc)


@pytest.fixture
def hosted_key(monkeypatch):
    """Pretend a key is configured, without any real key existing anywhere."""
    monkeypatch.setenv("GEMINI_API_KEY", "contract-test-fake-key")
    get_settings.cache_clear()
    yield
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setenv("GEMINI_API_KEY", "")
    get_settings.cache_clear()


def _patch_client(monkeypatch, fake: _FakeClient) -> None:
    import google.genai as genai
    monkeypatch.setattr(genai, "Client", lambda api_key: fake)


def _ctx() -> ToolContext:
    init_db()
    return ToolContext(session=Session(get_engine()), allow_network=False)


def _candidates() -> list[dict]:
    return [public_candidate(s) for s in candidates_for(None)]


def _assert_maps_to_frozen_schema(res) -> None:
    """A ProviderResult must assemble into the FROZEN response without edits."""
    built = AnalyseCatchResponse(
        analysis_id="contract-test",
        intent=res.intent,
        visible_characteristics=res.visible_characteristics,
        confidence_label=res.confidence_label,
        estimated_size_unverified_cm=res.estimated_size_unverified_cm,
        reply=res.reply,
        reply_morisyen=res.reply_morisyen,
        recommended_next_step=res.recommended_next_step,
        function_trace=res.function_trace,
        provider=ProviderInfo(mode=res.mode, provider_name=res.provider_name,
                              model=res.model, real_inference=res.real_inference,
                              latency_ms=res.latency_ms),
    )
    assert built.species_confirmation_required is True
    assert built.measured_size_required is True
    assert built.legal_check.status == "pending_confirmation"


# ------------------------------------------------------------------ 1. protocol

def test_every_registered_provider_satisfies_the_protocol():
    for name in registry.CANONICAL:
        provider = registry.get_provider(name)
        assert isinstance(provider, InferenceProvider), name
        assert provider.name == name


def test_selection_precedence_and_aliases(monkeypatch):
    assert registry.resolve_name("hosted") == registry.GEMMA_HOSTED
    assert registry.resolve_name("local") == registry.GEMMA_LOCAL
    assert registry.resolve_name("gemma_hosted") == registry.GEMMA_HOSTED
    assert registry.resolve_name("auto") == registry.AUTO
    # INFERENCE_PROVIDER beats the PROVIDER_MODE alias.
    monkeypatch.setenv("INFERENCE_PROVIDER", "gemma_local")
    monkeypatch.setenv("PROVIDER_MODE", "hosted")
    get_settings.cache_clear()
    try:
        assert registry.resolve_name(None) == registry.GEMMA_LOCAL
    finally:
        monkeypatch.delenv("INFERENCE_PROVIDER", raising=False)
        get_settings.cache_clear()
    with pytest.raises(KeyError):
        registry.resolve_name("made_up_provider")


def test_auto_policy_records_every_skip_and_lands_on_mock_without_key():
    provider, events = registry.select("auto")
    assert provider.name == registry.MOCK
    assert [e.skipped for e in events] == [registry.GEMMA_LOCAL, registry.GEMMA_HOSTED]
    assert all(e.reason for e in events)


# ------------------------------------------------------------------ 2. frozen schema

def test_hosted_valid_output_maps_onto_frozen_schema(monkeypatch, hosted_key):
    _patch_client(monkeypatch, _FakeClient(text=VALID_PAYLOAD))
    res = registry.get_provider(registry.GEMMA_HOSTED).analyse_catch_image(
        None, "mo'nn gagn enn ourite", "mfe", _candidates(), _ctx())
    assert res.mode == "hosted" and res.real_inference is True
    assert res.species_id == "octopus_cyanea"
    _assert_maps_to_frozen_schema(res)


def test_mock_output_maps_onto_frozen_schema():
    res = registry.get_provider(registry.MOCK).analyse_catch_image(
        None, "ki kalite lamer ena zordi?", "mfe", _candidates(), _ctx())
    assert res.mode == "mock" and res.real_inference is False
    _assert_maps_to_frozen_schema(res)


# ------------------------------------------------------------------ 3. degradation

def test_hosted_unparseable_output_degrades_to_explicit_unidentified(monkeypatch, hosted_key):
    _patch_client(monkeypatch, _FakeClient(text="the model rambled and produced no json at all"))
    res = registry.get_provider(registry.GEMMA_HOSTED).analyse_catch_image(
        None, "ki pwason sa?", "en", _candidates(), _ctx())
    assert res.species_id is None                      # never an invented identification
    assert res.confidence_label == "low"
    assert res.recommended_next_step == "confirm_species"
    assert res.diagnostics.get("fallback_reason")      # honest about why


# ------------------------------------------------------------------ 4. failure raises

def test_hosted_transport_failure_raises_for_the_caller(monkeypatch, hosted_key):
    _patch_client(monkeypatch, _FakeClient(raise_exc=TimeoutError("simulated transport timeout")))
    with pytest.raises(TimeoutError):
        registry.get_provider(registry.GEMMA_HOSTED).analyse_catch_image(
            None, "ki pwason sa?", "en", _candidates(), _ctx())


def test_hosted_without_key_raises_hosted_unavailable():
    with pytest.raises(gemma_hosted.HostedUnavailable):
        registry.get_provider(registry.GEMMA_HOSTED).analyse_catch_image(
            None, "x", "en", _candidates(), _ctx())


def test_local_raises_local_unavailable_for_inference_entry_points():
    provider = registry.get_provider(registry.GEMMA_LOCAL)
    with pytest.raises(LocalUnavailable):
        provider.analyse_catch_image(None, "x", "en", _candidates(), _ctx())
    with pytest.raises(LocalUnavailable):
        provider.chat("hello")


# ------------------------------------------------------------------ 5. health honesty

def test_health_checks_tell_the_truth():
    hosted_health = registry.get_provider(registry.GEMMA_HOSTED).health_check()
    assert isinstance(hosted_health, ProviderHealth)
    assert hosted_health.available is False            # conftest blanks the key
    assert hosted_health.simulated is False

    local_health = registry.get_provider(registry.GEMMA_LOCAL).health_check()
    assert local_health.available is False              # no model loaded, ever, in tests
    assert local_health.real_inference is False

    mock_health = registry.get_provider(registry.MOCK).health_check()
    assert mock_health.available is True
    assert mock_health.simulated is True                # can never claim real inference


def test_hosted_health_flips_available_with_a_key(hosted_key):
    assert registry.get_provider(registry.GEMMA_HOSTED).health_check().available is True


# ------------------------------------------------------------------ chat + tools

def test_mock_chat_is_disclosed_and_tools_route_through_central_registry():
    provider = registry.get_provider(registry.MOCK)
    assert "MOCK" in provider.chat("what can you do?")
    result, trace = provider.call_tools("get_current_demo_date", {}, _ctx())
    assert "date" in result
    assert trace.result_status == "ok"
    bad, trace2 = provider.call_tools("delete_database", {}, _ctx())
    assert bad == {"error": "unknown_function"}
    assert trace2.final_action == "rejected"


def test_hosted_chat_uses_mocked_transport(monkeypatch, hosted_key):
    _patch_client(monkeypatch, _FakeClient(text="Bonzur! Mo kapav ed ou."))
    text = registry.get_provider(registry.GEMMA_HOSTED).chat("ki to kapav fer?", language="mfe")
    assert text == "Bonzur! Mo kapav ed ou."
