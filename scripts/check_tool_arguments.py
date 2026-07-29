#!/usr/bin/env python3
"""Tool-argument validation against the live backend registry.

Every `expected_tool_call` must be an allow-listed routable tool, and every concrete
`expected_arguments` set must validate against that tool's real Pydantic argument model
— so training never teaches the model to emit arguments the backend would reject.

Deliberate-failure records (keys starting with `_`, e.g. `_invalid`, `_missing`,
`_ambiguous`, `_out_of_range`) describe cases where the CORRECT behaviour is to refuse
or ask; they are checked for intent, not validated as valid arguments.

    python scripts/check_tool_arguments.py
Exit 0 = pass, 1 = fail.
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.prompts.compact_router_v1 import ROUTABLE_TOOLS  # noqa: E402
from app.tools.registry import REGISTRY  # noqa: E402

DATA = ROOT / "training" / "data"

# Router-level argument names that the backend derives rather than accepting directly.
# `location_name` is resolved to lat/lon server-side; `day` selects a forecast slot.
ROUTER_ONLY_ARGS = {"location_name", "day"}

# Arguments the APPLICATION supplies from confirmed session state, not the router.
# `record_catch.species_id` is the clear case: the fisher says "log two fish", and the
# species comes from the analysis they already confirmed. A router that invented a
# species_id here would be doing exactly what the safety rules forbid. These are filled
# with a valid stub so the rest of the argument set is still really validated.
CONTEXT_SUPPLIED = {
    "record_catch": {"species_id": "octopus_cyanea"},
    "check_confirmed_catch_rule": {"species_id": "octopus_cyanea"},
    "get_species_details": {"species_id": "octopus_cyanea"},
    "submit_mock_declaration": {"declaration_id": "decl-stub"},
    "prepare_catch_declaration": {"period_start": "2026-07-01", "period_end": "2026-07-15"},
}


def load_jsonl(p: Path) -> list[dict]:
    return [json.loads(line) for line in p.read_text(encoding="utf-8").splitlines() if line.strip()]


def main() -> int:
    failures: list[str] = []
    master = load_jsonl(DATA / "master_records.jsonl")

    # every routable tool must exist in the real registry
    for tool in ROUTABLE_TOOLS:
        if tool not in REGISTRY:
            failures.append(f"routable tool {tool!r} is not in the backend REGISTRY")

    validated = 0
    negative = 0
    for r in master:
        tool = r["expected_tool_call"]
        args = r["expected_arguments"] or {}

        if tool is None:
            if args and not any(k.startswith("_") for k in args):
                failures.append(f"{r['id']} has arguments but no tool")
            continue

        if tool not in REGISTRY:
            failures.append(f"{r['id']} references unknown tool {tool!r}")
            continue
        if tool not in ROUTABLE_TOOLS:
            failures.append(f"{r['id']} uses non-routable tool {tool!r}")
            continue

        # Deliberate-failure record: the expected behaviour is refusal/clarification.
        if any(k.startswith("_") for k in args):
            negative += 1
            if not r["expected_final_behaviour"].strip():
                failures.append(f"{r['id']} is a negative argument case with no expected behaviour")
            continue

        concrete = {k: v for k, v in args.items()
                    if k not in ROUTER_ONLY_ARGS and v is not None}
        if not concrete:
            continue

        # Merge context-supplied fields the router is not responsible for, so the
        # router-supplied arguments are still genuinely validated against the real model.
        merged = {**CONTEXT_SUPPLIED.get(tool, {}), **concrete}
        model_cls, _handler = REGISTRY[tool]
        try:
            model_cls(**merged)
            validated += 1
        except Exception as e:  # noqa: BLE001
            failures.append(f"{r['id']} arguments rejected by {tool} model: {type(e).__name__}: "
                            f"{str(e).splitlines()[0][:120]}")

    report = {
        "records": len(master),
        "tools_in_registry": len(REGISTRY),
        "routable_tools": len(ROUTABLE_TOOLS),
        "argument_sets_validated": validated,
        "context_supplied_tools": sorted(CONTEXT_SUPPLIED),
        "negative_argument_cases": negative,
        "by_tool": dict(Counter(r["expected_tool_call"] or "(none)" for r in master)),
        "failures": failures,
        "passed": not failures,
    }
    out = ROOT / "training" / "results" / "tool_argument_validation.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"validated {validated} concrete argument sets, {negative} negative cases, "
          f"{len(ROUTABLE_TOOLS)} routable tools")
    for f in failures[:15]:
        print(f"  FAIL {f}")
    print("PASS" if not failures else "FAIL")
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
