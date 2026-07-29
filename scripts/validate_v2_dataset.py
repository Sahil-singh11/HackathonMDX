#!/usr/bin/env python3
"""Full v2 validation: schema, leakage, semantic families, arguments, safety.

Runs every v1 gate against the v2 master, and adds the v2-specific ones:
  - the original 34-record internal test keeps its exact membership
  - the 32-case external benchmark is unchanged
  - the challenge set is frozen, checksum-verified, and its families appear
    nowhere in train/validation/test
  - no training record near-duplicates a challenge record

    python scripts/validate_v2_dataset.py
Exit 0 = pass. Writes the five v2 reports under training/results/.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from difflib import SequenceMatcher
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.prompts.compact_router_v1 import ALLOWED_INTENTS, ROUTABLE_TOOLS  # noqa: E402
from app.tools.registry import REGISTRY  # noqa: E402

DATA = ROOT / "training" / "data"
RESULTS = ROOT / "training" / "results"
EXTERNAL = ROOT / "evaluation" / "cases" / "morisyen_cases.json"
ARCHIVE = ROOT / "training" / "archive" / "v1"

NEAR_DUP = 0.85
EXTERNAL_SIM = 0.80
SHINGLE_N = 4

REQUIRED = ["id", "language", "task", "semantic_family", "provenance", "human_review_status",
            "system_prompt_version", "compact_prompt_version", "user_input", "available_tools",
            "expected_intent", "expected_tool_call", "expected_arguments",
            "expected_structured_output", "expected_final_behaviour", "forbidden_behaviour",
            "safety_category", "source_ids", "split"]

SECRETS = [re.compile(p) for p in
           (r"AIza[0-9A-Za-z_\-]{30,}", r"hf_[A-Za-z0-9]{30,}", r"sk-[A-Za-z0-9]{20,}",
            r"-----BEGIN [A-Z ]*PRIVATE KEY-----")]

UNSAFE_TARGET = [
    (re.compile(r"\b(it is|this is|the catch is)\s+(legal|illegal)\b", re.I), "legal_verdict"),
    (re.compile(r"\bminimum (legal )?size is\s*\d", re.I), "invented_minimum_size"),
    (re.compile(r"\bclosed season (is|runs|starts)\b", re.I), "invented_closed_season"),
    (re.compile(r"\b(safe to (sail|go out|fish)|conditions are safe|guaranteed safe)\b", re.I), "safety_guarantee"),
    (re.compile(r"\b(definitely|certainly) (a|an|the)\b", re.I), "authoritative_identification"),
    (re.compile(r"\bofficial(ly)? submitted to the (ministry|government)\b", re.I), "fake_official"),
    (re.compile(r"\bmeasured length from the (photo|image)\b", re.I), "visual_size"),
]

CONTEXT_SUPPLIED = {
    "record_catch": {"species_id": "octopus_cyanea"},
    "check_confirmed_catch_rule": {"species_id": "octopus_cyanea"},
    "get_species_details": {"species_id": "octopus_cyanea"},
    "submit_mock_declaration": {"declaration_id": "d1"},
    "prepare_catch_declaration": {"period_start": "2026-07-01", "period_end": "2026-07-15"},
}
ROUTER_ONLY = {"location_name", "day", "selected_only"}


def L(p: Path) -> list[dict]:
    return [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]


def norm(t: str) -> str:
    t = t.lower().replace("'", " ").replace("’", " ")
    return " ".join(re.sub(r"[^\w\s]", " ", t).split())


def shingles(t: str, n: int = SHINGLE_N) -> set[str]:
    w = norm(t).split()
    return {" ".join(w[i:i + n]) for i in range(max(0, len(w) - n + 1))}


def write(name: str, payload: dict) -> None:
    RESULTS.mkdir(parents=True, exist_ok=True)
    (RESULTS / name).write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def main() -> int:
    master = L(DATA / "master_records_v2.jsonl")
    challenge = L(DATA / "v2_challenge_test.jsonl")
    internal34 = L(DATA / "internal_test_v1_34.jsonl")
    ext_bytes = EXTERNAL.read_bytes()
    external = json.loads(ext_bytes)["cases"]

    all_fail: dict[str, list[str]] = defaultdict(list)

    # ---------------- 1. schema
    f = all_fail["schema"]
    ids = Counter(r["id"] for r in master + challenge)
    for i, n in ids.items():
        if n > 1:
            f.append(f"duplicate id {i}")
    for r in master + challenge:
        miss = [k for k in REQUIRED if k not in r]
        if miss:
            f.append(f"{r['id']} missing {miss}")
        if r["expected_intent"] not in ALLOWED_INTENTS:
            f.append(f"{r['id']} bad intent {r['expected_intent']!r}")
        t = r["expected_tool_call"]
        if t is not None and t not in ROUTABLE_TOOLS:
            f.append(f"{r['id']} bad tool {t!r}")
        if not r["user_input"].strip():
            f.append(f"{r['id']} empty user_input")
    blob = json.dumps(master + challenge, ensure_ascii=False)
    for pat in SECRETS:
        if pat.search(blob):
            f.append(f"secret pattern {pat.pattern}")
    dupes = [t for t, n in Counter(norm(r["user_input"]) for r in master + challenge).items() if n > 1]
    if dupes:
        f.append(f"{len(dupes)} exact duplicate inputs e.g. {dupes[:2]}")

    write("v2_dataset_validation.json", {
        "total_records": len(master), "challenge_records": len(challenge),
        "semantic_families": len({r["semantic_family"] for r in master}),
        "by_split": dict(Counter(r["split"] for r in master)),
        "by_intent": dict(Counter(r["expected_intent"] for r in master)),
        "by_provenance": dict(Counter(r["provenance"] for r in master)),
        "unique_ids": len(ids), "failures": f, "passed": not f})

    # ---------------- 2. leakage
    f = all_fail["leakage"]
    manifest = json.loads((DATA / "external_test_manifest.json").read_text(encoding="utf-8"))
    if hashlib.sha256(ext_bytes).hexdigest() != manifest["sha256"]:
        f.append("external benchmark CHANGED — it is immutable")

    ch_manifest = json.loads((DATA / "v2_challenge_manifest.json").read_text(encoding="utf-8"))
    if hashlib.sha256((DATA / "v2_challenge_test.jsonl").read_bytes()).hexdigest() != ch_manifest["sha256"]:
        f.append("challenge set CHANGED since it was frozen")

    ext_pairs = [(c["id"], norm(c["note"]), shingles(c["note"])) for c in external]
    for r in master:
        rn, rs = norm(r["user_input"]), shingles(r["user_input"])
        for cid, cn, cs in ext_pairs:
            if rn == cn:
                f.append(f"{r['id']} copies external {cid}")
            elif SequenceMatcher(None, rn, cn).ratio() >= EXTERNAL_SIM:
                f.append(f"{r['id']} ~similar to external {cid}")
            elif rs & cs:
                f.append(f"{r['id']} shares {SHINGLE_N}-word run with external {cid}: {sorted(rs & cs)[:1]}")

    ch_pairs = [(c["id"], norm(c["user_input"]), shingles(c["user_input"])) for c in challenge]
    for r in master:
        rn, rs = norm(r["user_input"]), shingles(r["user_input"])
        for cid, cn, cs in ch_pairs:
            if rn == cn:
                f.append(f"{r['id']} copies challenge {cid}")
            elif SequenceMatcher(None, rn, cn).ratio() >= NEAR_DUP:
                f.append(f"{r['id']} near-duplicates challenge {cid}")

    by_split: dict[str, list[dict]] = defaultdict(list)
    for r in master:
        by_split[r["split"]].append(r)
    names = sorted(by_split)
    borderline = 0
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            for ra in by_split[a]:
                na = norm(ra["user_input"])
                for rb in by_split[b]:
                    ratio = SequenceMatcher(None, na, norm(rb["user_input"])).ratio()
                    if ratio >= NEAR_DUP:
                        f.append(f"near-dup across splits {ra['id']}({a}) / {rb['id']}({b}) {ratio:.2f}")
                    elif ratio >= 0.75:
                        borderline += 1

    arch_test = {r["id"] for r in L(ARCHIVE / "test.jsonl")}
    cur_test = {r["id"] for r in master if r["split"] == "test"}
    if not arch_test <= cur_test:
        f.append(f"v1 test records moved out of test: {sorted(arch_test - cur_test)[:5]}")
    if {r["id"] for r in internal34} != arch_test:
        f.append("internal_test_v1_34.jsonl does not match the archived v1 test set")

    write("v2_leakage_report.json", {
        "external_sha256_matches": hashlib.sha256(ext_bytes).hexdigest() == manifest["sha256"],
        "challenge_sha256_matches": hashlib.sha256((DATA / "v2_challenge_test.jsonl").read_bytes()).hexdigest() == ch_manifest["sha256"],
        "v1_internal_test_preserved": arch_test <= cur_test,
        "v1_internal_test_size": len(arch_test),
        "comparisons_vs_external": len(master) * len(external),
        "comparisons_vs_challenge": len(master) * len(challenge),
        "borderline_cross_split": borderline,
        "failures": f, "passed": not f})

    # ---------------- 3. semantic families
    f = all_fail["families"]
    fam_split: dict[str, set] = defaultdict(set)
    for r in master:
        fam_split[r["semantic_family"]].add(r["split"])
    for fam, s in fam_split.items():
        if len(s) > 1:
            f.append(f"family {fam} spans {sorted(s)}")
    ch_fams = {r["semantic_family"] for r in challenge}
    train_fams = set(fam_split)
    if ch_fams & train_fams:
        f.append(f"challenge families in training: {sorted(ch_fams & train_fams)}")
    write("v2_semantic_split_report.json", {
        "families": len(fam_split), "challenge_families": len(ch_fams),
        "family_split_overlap": sorted(ch_fams & train_fams),
        "by_split_intent": {s: dict(Counter(r["expected_intent"] for r in rows))
                            for s, rows in by_split.items()},
        "failures": f, "passed": not f})

    # ---------------- 4. arguments
    f = all_fail["arguments"]
    validated = negative = 0
    for r in master + challenge:
        tool, args = r["expected_tool_call"], r["expected_arguments"] or {}
        if tool is None:
            if args and not any(k.startswith("_") for k in args):
                f.append(f"{r['id']} has arguments but no tool")
            continue
        if tool not in REGISTRY:
            f.append(f"{r['id']} unknown tool {tool!r}")
            continue
        if any(k.startswith("_") for k in args):
            negative += 1
            continue
        concrete = {k: v for k, v in args.items() if k not in ROUTER_ONLY and v is not None}
        if not concrete:
            continue
        model_cls, _ = REGISTRY[tool]
        try:
            model_cls(**{**CONTEXT_SUPPLIED.get(tool, {}), **concrete})
            validated += 1
        except Exception as e:  # noqa: BLE001
            f.append(f"{r['id']} args rejected by {tool}: {type(e).__name__}")
    write("v2_argument_validation.json", {
        "argument_sets_validated": validated, "negative_cases": negative,
        "by_tool": dict(Counter(r["expected_tool_call"] or "(none)" for r in master)),
        "failures": f, "passed": not f})

    # ---------------- 5. safety
    f = all_fail["safety"]
    for r in master + challenge:
        target = r["expected_final_behaviour"] + json.dumps(r["expected_structured_output"])
        for pat, label in UNSAFE_TARGET:
            if pat.search(target):
                f.append(f"{r['id']} unsafe target ({label})")
        so = r["expected_structured_output"]
        if so.get("species_confirmation_required") is not True:
            f.append(f"{r['id']} confirmation not required")
        if so.get("measured_size_required") is not True:
            f.append(f"{r['id']} measured size not required")
        if r["safety_category"] != "none" and not r["forbidden_behaviour"]:
            f.append(f"{r['id']} safety record without forbidden_behaviour")
        if r["safety_category"] == "unknown_function_request" and r["expected_tool_call"] is not None:
            f.append(f"{r['id']} unknown-function request selects a tool")
        if r["expected_tool_call"] == "submit_mock_declaration":
            b = (" ".join(r["forbidden_behaviour"]) + r["expected_final_behaviour"]).lower()
            if "mock" not in b and "demonstration" not in b:
                f.append(f"{r['id']} mock submission not labelled")
    safety_records = [r for r in master + challenge if r["safety_category"] != "none"]
    write("v2_safety_validation.json", {
        "safety_records": len(safety_records),
        "by_category": dict(Counter(r["safety_category"] for r in master + challenge)),
        "unreviewed_safety_records": sum(1 for r in safety_records
                                         if r["human_review_status"] == "pending"),
        "failures": f, "passed": not f})

    # ---------------- summary
    total = sum(len(v) for v in all_fail.values())
    for name, fails in all_fail.items():
        status = "PASS" if not fails else f"FAIL ({len(fails)})"
        print(f"  {name:12} {status}")
        for x in fails[:5]:
            print(f"      {x}")
    print(f"\nv2 records {len(master)} | challenge {len(challenge)} | internal-34 pinned "
          f"{len(internal34)} | external {len(external)}")
    print("ALL PASS" if not total else f"FAILURES: {total}")
    return 0 if not total else 1


if __name__ == "__main__":
    sys.exit(main())
