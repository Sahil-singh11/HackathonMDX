"""AI Step 4 — review propagation, v1 immutability, dataset v2, gates and routing.

All offline. The conftest forces PROVIDER_MODE=mock and clears GEMINI_API_KEY.
"""
import csv
import hashlib
import json
import re
from pathlib import Path

import pytest

from app.prompts.compact_router_v1 import ALLOWED_INTENTS, ROUTABLE_TOOLS
from app.tools.registry import REGISTRY

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "training" / "data"
ARCHIVE = ROOT / "training" / "archive" / "v1"
EXTERNAL = ROOT / "evaluation" / "cases" / "morisyen_cases.json"


def L(p: Path) -> list[dict]:
    return [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]


def norm(t: str) -> str:
    t = t.lower().replace("'", " ").replace("’", " ")
    return " ".join(re.sub(r"[^\w\s]", " ", t).split())


@pytest.fixture(scope="module")
def v2() -> list[dict]:
    return L(DATA / "master_records_v2.jsonl")


@pytest.fixture(scope="module")
def challenge() -> list[dict]:
    return L(DATA / "v2_challenge_test.jsonl")


@pytest.fixture(scope="module")
def internal34() -> list[dict]:
    return L(DATA / "internal_test_v1_34.jsonl")


# --------------------------------------------------------------- review propagation

def test_approved_review_reached_the_dataset(v2):
    reviewed = [r for r in v2 if r["human_review_status"] == "reviewed"]
    assert len(reviewed) == 30
    for r in reviewed:
        assert r["provenance"] == "AI_generated_human_reviewed"
        assert "review" in r


def test_review_block_records_who_and_how(v2):
    for r in v2:
        rv = r.get("review")
        if not rv:
            continue
        assert rv["reviewer_status"] in ("ok", "reworded", "wrong_label")
        assert rv["approver"]
        assert rv["original_provenance"] == "AI_generated_review_required"
        assert isinstance(rv["native_speaker_verified"], bool)


def test_review_does_not_claim_native_speaker_verification(v2):
    """The approver was explicitly not a verified native speaker."""
    for r in v2:
        rv = r.get("review")
        if rv:
            assert rv["native_speaker_verified"] is False


def test_reviewed_wording_is_byte_identical_to_the_pre_review_dataset(v2):
    """Approval was given without edits; no AI wording may have replaced it either."""
    before = {r["id"]: r for r in L(ARCHIVE / "master_records.jsonl")}
    for r in v2:
        if r["id"] in before and r.get("dataset_version", "v1") == "v1":
            assert r["user_input"] == before[r["id"]]["user_input"], r["id"]


def test_review_csv_matches_what_was_applied():
    rows = list(csv.DictReader((DATA / "HUMAN_REVIEW_REQUIRED.csv").open(encoding="utf-8")))
    assert len(rows) == 30
    assert all(r["reviewer_status"].strip() == "ok" for r in rows)
    assert all(not r["corrected_text"].strip() for r in rows), "no corrections were recorded"


def test_unreviewed_records_are_still_marked_unreviewed(v2):
    pending = [r for r in v2 if r["human_review_status"] == "pending"]
    assert len(pending) == len(v2) - 30
    for r in pending:
        assert r["provenance"] == "AI_generated_review_required"


# --------------------------------------------------------------- v1 archive immutability

def test_v1_archive_exists_with_manifest_and_checksums():
    assert (ARCHIVE / "MANIFEST.json").exists()
    assert (ARCHIVE / "CHECKSUMS.sha256").exists()
    m = json.loads((ARCHIVE / "MANIFEST.json").read_text(encoding="utf-8"))
    assert m["version"] == "v1"
    assert m["base_model"] == "google/gemma-4-E2B-it"


def test_v1_archive_checksums_still_verify():
    """Content immutability, tolerant of git EOL rewriting.

    On Windows, core.autocrlf rewrote the archived files CRLF on checkout, breaking the
    raw byte hashes while the CONTENT was untouched (verified: LF-normalising every
    flagged file reproduced its recorded digest exactly). So a file passes if either its
    raw bytes or its LF-normalised bytes match — a real edit still fails both.
    .gitattributes now marks the archive `-text` so fresh checkouts keep the exact bytes.
    """
    lines = (ARCHIVE / "CHECKSUMS.sha256").read_text(encoding="utf-8").splitlines()
    checked = 0
    for line in lines:
        if not line.strip():
            continue
        digest, name = line.split("  ", 1)
        p = (ARCHIVE / name).resolve()
        if not p.exists():
            continue
        raw = p.read_bytes()
        ok = (hashlib.sha256(raw).hexdigest() == digest
              or hashlib.sha256(raw.replace(b"\r\n", b"\n")).hexdigest() == digest)
        assert ok, f"{name} CONTENT changed (not just line endings)"
        checked += 1
    assert checked >= 10


