#!/usr/bin/env python3
"""Freeze the exact Step-3 (v1) artifacts before v2 work begins.

Copies the v1 files as they were at commit `6aa1153`/`2715a34` into
training/archive/v1/, writes a MANIFEST.json describing each one, and a
CHECKSUMS.sha256 that can be verified later.

The 32-case external benchmark is NOT copied into the archive as a mutable file —
it is checksummed in place, because it must stay exactly where it is.

Adapter weights (17.7 MB) are excluded by repository policy; their location and
SHA-256 are recorded instead.

    python training/scripts/freeze_v1_archive.py
"""
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ARCHIVE = ROOT / "training" / "archive" / "v1"

# The commit at which the v1 dataset was created (pre-review).
V1_DATA_COMMIT = "6aa1153"
# The commit carrying the v1 training results.
V1_RESULTS_COMMIT = "2715a34"

# (archive name, git ref, repo path)  -- pulled from git so later edits cannot contaminate.
FROM_GIT = [
    ("master_records.jsonl", V1_DATA_COMMIT, "training/data/master_records.jsonl"),
    ("train.jsonl", V1_DATA_COMMIT, "training/data/train.jsonl"),
    ("validation.jsonl", V1_DATA_COMMIT, "training/data/validation.jsonl"),
    ("test.jsonl", V1_DATA_COMMIT, "training/data/test.jsonl"),
    ("dataset_statistics.json", V1_DATA_COMMIT, "training/data/dataset_statistics.json"),
    ("external_test_manifest.json", V1_DATA_COMMIT, "training/data/external_test_manifest.json"),
    ("compact_router_v1.json", V1_DATA_COMMIT, "training/configs/compact_router_v1.json"),
]

# Copied from the working tree (they are v1 results and are not edited by v2).
FROM_TREE = [
    ("train_lamer_konekte_e2b_qlora_v1.ipynb", "kaggle/notebooks/train_lamer_konekte_e2b_qlora.ipynb"),
    ("training_metrics.json", "training/results/training_metrics.json"),
    ("evaluation_metrics.json", "training/results/evaluation_metrics.json"),
    ("training_history.csv", "training/results/training_history.csv"),
    ("e2b_comparison.csv", "training/results/e2b_comparison.csv"),
    ("error_analysis.csv", "training/results/error_analysis.csv"),
    ("E2B_ADAPTER_MODEL_CARD.md", "training/results/E2B_ADAPTER_MODEL_CARD.md"),
]

# Checksummed in place — never moved, never rewritten.
IN_PLACE = [
    ("external_benchmark", "evaluation/cases/morisyen_cases.json"),
    ("compact_router_prompt_module", "backend/app/prompts/compact_router_v1.py"),
]

ADAPTER_DIR = ROOT / "kaggle" / "outputs" / "e2b_router" / "e2b_router_adapter"


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def git_show(ref: str, path: str) -> bytes:
    return subprocess.run(["git", "show", f"{ref}:{path}"], cwd=ROOT,
                          capture_output=True, check=True).stdout


def main() -> int:
    ARCHIVE.mkdir(parents=True, exist_ok=True)
    entries: list[dict] = []

    for name, ref, path in FROM_GIT:
        data = git_show(ref, path)
        dest = ARCHIVE / name
        dest.write_bytes(data)
        entries.append({"archived_as": name, "source": path, "from_git_ref": ref,
                        "bytes": len(data), "sha256": sha256_bytes(data)})
        print(f"  archived {name:44} ({len(data):>7} B) from {ref}")

    for name, path in FROM_TREE:
        src = ROOT / path
        if not src.exists():
            print(f"  MISSING  {path} — skipped")
            continue
        dest = ARCHIVE / name
        shutil.copy2(src, dest)
        entries.append({"archived_as": name, "source": path, "from_git_ref": "working_tree",
                        "bytes": dest.stat().st_size, "sha256": sha256_file(dest)})
        print(f"  archived {name:44} ({dest.stat().st_size:>7} B) from working tree")

    in_place = []
    for label, path in IN_PLACE:
        p = ROOT / path
        in_place.append({"label": label, "path": path, "bytes": p.stat().st_size,
                         "sha256": sha256_file(p),
                         "note": "checksummed IN PLACE — must not be moved or rewritten"})
        print(f"  in-place {label:44} {sha256_file(p)[:16]}")

    # Adapter weights: recorded, not committed.
    adapter = {"committed": False,
               "reason": "repository policy excludes adapter weights (kaggle/outputs is gitignored)",
               "local_path": str(ADAPTER_DIR.relative_to(ROOT)) if ADAPTER_DIR.exists() else None,
               "kaggle_kernel": "yuvineappadu/lamer-konekte-e2b-qlora-router",
               "kaggle_kernel_version": 15,
               "files": []}
    if ADAPTER_DIR.exists():
        for f in sorted(ADAPTER_DIR.rglob("*")):
            if f.is_file():
                adapter["files"].append({"file": str(f.relative_to(ADAPTER_DIR)),
                                         "bytes": f.stat().st_size, "sha256": sha256_file(f)})
        print(f"  adapter recorded: {len(adapter['files'])} files (weights NOT committed)")

    v1_metrics = json.loads((ROOT / "training" / "results" / "evaluation_metrics.json")
                            .read_text(encoding="utf-8"))
    manifest = {
        "version": "v1",
        "frozen_on": date.today().isoformat(),
        "purpose": ("Immutable snapshot of the Step-3 dataset, prompt, notebook, configuration "
                    "and results, taken before dataset v2 was created."),
        "data_commit": V1_DATA_COMMIT,
        "results_commit": V1_RESULTS_COMMIT,
        "base_model": "google/gemma-4-E2B-it",
        "archived_files": entries,
        "checksummed_in_place": in_place,
        "adapter": adapter,
        "step3_acceptance_decision": {
            "accepted": False,
            "gate": v1_metrics.get("acceptance_gate"),
            "internal_intent_accuracy": (v1_metrics.get("tuned_internal") or {}).get("intent_accuracy"),
            "internal_tool_accuracy": (v1_metrics.get("tuned_internal") or {}).get("tool_accuracy"),
            "external_intent_accuracy": (v1_metrics.get("tuned_external") or {}).get("intent_accuracy"),
            "decision": ("REJECTED — intent 73.5% and tool 58.8% were below the 90% threshold. "
                         "Hosted gemma-4-26b-a4b-it remained production and "
                         "FineTunedE2BRouterProvider stayed disabled."),
        },
        "immutability_rules": [
            "the 32-case external benchmark is never moved, edited or paraphrased",
            "the 34-record internal test keeps its exact membership in v2",
            "no failed test example is moved into training",
            "v1 results are never retroactively edited",
        ],
    }
    (ARCHIVE / "MANIFEST.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False),
                                           encoding="utf-8")

    lines = []
    for e in entries:
        lines.append(f"{e['sha256']}  {e['archived_as']}")
    for e in in_place:
        lines.append(f"{e['sha256']}  ../../../{e['path']}")
    (ARCHIVE / "CHECKSUMS.sha256").write_text("\n".join(sorted(lines)) + "\n", encoding="utf-8")

    print(f"\nfrozen {len(entries)} files + {len(in_place)} in-place checksums -> "
          f"{ARCHIVE.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
