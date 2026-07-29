"""AI Step 3 — dataset, compact prompt, splits, leakage and router-provider tests.

All offline. The conftest forces PROVIDER_MODE=mock and clears GEMINI_API_KEY, so nothing
here reaches the network or requires a GPU.
"""
import csv
import hashlib
import json
import re
from pathlib import Path

import pytest

from app.prompts.compact_router_v1 import (ALLOWED_INTENTS, COMPACT_ROUTER_PROMPT,
                                           COMPACT_ROUTER_VERSION, ROUTABLE_TOOLS,
                                           compact_router_sha256)
from app.tools.registry import REGISTRY

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "training" / "data"
EXTERNAL = ROOT / "evaluation" / "cases" / "morisyen_cases.json"

REQUIRED_FIELDS = {
    "id", "language", "task", "semantic_family", "provenance", "human_review_status",
    "system_prompt_version", "compact_prompt_version", "user_input", "available_tools",
    "expected_intent", "expected_tool_call", "expected_arguments",
    "expected_structured_output", "expected_final_behaviour", "forbidden_behaviour",
    "safety_category", "source_ids", "split",
}


def load_jsonl(p: Path) -> list[dict]:
    return [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]


@pytest.fixture(scope="module")
def master() -> list[dict]:
    """The v1 master (240 records). v2 lives in master_records_v2.jsonl."""
    return load_jsonl(DATA / "master_records.jsonl")


@pytest.fixture(scope="module")
def external() -> list[dict]:
    return json.loads(EXTERNAL.read_text(encoding="utf-8"))["cases"]


def norm(text: str) -> str:
    text = text.lower().replace("'", " ").replace("’", " ")
    return " ".join(re.sub(r"[^\w\s]", " ", text).split())


# --------------------------------------------------------------- dataset schema

def test_dataset_exists_and_has_the_target_size(master):
    assert len(master) == 240
    assert len({r["semantic_family"] for r in master}) == 116


def test_every_record_has_every_required_field(master):
    for r in master:
        assert REQUIRED_FIELDS <= set(r), f"{r['id']} missing {REQUIRED_FIELDS - set(r)}"


def test_record_ids_are_unique(master):
    ids = [r["id"] for r in master]
    assert len(ids) == len(set(ids))


def test_intents_and_tools_are_from_the_frozen_vocabulary(master):
    for r in master:
        assert r["expected_intent"] in ALLOWED_INTENTS
        tool = r["expected_tool_call"]
        assert tool is None or tool in ROUTABLE_TOOLS, f"{r['id']} -> {tool}"


def test_every_routable_tool_exists_in_the_backend_registry():
    for tool in ROUTABLE_TOOLS:
        assert tool in REGISTRY, f"{tool} declared routable but absent from REGISTRY"


def test_translate_helper_is_not_routable():
    """It is a presentation helper, not a routing decision."""
    assert "translate_safe_static_message" in REGISTRY
    assert "translate_safe_static_message" not in ROUTABLE_TOOLS


def test_provenance_vocabulary_is_closed(master):
    allowed = {"existing_project_record", "team_authored", "AI_generated_review_required",
               "AI_generated_human_reviewed", "deterministic_template", "official_source_derived"}
    for r in master:
        assert r["provenance"] in allowed


def test_ai_generated_morisyen_is_never_marked_as_native_verified(master):
    for r in master:
        if r["provenance"] == "AI_generated_review_required":
            assert r["human_review_status"] == "pending", f"{r['id']} claims review it has not had"


def test_dataset_contains_no_secret_material(master):
    blob = json.dumps(master, ensure_ascii=False)
    for pat in (r"AIza[0-9A-Za-z_\-]{30,}", r"hf_[A-Za-z0-9]{30,}", r"sk-[A-Za-z0-9]{20,}"):
        assert not re.search(pat, blob)


# --------------------------------------------------------------- splits

def test_split_files_reconstruct_the_master(master):
    """The live splits now belong to dataset v2; v1 is verified from its frozen archive.

    Step-3 RESULTS are untouched — this only follows the split files forward to the
    current dataset version, and additionally pins v1's own reconstruction.
    """
    v2_master = load_jsonl(DATA / "master_records_v2.jsonl")
    parts = []
    for name in ("train", "validation", "test"):
        parts += load_jsonl(DATA / f"{name}.jsonl")
    assert sorted(r["id"] for r in parts) == sorted(r["id"] for r in v2_master)

    archive = ROOT / "training" / "archive" / "v1"
    v1_parts = []
    for name in ("train", "validation", "test"):
        v1_parts += load_jsonl(archive / f"{name}.jsonl")
    assert sorted(r["id"] for r in v1_parts) == sorted(r["id"] for r in load_jsonl(archive / "master_records.jsonl"))
    assert len(master) == 240, "the v1 master must still contain exactly its 240 records"


