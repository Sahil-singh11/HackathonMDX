"""Portability of the hosted Gemma model across team laptops.

Two supported modes (docs/TEAM_AI_MODEL_SETUP.md):
  A  frontend only, pointed at the shared deployed backend — no local key
  B  full local stack — an authorised key in the repo-root .env, backend-only

These tests lock the properties that make both modes safe: nothing machine-specific in
the source, the key never crosses into the frontend or any response, the model resolves
from configuration to the pinned name, and the rejected E2B adapter cannot be switched on.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[1]
ROOT = BACKEND.parent
MODEL = "gemma-4-26b-a4b-it"

PY_SOURCES = [p for p in (BACKEND / "app").rglob("*.py")]
FE_SOURCES = [p for p in (ROOT / "frontend" / "src").rglob("*.ts")] + \
             [p for p in (ROOT / "frontend" / "src").rglob("*.tsx")]


# ------------------------------------------------------------ machine-specific config

def test_no_machine_specific_paths_in_backend_or_frontend_source():
    """A laptop-specific path is the classic reason a checkout works for one person only."""
    bad = re.compile(r"C:\\\\Users|C:/Users|/Users/[a-z]+/|OneDrive|AppData", re.I)
    offenders = []
    for path in PY_SOURCES + FE_SOURCES:
        for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if bad.search(line):
                offenders.append(f"{path.relative_to(ROOT)}:{i}")
    assert offenders == [], f"machine-specific paths: {offenders}"


def test_no_embedded_api_key_anywhere_in_source():
    key_shaped = re.compile(r"AIza[0-9A-Za-z_-]{20,}")
    for path in PY_SOURCES + FE_SOURCES:
        assert not key_shaped.search(path.read_text(encoding="utf-8")), path


def test_no_local_model_weights_are_required_to_start():
    """gemma-4-26b-a4b-it is called over the network; nothing is downloaded or loaded."""
    from app.core.config import get_settings
    s = get_settings()
    assert s.gemma_provider == "google"
    # No weight/checkpoint path setting exists that startup could depend on.
    for field in type(s).model_fields:
        assert not re.search(r"(weights|checkpoint|safetensors|model_path)", field), field


def test_adapter_is_not_loaded_automatically_at_import():
    """Importing the app must not pull in or activate the rejected adapter."""
    import app.main  # noqa: F401
    from app.api import routes
    assert not hasattr(routes, "finetuned_router")
    from app.providers import finetuned_router
    with pytest.raises(finetuned_router.RouterUnavailable):
        finetuned_router.route("ki kondisyon lamer?")


# ------------------------------------------------------------ model + provider resolution

def test_model_resolves_from_configuration_and_defaults_to_the_pinned_model():
    from app.core.config import Settings
    # _env_file=None so the developer's own .env cannot make this pass by accident.
    assert Settings(_env_file=None).gemma_model == MODEL


def test_provider_mode_env_var_selects_hosted(monkeypatch):
    """A teammate sets PROVIDER_MODE in their own .env; it must reach the setting."""
    from app.core.config import Settings
    monkeypatch.setenv("PROVIDER_MODE", "hosted")
    assert Settings(_env_file=None).provider_mode == "hosted"


def test_only_the_three_documented_provider_modes_are_accepted(client):
    """No undocumented value — including any adapter name — may be selected."""
    for mode in ("finetuned", "e2b", "finetuned_e2b", "adapter", "local_e2b"):
        r = client.post("/api/analyse-catch", data={"note": "test", "provider_mode": mode})
        assert r.status_code == 422, f"{mode} was accepted"


# ------------------------------------------------------------ secret containment

def test_frontend_never_references_a_gemini_key_variable():
    """Vite inlines every VITE_* value into the public bundle, so a key there is published."""
    for path in FE_SOURCES:
        text = path.read_text(encoding="utf-8")
        assert "VITE_GEMINI" not in text, path
        # The frontend may *mention* the name in a warning comment, but must never read one.
        assert not re.search(r"import\.meta\.env\.\w*(GEMINI|API_KEY|SECRET)", text), path


def test_frontend_env_example_declares_only_the_backend_url():
    example = ROOT / "frontend" / ".env.example"
    assert example.exists(), "frontend/.env.example is the switch between the two modes"
    assignments = [ln for ln in example.read_text(encoding="utf-8").splitlines()
                   if "=" in ln and not ln.strip().startswith("#")]
    assert assignments, "the example must show the variable"
    for line in assignments:
        name = line.split("=", 1)[0].strip()
        assert name == "VITE_API_BASE_URL", f"unexpected frontend variable {name}"


def test_repo_env_example_has_the_real_names_and_no_real_values():
    example = ROOT / ".env.example"
    text = example.read_text(encoding="utf-8")
    assert "GEMINI_API_KEY=" in text
    assert f"GEMMA_MODEL={MODEL}" in text
    assert "PROVIDER_MODE=hosted" in text
    # A placeholder only — never a usable key.
    assert not re.search(r"AIza[0-9A-Za-z_-]{20,}", text)
    for line in text.splitlines():
        if line.startswith("GEMINI_API_KEY="):
            value = line.split("=", 1)[1].strip()
            assert value == "" or value.isupper() or "PASTE" in value.upper(), value


def test_env_files_are_git_ignored_and_examples_are_not():
    ignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
    assert re.search(r"^\.env$", ignore, re.M)
    assert re.search(r"^\.env\.\*$", ignore, re.M)
    assert re.search(r"^!\.env\.example$", ignore, re.M)


def test_provider_status_never_returns_key_material(client):
    """Assert no key VALUE leaks — not that the variable is never named.

    The payload legitimately contains "gemini_api_key is not configured; hosted calls fall
    back to the mock", which is exactly the diagnostic a teammate needs. Banning the name
    outright would have forced that useful disclosure to be deleted to satisfy a test.
    """
    body = client.get("/api/provider/status").json()
    raw = repr(body)
    assert not re.search(r"AIza[0-9A-Za-z_-]{10,}", raw)
    # No name is bound to a secret-looking value anywhere in the payload.
    assert not re.search(r"(?i)['\"]?(api_key|gemini_api_key|secret|token)['\"]?\s*[:=]\s*['\"][^'\"]{8,}", raw)
    # And the real key from this developer's environment is not present.
    from app.core.config import get_settings
    real = get_settings().gemini_api_key
    if real:
        assert real not in raw
    # It must still report what a teammate needs in order to trust the model.
    assert body["hosted"]["model"] == MODEL


def test_public_config_never_returns_key_material(client):
    body = client.get("/api/config/public").json()
    raw = repr(body)
    assert not re.search(r"AIza[0-9A-Za-z_-]{10,}", raw)
    assert "api_key" not in raw.lower()


def test_no_module_logs_the_api_key():
    """A key printed into a log is a leaked key — Render's logs are readable by the team."""
    bad = re.compile(r"(log\.\w+|print|logger\.\w+)\([^)]*gemini_api_key", re.I)
    for path in PY_SOURCES:
        assert not bad.search(path.read_text(encoding="utf-8")), path


