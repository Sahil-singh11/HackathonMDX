"""Final acceptance regression tests.

Locks the shipped AI state: hosted gemma-4-26b-a4b-it is production, the rejected E2B
adapter cannot be activated accidentally (env var, provider mode, API route, dispatcher,
or malformed local output), and the training-evidence documents never carry a forbidden
claim. All offline.
"""
import json
import os
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]

REQUIRED_MODEL = "gemma-4-26b-a4b-it"


# ---------------------------------------------------------------- production model pinned

def test_production_model_is_exactly_the_pinned_gemma():
    from app.core.config import get_settings
    s = get_settings()
    assert s.gemma_model == REQUIRED_MODEL
    assert s.gemma_provider == "google"


def test_no_environment_default_substitutes_another_model(monkeypatch):
    """A blank/unset GEMMA_MODEL must still resolve to the pinned model, never Gemini/
    Gemma-3/another size."""
    from app.core.config import Settings
    monkeypatch.delenv("GEMMA_MODEL", raising=False)
    s = Settings(_env_file=None)  # ignore .env: pure defaults
    assert s.gemma_model == REQUIRED_MODEL
    low = s.gemma_model.lower()
    assert "gemini" not in low and "gemma-3" not in low and "e2b" not in low


def test_hosted_provider_has_no_hardcoded_model_substitution():
    """Audits the real implementation, not the shim.

    `app.providers.hosted` is a compatibility shim since the Task-1a inference-provider
    migration; the implementation lives in `app.inference.gemma_hosted`. Reading the shim
    would vacuously pass, so resolve to the module that actually calls the SDK.
    """
    import inspect

    from app.inference import gemma_hosted
    from app.providers import hosted

    src = inspect.getsource(gemma_hosted)
    assert "from google import genai" in src, "must use the official google-genai SDK"
    assert "settings.gemma_model" in src, "model must come from configuration, never a literal"
    assert not re.search(r"[\"']gemini-[\w.\-]+[\"']", src)
    assert not re.search(r"[\"']gemma-3[\w.\-]*[\"']", src)
    # The shim must forward to that implementation so both import paths agree.
    assert hosted.analyse is gemma_hosted.analyse


def test_capability_surface_reports_hosted_correctly():
    from app.providers.capabilities import all_capabilities
    caps = all_capabilities()
    h = caps["hosted"].model_dump()
    assert h["provider_name"] == "google-genai"
    assert h["model_name"] == REQUIRED_MODEL
    for k in ("supports_text", "supports_image", "supports_structured_output",
              "supports_function_calling"):
        assert h[k] is True
    assert h["timeout_seconds"] > 0
    m = caps["mock"].model_dump()
    assert m["simulated"] is True and m["real_inference"] is False, \
        "mock must always be labelled simulated"


# ---------------------------------------------------------------- adapter cannot activate

def test_adapter_readiness_reports_rejected_with_exact_gates():
    from app.providers import finetuned_router as fr
    s = fr.readiness()
    assert s.available is False
    assert s.gate_passed is False
    for criterion in ("A2_external_intent_ge_0.80", "A3_tool_ge_0.80",
                      "A10_min_critical_recall_ge_0.75"):
        assert criterion in s.reason, f"failing gate {criterion} must be named"


def test_adapter_metrics_match_the_recorded_rejection():
    from app.providers import finetuned_router as fr
    d = fr.readiness().as_dict()
    assert d["intent_accuracy"] == pytest.approx(0.8529, abs=1e-4)
    assert d["tool_accuracy"] == pytest.approx(0.5882, abs=1e-4)


def test_adapter_route_refuses_execution():
    from app.providers import finetuned_router as fr
    with pytest.raises(fr.RouterUnavailable):
        fr.route("Ki kondisyon lamer?")


def test_provider_mode_cannot_select_the_adapter():
    import typing

    from app.schemas.analysis import ProviderMode
    modes = set(typing.get_args(ProviderMode))
    assert modes == {"hosted", "local", "mock"}
    assert not any("e2b" in m or "finetuned" in m or "adapter" in m for m in modes)


def test_analyse_route_rejects_an_adapter_provider_mode(client):
    r = client.post("/api/analyse-catch",
                    data={"note": "test", "provider_mode": "finetuned"})
    assert r.status_code == 422, "an adapter provider_mode must be rejected by the API"


def test_no_environment_variable_silently_activates_the_adapter(monkeypatch):
    """Even a hypothetical enabling env var must not change readiness — activation is
    gated ONLY on a pre-registered gate pass recorded in the metrics artifact."""
    from app.providers import finetuned_router as fr
    for var in ("ENABLE_E2B_ROUTER", "FINETUNED_ROUTER", "E2B_ADAPTER", "ROUTER_MODE",
                "USE_ADAPTER", "PROVIDER_MODE"):
        monkeypatch.setenv(var, "finetuned")
    s = fr.readiness()
    assert s.available is False
    with pytest.raises(fr.RouterUnavailable):
        fr.route("test")


