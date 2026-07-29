#!/usr/bin/env python3
"""Real-photo species benchmark for hosted Gemma.

The Morisyen case suite measures intent and safety on synthetic images, so its
"species agreement" number reflects note-grounding, not vision. This script
measures identification on the 60 licensed iNaturalist photos instead:

    backend/.venv/bin/python evaluation/species_benchmark.py            # all splits
    backend/.venv/bin/python evaluation/species_benchmark.py --split test

Metrics: top-1 agreement against the observation's community ID, abstention
rate (species_id null = honest "unsure"), and a false-confident rate (high
confidence + wrong), which matters more than raw accuracy for our safety story.

Results -> evaluation/results/species_benchmark.{json,csv}
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
os.environ.setdefault("DATABASE_URL", f"sqlite:///{ROOT / 'storage' / 'bench.sqlite3'}")

RESULTS = ROOT / "evaluation" / "results"
MANIFEST = ROOT / "data" / "manifests" / "species_images.csv"
EVAL_SPLITS = {"train", "validation", "test"}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", choices=sorted(EVAL_SPLITS) + ["all"], default="all")
    ap.add_argument("--limit", type=int, default=0, help="cap images (0 = no cap)")
    args = ap.parse_args()

    from sqlmodel import Session

    from app.core.config import get_settings
    from app.db.session import get_engine, init_db
    from app.providers import hosted
    from app.services.species.retrieval import load_catalogue, public_candidate
    from app.services.vision.quality import assess
    from app.tools.registry import ToolContext

    if not get_settings().hosted_available:
        print("BLOCKED: GEMINI_API_KEY not configured — this benchmark needs real inference.")
        sys.exit(1)

    init_db()
    candidates = [public_candidate(s) for s in load_catalogue()]

    with open(MANIFEST, newline="") as f:
        rows = [r for r in csv.DictReader(f)
                if r["split"] in (EVAL_SPLITS if args.split == "all" else {args.split})
                and r["species_id"] in {c["species_id"] for c in candidates}]
    if args.limit:
        rows = rows[: args.limit]
    print(f"benchmarking {len(rows)} real photos ({args.split} split) — ~20 s each\n")

    records, latencies = [], []
    with Session(get_engine()) as session:
        ctx = ToolContext(session=session, language="en", allow_network=False)
        for i, r in enumerate(rows, 1):
            path = ROOT / r["path"]
            if not path.exists():
                print(f"  [{i}/{len(rows)}] MISSING {r['path']}")
                continue
            processed = assess(path.read_bytes(), "image/jpeg", get_settings().upload_max_bytes)
            if processed.jpeg_for_api is None:
                print(f"  [{i}/{len(rows)}] quality-gated ({processed.quality.status}) {path.name}")
                records.append({"path": r["path"], "truth": r["species_id"], "predicted": "",
                                "confidence": "", "correct": False, "abstained": False,
                                "quality": processed.quality.status, "latency_ms": 0, "split": r["split"]})
                continue
            try:
                res = hosted.analyse(processed.jpeg_for_api, None, "en", candidates, ctx)
                pred, conf, ms = res.species_id or "", res.confidence_label, res.latency_ms
            except Exception as e:  # noqa: BLE001 — one failure must not lose the run
                print(f"  [{i}/{len(rows)}] ERROR {type(e).__name__}")
                pred, conf, ms = "", "error", 0
            correct = bool(pred) and pred == r["species_id"]
            latencies.append(ms)
            records.append({"path": r["path"], "truth": r["species_id"], "predicted": pred,
                            "confidence": conf, "correct": correct, "abstained": not pred,
                            "quality": processed.quality.status, "latency_ms": ms, "split": r["split"]})
            mark = "OK " if correct else ("-- " if not pred else "XX ")
            print(f"  [{i}/{len(rows)}] {mark} {r['species_id']:22} -> {pred or '(unsure)':22} {conf:6} {ms:6} ms")
            time.sleep(1)  # be polite to the API

    answered = [x for x in records if x["predicted"]]
    correct = [x for x in answered if x["correct"]]
    abstained = [x for x in records if x["abstained"]]
    false_confident = [x for x in answered if not x["correct"] and x["confidence"] == "high"]
    per_species: dict[str, Counter] = defaultdict(Counter)
    for x in records:
        per_species[x["truth"]]["n"] += 1
        per_species[x["truth"]]["correct"] += int(x["correct"])

    summary = {
        "run_at": datetime.now(timezone.utc).isoformat(),
        "model": get_settings().gemma_model,
        "split": args.split,
        "images": len(records),
        "answered": len(answered),
        "abstained": len(abstained),
        "abstention_rate": round(len(abstained) / len(records), 3) if records else None,
        "top1_agreement_all_images": round(len(correct) / len(records), 3) if records else None,
        "top1_agreement_when_answered": round(len(correct) / len(answered), 3) if answered else None,
        "false_confident_rate": round(len(false_confident) / len(answered), 3) if answered else None,
        "median_latency_ms": sorted(latencies)[len(latencies) // 2] if latencies else None,
        "per_species": {k: {"n": v["n"], "correct": v["correct"]} for k, v in per_species.items()},
        "note": ("Ground truth is the iNaturalist community identification, not an expert re-verification. "
                 "Abstention (species_id null) is counted separately from a wrong answer: for this product, "
                 "an honest 'unsure' is a safe outcome, a confident wrong answer is not."),
    }

    RESULTS.mkdir(parents=True, exist_ok=True)
    (RESULTS / "species_benchmark.json").write_text(json.dumps(summary, indent=2))
    with open(RESULTS / "species_benchmark.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(records[0].keys()))
        w.writeheader()
        w.writerows(records)
    print("\n" + json.dumps({k: v for k, v in summary.items() if k != "per_species"}, indent=2))


if __name__ == "__main__":
    main()