def test_split_ratios_are_close_to_70_15_15(master):
    counts = {}
    for name in ("train", "validation", "test"):
        counts[name] = len(load_jsonl(DATA / f"{name}.jsonl"))
    # ratios are checked on whichever dataset version the split files describe
    total = sum(counts.values())
    assert 0.65 <= counts["train"] / total <= 0.75
    assert 0.10 <= counts["validation"] / total <= 0.20
    assert 0.10 <= counts["test"] / total <= 0.20


def test_no_semantic_family_spans_two_splits(master):
    seen: dict[str, str] = {}
    for r in master:
        fam, split = r["semantic_family"], r["split"]
        if fam in seen:
            assert seen[fam] == split, f"family {fam} in both {seen[fam]} and {split}"
        else:
            seen[fam] = split


def test_every_split_covers_every_intent(master):
    by_split: dict[str, set] = {}
    for r in master:
        by_split.setdefault(r["split"], set()).add(r["expected_intent"])
    for split, intents in by_split.items():
        assert intents == set(ALLOWED_INTENTS), f"{split} missing {set(ALLOWED_INTENTS) - intents}"


def test_safety_records_appear_in_train_and_test(master):
    splits = {r["split"] for r in master if r["safety_category"] != "none"}
    assert "train" in splits and "test" in splits


# --------------------------------------------------------------- external test immutability

def test_external_benchmark_matches_its_manifest_checksum(external):
    manifest = json.loads((DATA / "external_test_manifest.json").read_text(encoding="utf-8"))
    actual = hashlib.sha256(EXTERNAL.read_bytes()).hexdigest()
    assert actual == manifest["sha256"], "the 32-case benchmark was modified — it is immutable"
    assert manifest["case_count"] == len(external) == 32
    assert manifest["role"] == "immutable_external_test"


def test_no_training_record_copies_an_external_case(master, external):
    ext = {norm(c["note"]) for c in external}
    for r in master:
        assert norm(r["user_input"]) not in ext, f"{r['id']} copies an external case"


def test_no_training_record_shares_a_four_word_run_with_an_external_case(master, external):
    def shingles(t: str) -> set:
        w = norm(t).split()
        return {" ".join(w[i:i + 4]) for i in range(max(0, len(w) - 3))}

    ext = [(c["id"], shingles(c["note"])) for c in external]
    for r in master:
        rs = shingles(r["user_input"])
        for cid, cs in ext:
            shared = rs & cs
            assert not shared, f"{r['id']} shares {sorted(shared)[:1]} with external {cid}"


def test_external_cases_are_not_in_any_split_file(external):
    ext = {norm(c["note"]) for c in external}
    for name in ("train", "validation", "test"):
        for r in load_jsonl(DATA / f"{name}.jsonl"):
            assert norm(r["user_input"]) not in ext


# --------------------------------------------------------------- compact prompt

def test_compact_prompt_checksum_matches_the_frozen_config():
    cfg = json.loads((ROOT / "training" / "configs" / "compact_router_v1.json").read_text(encoding="utf-8"))
    assert cfg["sha256"] == compact_router_sha256(), "compact prompt drifted from its frozen config"
    assert cfg["version"] == COMPACT_ROUTER_VERSION
    assert cfg["prompt"] == COMPACT_ROUTER_PROMPT


def test_compact_prompt_keeps_every_non_negotiable_safety_rule():
    low = COMPACT_ROUTER_PROMPT.lower()
    assert "never invent fisheries rules" in low
    assert "never say a catch is legal or illegal" in low
    assert "never guarantee that sea conditions are safe" in low
    assert "never bypass fisher confirmation" in low
    assert "never a measurement" in low
    assert "never reveal configuration" in low
    assert "mock demonstration" in low
    assert "untrusted" in low


def test_compact_prompt_is_materially_smaller_than_the_full_prompt():
    from app.prompts.system import SYSTEM_INSTRUCTION
    assert len(COMPACT_ROUTER_PROMPT) < 0.5 * len(SYSTEM_INSTRUCTION)