def test_dispatcher_never_references_the_finetuned_provider():
    import inspect

    from app.providers import dispatcher
    src = inspect.getsource(dispatcher)
    assert "finetuned" not in src.lower()
    assert "e2b" not in src.lower()


def test_malformed_local_output_cannot_execute_a_function():
    from app.providers import finetuned_router as fr
    from app.tools.registry import REGISTRY
    for bad in (None, {"intent": "x", "tool": "delete_everything"},
                {"tool": "get_marine_conditions'; DROP TABLE"}, {"arguments": "not-a-dict"}):
        out = fr.validate_route(bad if isinstance(bad, dict) else None)
        assert out["tool"] is None or out["tool"] in REGISTRY


def test_adapter_weights_are_gitignored():
    import subprocess
    r = subprocess.run(["git", "check-ignore", "kaggle/outputs"], cwd=ROOT,
                       capture_output=True, text=True)
    assert r.returncode == 0, "kaggle/outputs (adapter weights) must be git-ignored"
    tracked = subprocess.run(["git", "ls-files", "kaggle/outputs"], cwd=ROOT,
                             capture_output=True, text=True).stdout.strip()
    assert not tracked, "no adapter weight files may be tracked"


def test_historical_acceptance_decision_is_unchanged():
    m = json.loads((ROOT / "training" / "results" / "v2_evaluation_metrics.json")
                   .read_text(encoding="utf-8"))
    assert m["decision"] == "REJECTED"
    assert m["gate_a"]["ACCEPTED"] is False
    assert m["gate_b"]["ACCEPTED"] is False
    v1 = json.loads((ROOT / "training" / "archive" / "v1" / "MANIFEST.json")
                    .read_text(encoding="utf-8"))
    assert v1["step3_acceptance_decision"]["accepted"] is False


# ---------------------------------------------------------------- forbidden claims

FORBIDDEN_PATTERNS = [
    (re.compile(r"adapter is (now |the )?production", re.I), "adapter-as-production"),
    (re.compile(r"universal(ly)? 85\.?3?%", re.I), "universal accuracy"),
    (re.compile(r"all Morisyen (data )?(is|was) native[- ]speaker verified", re.I),
     "native-speaker claim"),
    (re.compile(r"\bAI (makes|decides) legal", re.I), "legal decisions"),
    (re.compile(r"guarantee[sd]? (marine )?safety", re.I), "safety guarantee"),
    (re.compile(r"ministry submission is real", re.I), "real ministry"),
]

SUBMISSION_DOCS = [
    "docs/AI_SUBMISSION_SUMMARY.md", "docs/AI_JUDGE_TECHNICAL_PROOF.md",
    "docs/AI_DEMO_SCRIPT.md", "docs/AI_LIMITATIONS.md", "docs/AI_FINAL_HANDOFF.md",
    "docs/AI_MODEL_SELECTION_DECISION.md", "kaggle/writeup.md",
]


@pytest.mark.parametrize("doc", SUBMISSION_DOCS)
def test_submission_documents_carry_no_forbidden_claim(doc):
    text = (ROOT / doc).read_text(encoding="utf-8")
    for pat, label in FORBIDDEN_PATTERNS:
        assert not pat.search(text), f"{doc}: forbidden claim ({label})"


def test_writeup_uses_the_approved_rejection_phrasing():
    text = (ROOT / "kaggle" / "writeup.md").read_text(encoding="utf-8").lower()
    assert "training succeeded, but the adapter did not pass the production acceptance" in text
    assert "the fine-tuning failed" not in text


# ---------------------------------------------------------------- declaration PDF export

def test_declaration_pdf_exports_with_the_em_dash_mock_label(tmp_path, monkeypatch):
    """Regression: fpdf core fonts are Latin-1, and MOCK_LABEL contains an em-dash.

    Before the fix, GET /api/declarations/{id}/pdf raised
    FPDFUnicodeEncodingException and returned 500 for every declaration.
    """
    import json as _json

    from app.models.entities import Declaration
    from app.services.declarations import service

    monkeypatch.setattr(service.get_settings(), "storage_dir", tmp_path, raising=False)
    decl = Declaration(
        fisher_name="Tester", fishing_area="Grand Baie",
        period_start="2026-07-01", period_end="2026-07-31", status="prepared",
        catches_json=_json.dumps([{"capture_date": "2026-07-29", "species_id": "octopus_cyanea",
                                   "count": 1, "measured_length_cm": 45.0,
                                   "legal_status": "allowed"}]),
        mock_receipt_id="MOCK-20260729-ABCDEF",
    )
    out = service.export_pdf(decl)
    assert out.exists()
    assert out.read_bytes()[:4] == b"%PDF"


def test_pdf_safe_preserves_the_mock_safety_wording():
    from app.services.declarations.service import MOCK_LABEL, _pdf_safe
    safe = _pdf_safe(MOCK_LABEL)
    assert "MOCK DEMONSTRATION" in safe
    assert "NOT AN OFFICIAL GOVERNMENT SUBMISSION" in safe
    safe.encode("latin-1")  # must not raise


