#!/usr/bin/env python3
"""One-command final AI verification.

    python scripts/final_ai_check.py --offline    # no API key, no network to Google
    python scripts/final_ai_check.py --live       # offline + real hosted gates + Render
    python scripts/final_ai_check.py --quick      # minimum demo-readiness

Prints a PASS/FAIL table, writes evaluation/results/final_ai_check.json, and exits
non-zero if any REQUIRED check fails. Never prints secrets.
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
IS_WIN = platform.system() == "Windows"
PY = ROOT / "backend" / (".venv/Scripts/python.exe" if IS_WIN else ".venv/bin/python")
if not PY.exists():
    PY = Path(sys.executable)

RESULTS: list[dict] = []


def run(name: str, cmd: list[str], *, cwd: Path = ROOT, required: bool = True,
        timeout: int = 1800, env_extra: dict | None = None) -> bool:
    env = {**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1", **(env_extra or {})}
    t0 = time.monotonic()
    try:
        p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True,
                           timeout=timeout, env=env, encoding="utf-8", errors="replace")
        ok = p.returncode == 0
        tail = (p.stdout or p.stderr or "").strip().splitlines()
        detail = tail[-1][:160] if tail else ""
    except subprocess.TimeoutExpired:
        ok, detail = False, f"timed out after {timeout}s"
    except Exception as e:  # noqa: BLE001
        ok, detail = False, f"{type(e).__name__}: {e}"
    ms = int((time.monotonic() - t0) * 1000)
    RESULTS.append({"check": name, "ok": ok, "required": required,
                    "seconds": round(ms / 1000, 1), "detail": detail})
    flag = "PASS" if ok else ("FAIL" if required else "WARN")
    print(f"  [{flag}] {name:<42} {ms/1000:>6.1f}s  {detail[:70]}")
    return ok


def has_key() -> bool:
    if os.environ.get("GEMINI_API_KEY"):
        return True
    env = ROOT / ".env"
    if not env.exists():
        return False
    for line in env.read_text(encoding="utf-8").splitlines():
        if line.startswith("GEMINI_API_KEY=") and line.split("=", 1)[1].strip():
            return True
    return False


def missing_requirements() -> list[str]:
    """Declared backend requirements that are not installed in the venv being used.

    Without this, a venv that predates a teammate's new dependency fails as an opaque
    pytest collection error, which reads like a code regression instead of "run pip
    install". Only distribution names are reported — never versions of anything secret.
    """
    req = ROOT / "backend" / "requirements.txt"
    if not req.exists():
        return []
    names = []
    for raw in req.read_text(encoding="utf-8").splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line or line.startswith("-"):
            continue
        names.append(re.split(r"[<>=!~\[;]", line, 1)[0].strip())
    probe = (
        "import importlib.metadata as m, sys\n"
        "out=[]\n"
        "for n in sys.argv[1:]:\n"
        "    try: m.version(n)\n"
        "    except Exception: out.append(n)\n"
        "print(' '.join(out))\n"
    )
    try:
        p = subprocess.run([str(PY), "-c", probe, *names], capture_output=True, text=True,
                           timeout=120, encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001 — a probe failure must not mask the real checks
        return []
    return (p.stdout or "").split()


def offline_suite(quick: bool) -> None:
    print("\n== offline ==")
    absent = missing_requirements()
    if absent:
        print(f"  [WARN] {len(absent)} declared backend dependency/ies not installed in the "
              f"venv: {', '.join(absent)}")
        print(f"         fix with: {PY} -m pip install -r backend/requirements.txt")
        print("         test failures below are most likely this, not a code regression.")
    run("backend unit + AI + safety tests", [str(PY), "-m", "pytest", "-q"],
        cwd=ROOT / "backend")
    run("final acceptance regression tests",
        [str(PY), "-m", "pytest", "tests/test_final_acceptance.py", "-q"], cwd=ROOT / "backend")
    run("dataset + leakage + family + args + safety validators",
        [str(PY), "scripts/validate_v2_dataset.py"])
    run("function-calling audit", [str(PY), "scripts/audit_function_calling.py"])
    run("training-evidence audit", [str(PY), "scripts/audit_training_evidence.py"])
    if not quick:
        npm = "npm.cmd" if IS_WIN else "npm"
        run("frontend production build", [npm, "run", "build"], cwd=ROOT / "frontend")
        # A bare "bash" on Windows resolves to the WSL stub, which cannot see the repo's
        # venv paths; prefer Git-for-Windows bash when it exists.
        bash = "bash"
        if IS_WIN:
            for cand in ("C:/Program Files/Git/bin/bash.exe",
                         "C:/Program Files (x86)/Git/bin/bash.exe"):
                if Path(cand).exists():
                    bash = cand
                    break
        run("release gate (13 checks)", [bash, "scripts/release_gate.sh"],
            required=(bash != "bash" or not IS_WIN))


def live_suite() -> None:
    print("\n== live ==")
    if not has_key():
        RESULTS.append({"check": "hosted live gates", "ok": False, "required": True,
                        "seconds": 0.0, "detail": "GEMINI_API_KEY not available"})
        print("  [FAIL] hosted live gates                        "
              "     0.0s  GEMINI_API_KEY not available")
        return
    key = os.environ.get("GEMINI_API_KEY") or next(
        (l.split("=", 1)[1].strip() for l in (ROOT / ".env").read_text(encoding="utf-8").splitlines()
         if l.startswith("GEMINI_API_KEY=")), "")
    run("hosted Gemma live gates (10, real inference)",
        [str(PY), "scripts/run_final_live_gates.py"], cwd=ROOT / "backend",
        env_extra={"GEMINI_API_KEY": key})
    run("hosted integration tests (live tier)",
        [str(PY), "-m", "pytest", "tests/test_hosted_integration.py", "-m", "live", "-q"],
        cwd=ROOT / "backend", env_extra={"GEMINI_API_KEY": key})
    run("deployed Render checks", [str(PY), "scripts/final_render_check.py", "--live"],
        required=False)


def main() -> int:
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--offline", action="store_true")
    g.add_argument("--live", action="store_true")
    g.add_argument("--quick", action="store_true")
    a = ap.parse_args()
    mode = "live" if a.live else ("quick" if a.quick else "offline")

    started = datetime.now(timezone.utc)
    print(f"Final AI check — mode: {mode}  ({started.isoformat(timespec='seconds')})")
    print(f"interpreter: {PY}")
    print(f"API key available: {'yes' if has_key() else 'no'}  (value never printed)")

    offline_suite(quick=a.quick)
    if a.live:
        live_suite()

    required = [r for r in RESULTS if r["required"]]
    failed = [r for r in required if not r["ok"]]
    optional_failed = [r for r in RESULTS if not r["required"] and not r["ok"]]

    payload = {
        "run_at": started.isoformat(), "mode": mode,
        "api_key_available": has_key(),
        "checks_total": len(RESULTS),
        "required_passed": len(required) - len(failed),
        "required_failed": len(failed),
        "optional_failed": len(optional_failed),
        "passed": not failed,
        "results": RESULTS,
    }
    out = ROOT / "evaluation" / "results" / "final_ai_check.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    print("\n" + "=" * 78)
    print(f"{'CHECK':<46}{'REQ':<6}{'RESULT'}")
    print("-" * 78)
    for r in RESULTS:
        print(f"{r['check']:<46}{'yes' if r['required'] else 'no':<6}"
              f"{'PASS' if r['ok'] else ('FAIL' if r['required'] else 'WARN')}")
    print("=" * 78)
    print(f"mode={mode}  required {payload['required_passed']}/{len(required)} passed"
          + (f"  ({len(optional_failed)} optional warning)" if optional_failed else ""))
    print("OVERALL: " + ("PASS" if not failed else "FAIL"))
    if failed:
        print("failing required checks: " + ", ".join(r["check"] for r in failed))
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