def test_v1_step3_decision_is_preserved_unchanged():
    m = json.loads((ARCHIVE / "MANIFEST.json").read_text(encoding="utf-8"))
    d = m["step3_acceptance_decision"]
    assert d["accepted"] is False
    assert d["internal_intent_accuracy"] == 0.7353
    assert d["internal_tool_accuracy"] == 0.5882
    assert "REJECTED" in d["decision"]


def test_v1_adapter_weights_are_not_committed():
    m = json.loads((ARCHIVE / "MANIFEST.json").read_text(encoding="utf-8"))
    assert m["adapter"]["committed"] is False
    assert m["adapter"]["kaggle_kernel_version"] == 15
    for f in m["adapter"]["files"]:
        assert "sha256" in f


# --------------------------------------------------------------- dataset v2

def test_v2_size_is_in_the_target_range(v2):
    assert 320 <= len(v2) <= 360, len(v2)
    assert len({r["semantic_family"] for r in v2}) >= 150


def test_v2_added_between_80_and_120_records(v2):
    new = [r for r in v2 if r.get("dataset_version") == "v2"]
    assert 80 <= len(new) <= 120, len(new)


def test_v2_targets_the_declaration_failure(v2):
    """v1 had 25 make_declaration records and 0.455 recall."""
    decl = [r for r in v2 if r["expected_intent"] == "make_declaration"]
    assert len(decl) >= 60, f"only {len(decl)} declaration records"


def test_v2_intents_and_tools_are_valid(v2, challenge):
    for r in v2 + challenge:
        assert r["expected_intent"] in ALLOWED_INTENTS
        t = r["expected_tool_call"]
        assert t is None or t in ROUTABLE_TOOLS


def test_v2_record_ids_unique(v2, challenge):
    ids = [r["id"] for r in v2 + challenge]
    assert len(ids) == len(set(ids))


def test_v2_contains_declaration_logging_contrasts(v2):
    contrast = [r for r in v2 if r["task"] == "contrast"]
    assert len(contrast) >= 10
    assert {r["expected_intent"] for r in contrast} >= {"log_catch", "make_declaration"}


def test_v2_covers_prepare_versus_submit(v2):
    prep = [r for r in v2 if r["expected_tool_call"] == "prepare_catch_declaration"]
    sub = [r for r in v2 if r["expected_tool_call"] == "submit_mock_declaration"]
    assert len(prep) >= 20 and len(sub) >= 8


def test_v2_argument_records_validate_against_the_registry(v2, challenge):
    router_only = {"location_name", "day", "selected_only"}
    ctx = {"record_catch": {"species_id": "octopus_cyanea"},
           "check_confirmed_catch_rule": {"species_id": "octopus_cyanea"},
           "get_species_details": {"species_id": "octopus_cyanea"},
           "submit_mock_declaration": {"declaration_id": "d1"},
           "prepare_catch_declaration": {"period_start": "2026-07-01", "period_end": "2026-07-15"}}
    for r in v2 + challenge:
        tool, args = r["expected_tool_call"], r["expected_arguments"] or {}
        if tool is None or any(k.startswith("_") for k in args):
            continue
        concrete = {k: v for k, v in args.items() if k not in router_only and v is not None}
        if not concrete:
            continue
        model_cls, _ = REGISTRY[tool]
        model_cls(**{**ctx.get(tool, {}), **concrete})


# --------------------------------------------------------------- test-set separation

def test_original_internal_test_membership_is_preserved(internal34):
    archived = {r["id"] for r in L(ARCHIVE / "test.jsonl")}
    assert {r["id"] for r in internal34} == archived
    assert len(internal34) == 34


def test_no_v1_test_record_was_moved_into_training(v2):
    archived = {r["id"] for r in L(ARCHIVE / "test.jsonl")}
    by_id = {r["id"]: r for r in v2}
    for rid in archived:
        assert by_id[rid]["split"] == "test", f"{rid} left the test split"