def test_pdf_safe_transliterates_typographic_characters():
    from app.services.declarations.service import _pdf_safe
    assert _pdf_safe("a\u2014b") == "a-b"
    assert _pdf_safe("\u2018q\u2019 \u201cd\u201d") == "'q' \"d\""
    _pdf_safe("\u2026\u00a0").encode("latin-1")


# --- harness honesty: a transport error is neither a pass nor a safety failure ----------

def test_live_gate_runner_retries_server_side_transients_but_not_content_errors():
    """A 500/503 never reaches a content assertion, so scoring it as a gate failure is a
    false alarm — and scoring it as a pass would be dishonest. It must be retried, then
    labelled TRANS, while a real model error (NOT_FOUND) must not be retried."""
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "_gates", Path(__file__).resolve().parents[1] / "scripts" / "run_final_live_gates.py")
    gates = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gates)

    for transient in ("ServerError: 500 INTERNAL", "503 UNAVAILABLE", "429 RESOURCE_EXHAUSTED",
                      "504 DEADLINE_EXCEEDED", "502 Bad Gateway"):
        assert gates.TRANSIENT.search(transient), transient
    for real in ("404 NOT_FOUND: model not found", "400 INVALID_ARGUMENT",
                 "403 PERMISSION_DENIED"):
        assert not gates.TRANSIENT.search(real), real

    gates.RESULTS.clear()
    gates.record("gate_x", "n", "FAIL", "ServerError: 500 INTERNAL.")
    assert gates.RESULTS[-1]["status"] == "TRANS"

    # A failure with real check results stays FAIL even if the detail mentions a code.
    gates.RESULTS.clear()
    gates.record("gate_y", "n", "FAIL", "500 INTERNAL", checks={"no_safety_claim": False})
    assert gates.RESULTS[-1]["status"] == "FAIL"
    gates.RESULTS.clear()


def test_live_tier_client_retries_transients_and_reraises_real_errors():
    from tests import test_hosted_integration as live

    class Boom:
        def __init__(self, exc, succeed_on=None):
            self.exc, self.succeed_on, self.calls = exc, succeed_on, 0

        def generate_content(self, **kw):
            self.calls += 1
            if self.succeed_on and self.calls >= self.succeed_on:
                return "ok"
            raise RuntimeError(self.exc)

    recovering = Boom("ServerError: 500 INTERNAL", succeed_on=2)
    assert live._RetryingModels(recovering, attempts=3, delay=0).generate_content() == "ok"
    assert recovering.calls == 2

    permanent = Boom("404 NOT_FOUND")
    with pytest.raises(RuntimeError):
        live._RetryingModels(permanent, attempts=3, delay=0).generate_content()
    assert permanent.calls == 1, "a real model error must not be retried"

    persistent = Boom("503 UNAVAILABLE")
    with pytest.raises(RuntimeError):
        live._RetryingModels(persistent, attempts=3, delay=0).generate_content()
    assert persistent.calls == 3, "retry must be bounded and must still surface the failure"


def test_final_check_reports_missing_backend_dependencies_by_name():
    """An unsynced venv must be named as such, not surface as an opaque collection error."""
    import importlib.util

    root = Path(__file__).resolve().parents[2]
    spec = importlib.util.spec_from_file_location(
        "_finalcheck", root / "scripts" / "final_ai_check.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    absent = mod.missing_requirements()
    assert absent == [], f"venv is out of sync with backend/requirements.txt: {absent}"
    assert "pypdf" in (root / "backend" / "requirements.txt").read_text(encoding="utf-8")


def test_weather_gate_follows_the_tool_chain_instead_of_assuming_the_first_turn():
    """The model may resolve the demo date before asking for conditions ("dime" = tomorrow).
    The gate must audit the whole chain — allow-listed at every turn, marine tool reached —
    and gate 4 must round-trip the marine tool specifically, not a preparatory one."""
    src = (Path(__file__).resolve().parents[1] / "scripts" / "run_final_live_gates.py"
           ).read_text(encoding="utf-8")
    assert "MAX_TURNS" in src
    assert '"requested_get_marine_conditions": "get_marine_conditions" in chain' in src
    assert '"allow_listed_only": all(n in REGISTRY for n in chain)' in src
    assert '"round_trips_the_marine_tool": fc.name == "get_marine_conditions"' in src


def test_transient_classifier_covers_network_faults_not_just_google_errors():
    """A DNS failure or dropped connection also never reaches an assertion. Classifying it
    as a gate failure would report a model regression for a Wi-Fi drop."""
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "_gates2", Path(__file__).resolve().parents[1] / "scripts" / "run_final_live_gates.py")
    gates = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gates)

    for fault in ("ConnectError: [Errno 11004] getaddrinfo failed",
                  "RemoteProtocolError: Server disconnected without sending a response.",
                  "ConnectTimeout", "ReadTimeout", "Connection reset by peer",
                  "Temporary failure in name resolution"):
        assert gates.TRANSIENT.search(fault), fault
    for behavioural in ("species_confirmation_required was false",
                        "AUTHORITATIVE claim present", "schema validation failed"):
        assert not gates.TRANSIENT.search(behavioural), behavioural
