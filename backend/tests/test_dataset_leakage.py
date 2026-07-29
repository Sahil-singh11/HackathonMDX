"""Dataset split leakage tests over the image manifest."""
import csv
from collections import defaultdict
from pathlib import Path

MANIFEST = Path(__file__).resolve().parents[2] / "data" / "manifests" / "species_images.csv"
EVAL_SPLITS = {"train", "validation", "test"}


def _rows():
    if not MANIFEST.exists():
        return []
    with open(MANIFEST, newline="") as f:
        return list(csv.DictReader(f))


def test_no_observation_crosses_eval_splits():
    seen: dict[str, set[str]] = defaultdict(set)
    for r in _rows():
        if r["split"] in EVAL_SPLITS and r["observation_id"]:
            seen[r["observation_id"]].add(r["split"])
    offenders = {k: v for k, v in seen.items() if len(v) > 1}
    assert not offenders, f"observations in multiple splits: {offenders}"


def test_no_sha_duplicated_across_eval_splits():
    seen: dict[str, set[str]] = defaultdict(set)
    for r in _rows():
        if r["split"] in EVAL_SPLITS:
            seen[r["sha256"]].add(r["split"])
    offenders = {k: v for k, v in seen.items() if len(v) > 1}
    assert not offenders


def test_only_permitted_media_is_git_trackable():
    import subprocess
    root = MANIFEST.parents[2]
    for r in _rows():
        if r["redistribution_permission"] != "yes":
            chk = subprocess.run(["git", "check-ignore", r["path"]], cwd=root, capture_output=True)
            assert chk.returncode == 0, f"non-redistributable file not ignored: {r['path']}"