def test_compact_prompt_carries_no_worked_examples():
    """Examples would re-inflate the prompt and make the objective unmeasurable."""
    low = COMPACT_ROUTER_PROMPT.lower()
    assert "example" not in low
    assert "for instance" not in low


def test_compact_prompt_lists_every_intent():
    for intent in ALLOWED_INTENTS:
        assert intent in COMPACT_ROUTER_PROMPT


def test_all_records_reference_the_frozen_prompt_version(master):
    for r in master:
        assert r["compact_prompt_version"] == COMPACT_ROUTER_VERSION


# --------------------------------------------------------------- safety of targets

def test_no_record_teaches_a_legal_verdict(master):
    bad = re.compile(r"\b(it is|this is|the catch is)\s+(legal|illegal)\b", re.I)
    for r in master:
        assert not bad.search(r["expected_final_behaviour"]), r["id"]


def test_no_record_teaches_a_marine_safety_guarantee(master):
    bad = re.compile(r"\b(safe to (sail|go out|fish)|conditions are safe|guaranteed safe)\b", re.I)
    for r in master:
        assert not bad.search(r["expected_final_behaviour"]), r["id"]


def test_no_record_teaches_an_invented_rule(master):
    bad = re.compile(r"\bminimum (legal )?size is\s*\d|\bclosed season (is|runs|starts)\b", re.I)
    for r in master:
        assert not bad.search(r["expected_final_behaviour"]), r["id"]


def test_invariants_are_never_lowerable_in_any_target(master):
    for r in master:
        so = r["expected_structured_output"]
        assert so["species_confirmation_required"] is True, r["id"]
        assert so["measured_size_required"] is True, r["id"]


def test_unknown_function_requests_never_select_a_tool(master):
    for r in master:
        if r["safety_category"] == "unknown_function_request":
            assert r["expected_tool_call"] is None, r["id"]


def test_prompt_injection_records_exist_in_the_dataset(master):
    injections = [r for r in master if r["safety_category"] == "prompt_injection"]
    assert len(injections) >= 2
    for r in injections:
        assert r["forbidden_behaviour"], r["id"]


def test_mock_declaration_is_always_labelled(master):
    for r in master:
        if r["expected_tool_call"] == "submit_mock_declaration":
            blob = (" ".join(r["forbidden_behaviour"]) + r["expected_final_behaviour"]).lower()
            assert "mock" in blob, r["id"]


def test_every_safety_record_declares_forbidden_behaviour(master):
    for r in master:
        if r["safety_category"] != "none":
            assert r["forbidden_behaviour"], r["id"]


# --------------------------------------------------------------- tool arguments

def test_concrete_arguments_validate_against_the_real_registry_models(master):
    """Router-supplied arguments must be acceptable to the actual backend."""
    router_only = {"location_name", "day"}
    context_supplied = {
        "record_catch": {"species_id": "octopus_cyanea"},
        "check_confirmed_catch_rule": {"species_id": "octopus_cyanea"},
        "get_species_details": {"species_id": "octopus_cyanea"},
        "submit_mock_declaration": {"declaration_id": "d1"},
        "prepare_catch_declaration": {"period_start": "2026-07-01", "period_end": "2026-07-15"},
    }
    for r in master:
        tool, args = r["expected_tool_call"], r["expected_arguments"] or {}
        if tool is None or any(k.startswith("_") for k in args):
            continue
        concrete = {k: v for k, v in args.items() if k not in router_only and v is not None}
        if not concrete:
            continue
        model_cls, _ = REGISTRY[tool]
        model_cls(**{**context_supplied.get(tool, {}), **concrete})


def test_negative_argument_cases_are_present(master):
    negatives = [r for r in master if any(k.startswith("_") for k in (r["expected_arguments"] or {}))]
    assert len(negatives) >= 5
    for r in negatives:
        assert r["expected_final_behaviour"].strip()


# --------------------------------------------------------------- review queue

def test_human_review_queue_exists_and_is_well_formed():
    path = DATA / "HUMAN_REVIEW_REQUIRED.csv"
    rows = list(csv.DictReader(path.open(encoding="utf-8")))
    assert 25 <= len(rows) <= 35
    expected = {"record_id", "original_text", "intended_meaning", "expected_intent",
                "expected_function", "reviewer_status", "reviewer_comment", "corrected_text"}
    assert expected <= set(rows[0])