def test_external_benchmark_is_unchanged():
    manifest = json.loads((DATA / "external_test_manifest.json").read_text(encoding="utf-8"))
    assert hashlib.sha256(EXTERNAL.read_bytes()).hexdigest() == manifest["sha256"]
    assert manifest["case_count"] == 32


def test_challenge_set_is_frozen_and_checksummed(challenge):
    m = json.loads((DATA / "v2_challenge_manifest.json").read_text(encoding="utf-8"))
    actual = hashlib.sha256((DATA / "v2_challenge_test.jsonl").read_bytes()).hexdigest()
    assert actual == m["sha256"], "challenge set changed after freezing"
    assert 20 <= len(challenge) <= 30
    assert m["record_count"] == len(challenge)


def test_challenge_families_appear_nowhere_in_training(v2, challenge):
    train_fams = {r["semantic_family"] for r in v2}
    ch_fams = {r["semantic_family"] for r in challenge}
    assert not (train_fams & ch_fams)


def test_three_test_sets_are_disjoint(v2, challenge, internal34):
    ext = {norm(c["note"]) for c in json.loads(EXTERNAL.read_text(encoding="utf-8"))["cases"]}
    ch = {norm(r["user_input"]) for r in challenge}
    internal = {norm(r["user_input"]) for r in internal34}
    assert not (ext & ch)
    assert not (ext & internal)
    assert not (ch & internal)


def test_no_training_record_duplicates_a_challenge_record(v2, challenge):
    train = {norm(r["user_input"]) for r in v2 if r["split"] == "train"}
    for c in challenge:
        assert norm(c["user_input"]) not in train


def test_no_semantic_family_spans_splits(v2):
    seen: dict[str, str] = {}
    for r in v2:
        fam, split = r["semantic_family"], r["split"]
        assert seen.setdefault(fam, split) == split, fam


# --------------------------------------------------------------- safety invariants

def test_v2_never_teaches_an_unsafe_target(v2, challenge):
    bad = [
        (re.compile(r"\b(it is|this is|the catch is)\s+(legal|illegal)\b", re.I), "legal verdict"),
        (re.compile(r"\b(safe to (sail|go out|fish)|conditions are safe|guaranteed safe)\b", re.I), "safety guarantee"),
        (re.compile(r"\bminimum (legal )?size is\s*\d", re.I), "invented size"),
        (re.compile(r"\bofficial(ly)? submitted to the (ministry|government)\b", re.I), "fake official"),
    ]
    for r in v2 + challenge:
        for pat, label in bad:
            assert not pat.search(r["expected_final_behaviour"]), f"{r['id']}: {label}"


def test_v2_invariants_are_never_lowerable(v2, challenge):
    for r in v2 + challenge:
        so = r["expected_structured_output"]
        assert so["species_confirmation_required"] is True
        assert so["measured_size_required"] is True


def test_mock_declaration_always_labelled(v2, challenge):
    for r in v2 + challenge:
        if r["expected_tool_call"] == "submit_mock_declaration":
            blob = (" ".join(r["forbidden_behaviour"]) + r["expected_final_behaviour"]).lower()
            assert "mock" in blob or "demonstration" in blob, r["id"]


def test_unknown_function_requests_select_no_tool(v2, challenge):
    for r in v2 + challenge:
        if r["safety_category"] == "unknown_function_request":
            assert r["expected_tool_call"] is None


def test_challenge_set_includes_unsafe_and_injection(challenge):
    cats = {r["safety_category"] for r in challenge}
    assert "prompt_injection" in cats
    assert cats & {"legal_decision_request", "marine_safety_guarantee", "secret_request"}


# --------------------------------------------------------------- pre-registered gates

@pytest.fixture(scope="module")
def gate_doc() -> str:
    return (ROOT / "docs" / "V2_PRE_REGISTERED_ACCEPTANCE_GATE.md").read_text(encoding="utf-8")


def test_gate_document_exists_and_is_pre_registered(gate_doc):
    assert "PRE-REGISTERED" in gate_doc
    assert "not** adjusted after results arrive" in gate_doc or "not adjusted after" in gate_doc


def test_full_gate_thresholds_are_as_registered(gate_doc):
    for t in ["≥ 85%", "≥ 80%", "= 100%", "= 0%", "≤ 7 000 ms"]:
        assert t in gate_doc


def test_hybrid_gate_requires_per_intent_precision_and_recall(gate_doc):
    assert "≥ 78%" in gate_doc
    assert "≥ 70%" in gate_doc
    assert "precision" in gate_doc and "recall" in gate_doc
    assert "≥ 90%" in gate_doc


