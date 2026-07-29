"""The executable surface (REGISTRY) must exactly match the declared surface
(gemma_function_declarations) — no handler reachable that the model was never
told about, and no declared name missing its handler.

Regression test for a real gap found in review: REGISTRY had 12 executable
handlers but only 9 were declared to the model. prepare_catch_declaration,
submit_mock_declaration and queue_for_offline_sync were reachable via
execute() despite never being offered as a function-calling option.
"""
from sqlmodel import Session

from app.db.session import get_engine, init_db
from app.tools.registry import DECLARED, REGISTRY, ToolContext, execute, gemma_function_declarations


def test_executable_set_equals_declared_set():
    assert set(REGISTRY.keys()) == DECLARED


def test_no_duplicate_declarations():
    names = [d["name"] for d in gemma_function_declarations()]
    assert len(names) == len(set(names))


def test_every_declaration_has_a_working_handler():
    for d in gemma_function_declarations():
        assert d["name"] in REGISTRY, f"{d['name']} is declared but has no REGISTRY handler"


def test_a_registered_but_undeclared_name_would_be_rejected():
    """Simulates the exact bug this PR fixes: REGISTRY has an entry DECLARED
    doesn't. execute() must refuse it, not silently run it."""
    import app.tools.registry as reg

    real_declared = reg.DECLARED
    try:
        reg.DECLARED = frozenset(real_declared - {"record_catch"})  # pretend it's undeclared
        init_db()
        ctx = ToolContext(session=Session(get_engine()), allow_network=False)
        result, trace = execute("record_catch", {"species_id": "octopus_cyanea"}, ctx)
        assert result == {"error": "unknown_function"}
        assert trace.result_status == "unknown_function"
        assert trace.final_action == "rejected"
    finally:
        reg.DECLARED = real_declared  # never leak state into other tests
