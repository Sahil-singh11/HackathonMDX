#!/usr/bin/env bash
# One-command final AI verification (macOS/Linux/WSL).
#   ./scripts/run_final_ai_check.sh            offline
#   ./scripts/run_final_ai_check.sh --live     + real hosted gates + Render
#   ./scripts/run_final_ai_check.sh --quick    minimum demo readiness
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
if [ -x "$ROOT/backend/.venv/bin/python" ]; then PY="$ROOT/backend/.venv/bin/python";
elif [ -x "$ROOT/backend/.venv/Scripts/python.exe" ]; then PY="$ROOT/backend/.venv/Scripts/python.exe";
else PY=python3; fi
MODE="${1:---offline}"
export PYTHONIOENCODING=utf-8 PYTHONUTF8=1
exec "$PY" "$ROOT/scripts/final_ai_check.py" "$MODE"
