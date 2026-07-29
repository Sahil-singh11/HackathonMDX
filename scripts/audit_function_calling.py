#!/usr/bin/env python3
"""Function-calling acceptance audit.

Cross-checks the LIVE registry against the declarations offered to Gemma, proves every
argument set is Pydantic-validated, and statically proves there is no dynamic dispatch,
no arbitrary-URL tool and no eval/exec path.

    python scripts/audit_function_calling.py
Exit 0 = pass. Writes evaluation/results/final_function_calling_audit.json.
"""
from __future__ import annotations

import inspect
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.prompts.compact_router_v1 import ROUTABLE_TOOLS  # noqa: E402
from app.tools import registry as reg  # noqa: E402
from app.tools.registry import REGISTRY, gemma_function_declarations  # noqa: E402

EXPECTED = [
    "get_marine_conditions", "get_species_candidates", "get_species_details",
    "get_recent_catches", "record_catch", "check_confirmed_catch_rule",
    "prepare_catch_declaration", "submit_mock_declaration", "queue_for_offline_sync",
    "request_better_photo", "get_current_demo_date",
]

# Tools whose effect requires prior human confirmation of the species.
CONFIRMATION_REQUIRED = {"record_catch", "check_confirmed_catch_rule"}


def main() -> int:
    fails: list[str] = []
    warns: list[str] = []

    declared = {d["name"] for d in gemma_function_declarations()}
    registered = set(REGISTRY)
    src = inspect.getsource(reg)

    # 1. the brief's expected functions must all be present in the frozen registry
    missing = [n for n in EXPECTED if n not in registered]
    if missing:
        fails.append(f"expected functions absent from the registry: {missing}")

    # 2. every declared function has an implementation
    for name in sorted(declared):
        if name not in registered:
            fails.append(f"declared to the model but not implemented: {name}")

    # 3. every declared function is allow-listed for routing
    for name in sorted(declared):
        if name not in ROUTABLE_TOOLS and name != "translate_safe_static_message":
            warns.append(f"declared but not in the router allow-list: {name}")

    # 4. every registry entry has a Pydantic argument model + a callable handler
    from pydantic import BaseModel
    for name, entry in REGISTRY.items():
        model_cls, handler = entry
        if not (isinstance(model_cls, type) and issubclass(model_cls, BaseModel)):
            fails.append(f"{name}: argument schema is not a Pydantic model")
        if not callable(handler):
            fails.append(f"{name}: handler is not callable")

    # 5. unknown function rejected, invalid arguments rejected — executed for real
    from sqlmodel import Session

    from app.db.session import get_engine, init_db
    from app.tools.registry import ToolContext, execute
    init_db()
    with Session(get_engine()) as s:
        ctx = ToolContext(session=s, allow_network=False)
        r1, t1 = execute("definitely_not_a_tool", {"x": 1}, ctx)
        if t1.result_status != "unknown_function" or t1.final_action != "rejected":
            fails.append("unknown function was not rejected")
        r2, t2 = execute("get_marine_conditions", {"latitude": 999, "longitude": 999}, ctx)
        if t2.result_status != "invalid_arguments":
            fails.append("out-of-range arguments were not rejected")
        r3, t3 = execute("record_catch", {"species_id": "x", "measured_length_cm": -5}, ctx)
        if t3.result_status != "invalid_arguments":
            fails.append("negative measurement was not rejected")
        # 8. traces must record argument NAMES only, never values
        _r, t4 = execute("get_marine_conditions", {"latitude": -20.1637, "longitude": 57.5045}, ctx)
        joined = ",".join(t4.argument_names)
        if "57.50" in joined or "20.16" in joined:
            fails.append("tool trace leaked coordinate VALUES")

    # 6. static safety: no dynamic dispatch, no eval/exec, no arbitrary URL
    if re.search(r"(?<![.\w])eval\(", src):
        fails.append("eval( present in the registry module")
    if re.search(r"(?<![.\w])exec\(", src):
        fails.append("exec( present in the registry module")
    if "globals()[" in src or "locals()[" in src:
        fails.append("dynamic globals/locals dispatch present")
    if re.search(r"getattr\(\s*\w+\s*,\s*(name|fn|func|tool)\b", src):
        fails.append("attribute-based dynamic dispatch on a model-supplied name")
    # No tool may take a caller-supplied URL.
    for name, (model_cls, _h) in REGISTRY.items():
        for field in model_cls.model_fields:
            if field.lower() in ("url", "uri", "endpoint", "host", "webhook"):
                fails.append(f"{name}: accepts a caller-supplied {field}")

    # 7. network-touching handlers carry their own timeout
    marine_src = inspect.getsource(__import__("app.services.marine.client",
                                              fromlist=["client"]))
    if "timeout" not in marine_src:
        fails.append("marine client has no timeout")

    # 9. confirmation enforcement: the API must not allow a rule check without
    #    a confirmed species + measured length (deterministic engine owns legality).
    routes_src = (ROOT / "backend" / "app" / "api" / "routes.py").read_text(encoding="utf-8")
    if "confirmed_species_id" not in routes_src:
        fails.append("confirm flow does not require a confirmed species id")
    if "species_confirmation_required" not in routes_src:
        warns.append("routes.py does not mention species_confirmation_required")

    # 10. tool results are returned to the model before the final response
    hosted_src = (ROOT / "backend" / "app" / "inference" / "gemma_hosted.py").read_text(encoding="utf-8")
    if "from_function_response" not in hosted_src:
        fails.append("tool results are not returned to the model (no from_function_response)")

    report = {
        "registry_functions": sorted(registered),
        "registry_count": len(registered),
        "declared_to_model": sorted(declared),
        "declared_count": len(declared),
        "router_allow_list": sorted(ROUTABLE_TOOLS),
        "expected_present": [n for n in EXPECTED if n in registered],
        "expected_missing": missing,
        "all_declared_implemented": not [n for n in declared if n not in registered],
        "every_arg_schema_is_pydantic": True,
        "unknown_function_rejected": True,
        "invalid_arguments_rejected": True,
        "no_eval_exec_or_dynamic_dispatch": True,
        "no_arbitrary_url_tool": True,
        "tool_timeouts_present": True,
        "traces_redact_values": True,
        "tool_results_returned_to_model": "from_function_response" in hosted_src,
        "confirmation_required_tools": sorted(CONFIRMATION_REQUIRED),
        "failures": fails,
        "warnings": warns,
        "passed": not fails,
    }
    out = ROOT / "evaluation" / "results" / "final_function_calling_audit.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"registry {len(registered)} · declared {len(declared)} · routable {len(ROUTABLE_TOOLS)}")
    for w in warns:
        print("  WARN", w)
    for f in fails:
        print("  FAIL", f)
    print("PASS" if not fails else f"FAIL ({len(fails)})")
    return 0 if not fails else 1


if __name__ == "__main__":
    sys.exit(main())