# ------------------------------------------------------------ frontend API base

def test_frontend_routes_every_request_through_the_configurable_base():
    """Mode A works only if no call is hardcoded to a relative path or to localhost."""
    client_ts = (ROOT / "frontend" / "src" / "api" / "client.ts").read_text(encoding="utf-8")
    unwrapped = re.findall(r"fetch\((['\"`])/(?:api|health)", client_ts)
    assert unwrapped == [], f"{len(unwrapped)} fetch call(s) bypass apiUrl()"
    assert "from './base'" in client_ts


def test_api_base_module_reads_no_secret():
    base_ts = (ROOT / "frontend" / "src" / "api" / "base.ts").read_text(encoding="utf-8")
    assert "VITE_API_BASE_URL" in base_ts
    assert not re.search(r"import\.meta\.env\.\w*(GEMINI|KEY|SECRET|TOKEN)", base_ts)


def test_no_hardcoded_localhost_in_frontend_request_code():
    for path in FE_SOURCES:
        text = path.read_text(encoding="utf-8")
        for match in re.finditer(r"https?://(?:localhost|127\.0\.0\.1)(:\d+)?", text):
            line_start = text.rfind("\n", 0, match.start()) + 1
            line = text[line_start:text.find("\n", match.start())]
            # Comments and documentation may name the local URL; code must not.
            assert line.lstrip().startswith(("*", "//", "#")), f"{path.relative_to(ROOT)}: {line.strip()}"


# ------------------------------------------------------------ shared-backend CORS

def test_a_teammate_frontend_on_any_loopback_port_is_allowed():
    """run.ps1 walks the frontend port upward when 5173 is taken, so an exact-match origin
    list silently broke Mode A for anyone whose 5173 was already in use."""
    from app.main import create_app
    app = create_app()
    cors = [m for m in app.user_middleware if "CORS" in str(m)]
    assert cors, "CORS middleware is required for the shared-backend mode"
    options = cors[0].kwargs
    pattern = options.get("allow_origin_regex")
    assert pattern, "a loopback regex is required so non-5173 ports still work"
    compiled = re.compile(pattern)
    for port in ("5173", "5174", "5199", "4173"):
        assert compiled.fullmatch(f"http://127.0.0.1:{port}"), port
        assert compiled.fullmatch(f"http://localhost:{port}"), port


def test_extra_cors_origins_are_configurable_without_code_changes(monkeypatch):
    from app.core.config import Settings
    assert Settings(_env_file=None).cors_extra_origins_list == []
    monkeypatch.setenv("CORS_EXTRA_ORIGINS", "https://a.example, https://b.example")
    assert Settings(_env_file=None).cors_extra_origins_list == ["https://a.example",
                                                               "https://b.example"]