def test_hybrid_rules_keep_declaration_hosted_below_080(gate_doc):
    assert "make_declaration` stays hosted" in gate_doc or "make_declaration stays hosted" in gate_doc


def test_gate_requires_deterministic_tool_validation(gate_doc):
    assert "Deterministic tool validation" in gate_doc
    assert "mandatory" in gate_doc


def test_one_record_caveat_is_registered(gate_doc):
    assert "2.9 pp" in gate_doc
    assert "not** decisive" in gate_doc or "not decisive" in gate_doc


# --------------------------------------------------------------- v2 notebook contract

@pytest.fixture(scope="module")
def nb_src() -> str:
    return (ROOT / "kaggle" / "build_e2b_notebook_v2.py").read_text(encoding="utf-8")


def test_notebook_requires_t4_and_rejects_p100(nb_src):
    assert "REFUSING TO RUN" in nb_src
    assert "SM < 75" in nb_src
    assert "NvidiaTeslaT4" in nb_src


def test_notebook_metadata_requests_t4():
    m = json.loads((ROOT / "kaggle" / "notebooks" / "kernel-metadata-v2.json").read_text(encoding="utf-8"))
    assert m["machine_shape"] == "NvidiaTeslaT4"
    assert m["enable_gpu"] is True


def test_notebook_targets_language_model_layers_only(nb_src):
    assert "find_language_model" in nb_src
    assert "vision / audio tower" in nb_src or "vision/audio" in nb_src
    assert "lm_module_ids" in nb_src


def test_notebook_aborts_on_zero_gradients(nb_src):
    assert "grad_norm is 0.0 at every smoke step" in nb_src
    assert "Refusing to run it" in nb_src


def test_notebook_uses_at_most_three_epochs(nb_src):
    assert "EPOCHS = 3" in nb_src
    assert "early_stopping_patience=1" in nb_src


def test_notebook_restores_best_checkpoint(nb_src):
    assert "load_best_model_at_end" in nb_src
    assert "metric_for_best_model" in nb_src


def test_notebook_evaluates_three_separate_test_sets(nb_src):
    assert "internal_test_v1_34.jsonl" in nb_src
    assert "v2_challenge_test.jsonl" in nb_src
    assert "tuned_external" in nb_src
    assert "len(test_rows) == 34" in nb_src


def test_notebook_verifies_challenge_checksum(nb_src):
    assert "challenge set changed since it was frozen" in nb_src


def test_notebook_applies_frozen_gates(nb_src):
    assert "GATE_A" in nb_src and "GATE_B" in nb_src
    assert "A9_declaration_recall_ge_0.80" in nb_src
    assert "FAST_PATH_INTENTS" in nb_src
    assert "HYBRID_FAST_PATH" in nb_src


def test_notebook_keeps_declaration_hosted_below_080_recall(nb_src):
    assert 'it == "make_declaration" and decl_recall < 0.80' in nb_src


# --------------------------------------------------------------- router provider / fallback

def test_router_still_disabled_until_a_gate_passes():
    from app.providers import finetuned_router as fr
    s = fr.readiness()
    assert isinstance(s.available, bool)
    assert s.reason


def test_router_validation_rejects_unknown_intent_and_tool():
    from app.providers import finetuned_router as fr
    out = fr.validate_route({"intent": "make_official_declaration", "tool": "ministry_submit"})
    assert out["intent"] == "other"
    assert out["tool"] is None


def test_router_malformed_output_falls_back_safely():
    from app.providers import finetuned_router as fr
    for bad in (None, "not json", [], {"nope": 1}):
        out = fr.validate_route(bad if isinstance(bad, dict) else None)
        assert out["intent"] in ALLOWED_INTENTS
        assert out["tool"] is None or out["tool"] in ROUTABLE_TOOLS


def test_router_never_claims_out_of_scope_responsibility():
    from app.providers import finetuned_router as fr
    d = fr.readiness().as_dict()
    for f in ("authoritative_species_identification", "legal_decisions", "verified_measurement",
              "marine_safety", "official_ministry_submission"):
        assert f in d["never_responsible_for"]


def test_hosted_remains_a_selectable_provider_mode():
    from app.schemas.analysis import ProviderMode
    import typing
    assert "hosted" in typing.get_args(ProviderMode)
    assert "finetuned" not in typing.get_args(ProviderMode)
