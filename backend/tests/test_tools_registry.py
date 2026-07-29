"""Allow-list, argument validation, injection resistance, trace redaction."""
from sqlmodel import Session

from app.db.session import get_engine, init_db
from app.tools.registry import REGISTRY, ToolContext, execute


def _ctx() -> ToolContext:
    init_db()
    return ToolContext(session=Session(get_engine()), allow_network=False)


def test_unknown_function_fails_safely():
    result, trace = execute("run_shell_command", {"cmd": "rm -rf /"}, _ctx())
    assert result == {"error": "unknown_function"}
    assert trace.result_status == "unknown_function"
    assert trace.final_action == "rejected"


def test_invalid_arguments_fail_safely():
    result, trace = execute("get_marine_conditions", {"latitude": 500}, _ctx())
    assert result["error"] == "invalid_arguments"
    assert trace.result_status == "invalid_arguments"


def test_registry_is_exactly_the_allow_list():
    expected = {
        "get_marine_conditions", "get_species_candidates", "get_species_details",
        "get_recent_catches", "record_catch", "check_confirmed_catch_rule",
        "prepare_catch_declaration", "submit_mock_declaration", "queue_for_offline_sync",
        "request_better_photo", "get_current_demo_date", "translate_safe_static_message",
    }
    assert set(REGISTRY.keys()) == expected


def test_no_dynamic_dispatch_primitives_in_registry_module():
    import inspect
    import re

    import app.tools.registry as reg
    src = inspect.getsource(reg)
    # Bare builtins only — attribute calls like session.exec() are fine.
    assert not re.search(r"(?<![.\w])eval\(", src)
    assert not re.search(r"(?<![.\w])exec\(", src)
    assert "globals()[" not in src


def test_species_candidates_offline():
    result, trace = execute("get_species_candidates", {"note": "mo'nn gagn enn ourite"}, _ctx())
    assert trace.result_status == "ok"
    ids = [c["species_id"] for c in result["candidates"]]
    assert "octopus_cyanea" in ids


def test_marine_offline_returns_disclosed_mock():
    result, trace = execute("get_marine_conditions", {"latitude": -20.16, "longitude": 57.5}, _ctx())
    assert trace.result_status == "ok"
    assert result.get("mock") is True or result.get("cached") is True
    assert "informational" in result["disclaimer"]


def test_rule_check_tool_is_deterministic_and_noticed():
    result, _ = execute("check_confirmed_catch_rule",
                        {"species_id": "octopus_cyanea", "capture_date": "2026-09-01"}, _ctx())
    assert result["legal_check"]["status"] == "closed_season"
    assert "official fisheries notice" in result["notice"]


def test_translate_static_message():
    result, _ = execute("translate_safe_static_message",
                        {"message_key": "marine_disclaimer", "language": "mfe"}, _ctx())
    assert "lamer" in result["text"].lower() or "ofisiel" in result["text"].lower()


def test_trace_contains_argument_names_not_values():
    _, trace = execute("get_marine_conditions", {"latitude": -20.1637, "longitude": 57.5045}, _ctx())
    joined = ",".join(trace.argument_names)
    assert "latitude" in joined
    assert "57.50" not in joined  # no coordinate values in traces