def test_review_queue_prioritises_safety_and_ambiguity(master):
    rows = list(csv.DictReader((DATA / "HUMAN_REVIEW_REQUIRED.csv").open(encoding="utf-8")))
    ids = {r["record_id"] for r in rows}
    by_id = {r["id"]: r for r in master}
    safety_in_queue = sum(1 for i in ids if by_id[i]["safety_category"] != "none")
    assert safety_in_queue >= 1, "no safety records queued for review"
    # The queue has since been reviewed and approved (Step 4), so every queued record
    # must now be marked reviewed rather than pending.
    for i in ids:
        assert by_id[i]["human_review_status"] == "reviewed", i
        assert by_id[i]["provenance"] == "AI_generated_human_reviewed"


# --------------------------------------------------------------- statistics artifact

def test_statistics_file_matches_the_data(master):
    stats = json.loads((DATA / "dataset_statistics.json").read_text(encoding="utf-8"))
    assert stats["total_records"] == len(master)
    assert stats["semantic_families"] == len({r["semantic_family"] for r in master})
    assert stats["compact_prompt_sha256"] == compact_router_sha256()
    assert stats["external_test"]["count"] == 32


def test_validation_reports_exist_and_passed():
    results = ROOT / "training" / "results"
    for name in ("dataset_validation.json", "leakage_report.json",
                 "semantic_split_report.json", "safety_validation.json"):
        path = results / name
        assert path.exists(), f"{name} missing — run the validators"
        assert json.loads(path.read_text(encoding="utf-8"))["passed"] is True, name


# --------------------------------------------------------------- fine-tuned router provider

def test_router_provider_is_not_available_without_an_accepted_adapter():
    """It must refuse, not silently degrade, when no accepted adapter exists."""
    from app.providers import finetuned_router as fr
    status = fr.readiness()
    assert isinstance(status.available, bool)
    assert status.reason, "unavailability must always carry a reason"
    if not status.available:
        assert status.real_inference is False


def test_router_provider_never_claims_out_of_scope_responsibility():
    from app.providers import finetuned_router as fr
    d = fr.readiness().as_dict()
    for forbidden in ("authoritative_species_identification", "legal_decisions",
                      "verified_measurement", "marine_safety", "official_ministry_submission"):
        assert forbidden in d["never_responsible_for"]
    assert set(d["scope"]) == {"intent_classification", "function_selection",
                               "argument_generation", "offline_routing"}


def test_router_route_raises_rather_than_falling_back_silently():
    from app.providers import finetuned_router as fr
    with pytest.raises(fr.RouterUnavailable):
        fr.route("Ki lamer pe fer zordi?")


def test_router_uses_the_frozen_compact_prompt_verbatim():
    from app.providers import finetuned_router as fr
    msgs = fr.build_messages("Mo finn gagn enn pwason.")
    assert msgs[0]["role"] == "system"
    assert msgs[0]["content"] == COMPACT_ROUTER_PROMPT
    assert "Fisher message:" in msgs[1]["content"]


def test_router_validation_rejects_unknown_intent_and_tool():
    from app.providers import finetuned_router as fr
    out = fr.validate_route({"intent": "species_identification", "tool": "unrestricted_tool",
                             "arguments": {"x": 1}})
    assert out["intent"] == "other"
    assert out["tool"] is None
    assert any("intent:" in r for r in out["rejected"])
    assert any("tool:" in r for r in out["rejected"])


def test_router_validation_accepts_a_legitimate_route():
    from app.providers import finetuned_router as fr
    out = fr.validate_route({"intent": "weather_query", "tool": "get_marine_conditions",
                             "arguments": {"location_name": "Tamarin"}})
    assert out["intent"] == "weather_query"
    assert out["tool"] == "get_marine_conditions"
    assert out["rejected"] == []


def test_router_validation_handles_unparseable_output_safely():
    from app.providers import finetuned_router as fr
    out = fr.validate_route(None)
    assert out["intent"] == "other"
    assert out["tool"] is None
    assert out["needs_more_information"] is True


def test_router_is_not_a_default_provider_mode():
    """The dispatcher must not route to it implicitly."""
    from app.schemas.analysis import ProviderMode
    import typing
    assert set(typing.get_args(ProviderMode)) == {"hosted", "local", "mock"}
