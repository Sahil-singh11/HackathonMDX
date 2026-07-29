#!/usr/bin/env bash
# Start the Lamer Konekte backend and frontend with one command.
#
#   ./scripts/start.sh          dev mode:  uvicorn --reload (:8000) + Vite dev server (:5173)
#   ./scripts/start.sh --prod   prod mode: npm run build, then uvicorn serves the PWA from :8000
#   ./scripts/start.sh --fg     run in the foreground; Ctrl+C stops everything
#
# Env overrides: BACKEND_PORT (8000), FRONTEND_PORT (5173), HOST (127.0.0.1)
# Stop everything again with ./scripts/stop.sh
set -uo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

BACKEND_PORT="${BACKEND_PORT:-8000}"
FRONTEND_PORT="${FRONTEND_PORT:-5173}"
HOST="${HOST:-127.0.0.1}"
RUN_DIR="$ROOT/.run"
MODE="dev"
FOREGROUND=0

for arg in "$@"; do
  case "$arg" in
    --prod) MODE="prod" ;;
    --dev)  MODE="dev" ;;
    --fg|--foreground) FOREGROUND=1 ;;
    -h|--help) sed -n '2,9p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "start.sh: unknown option '$arg' (try --help)" >&2; exit 2 ;;
  esac
done

die() { echo "ERROR: $*" >&2; exit 1; }
say() { printf '%-24s %s\n' "$1" "$2"; }

# --- Locate the venv interpreter (Linux/WSL uses bin/, Git Bash on Windows uses Scripts/)
if   [ -x "$ROOT/backend/.venv/bin/python" ];        then PY="$ROOT/backend/.venv/bin/python"
elif [ -x "$ROOT/backend/.venv/Scripts/python.exe" ]; then PY="$ROOT/backend/.venv/Scripts/python.exe"
else die "backend venv missing. Run: cd backend && python3.12 -m venv .venv && .venv/bin/pip install -r requirements.txt"; fi

# --- PIDs listening on a TCP port, one per line
port_pids() {
  local port="$1"
  if command -v lsof >/dev/null 2>&1; then
    lsof -tiTCP:"$port" -sTCP:LISTEN 2>/dev/null
  elif command -v ss >/dev/null 2>&1; then
    ss -lptnH "sport = :$port" 2>/dev/null | grep -oE 'pid=[0-9]+' | cut -d= -f2 | sort -u
  elif command -v netstat >/dev/null 2>&1; then
    # Windows netstat: Proto | Local Address | Foreign Address | State | PID
    netstat -ano 2>/dev/null | tr -d '\r' \
      | awk -v p=":${port}$" '$1=="TCP" && $2 ~ p && $4=="LISTENING" {print $5}' | sort -u
  fi
}

wait_for_http() {  # url, seconds
  local url="$1" deadline=$(( SECONDS + $2 ))
  while [ "$SECONDS" -lt "$deadline" ]; do
    if command -v curl >/dev/null 2>&1; then
      curl -fsS -o /dev/null --max-time 2 "$url" 2>/dev/null && return 0
    else
      "$PY" -c "import sys,urllib.request; urllib.request.urlopen('$url', timeout=2)" 2>/dev/null && return 0
    fi
    sleep 1
  done
  return 1
}

# --- Preflight -------------------------------------------------------------
echo "=== Lamer Konekte — starting ($MODE mode) ==="

[ -d "$ROOT/frontend/node_modules" ] || die "frontend/node_modules missing. Run: cd frontend && npm install"
command -v npm >/dev/null 2>&1 || die "npm not found on PATH."

for p in "$BACKEND_PORT" "$FRONTEND_PORT"; do
  [ "$MODE" = "prod" ] && [ "$p" = "$FRONTEND_PORT" ] && continue
  if [ -n "$(port_pids "$p")" ]; then
    die "port $p is already in use. Run ./scripts/stop.sh first, or set BACKEND_PORT/FRONTEND_PORT."
  fi
done

if [ -f "$ROOT/.env" ] && grep -qE '^GEMINI_API_KEY=.+' "$ROOT/.env"; then
  say "provider" "key present in .env (hosted Gemma)"
else
  say "provider" "no GEMINI_API_KEY — deterministic mock mode"
fi

mkdir -p "$RUN_DIR"

# --- Frontend --------------------------------------------------------------
FRONTEND_PID=""
if [ "$MODE" = "prod" ]; then
  say "frontend" "building (npm run build)..."
  ( cd "$ROOT/frontend" && npm run build ) >"$RUN_DIR/frontend.log" 2>&1 \
    || { echo "--- last 20 lines of $RUN_DIR/frontend.log ---"; tail -20 "$RUN_DIR/frontend.log"; \
         die "frontend build failed."; }
  [ -f "$ROOT/frontend/dist/index.html" ] || die "build produced no frontend/dist/index.html"
  say "frontend" "built -> served by the backend on :$BACKEND_PORT"
fi

# --- Backend ---------------------------------------------------------------
BACKEND_ARGS=(-m uvicorn app.main:app --host "$HOST" --port "$BACKEND_PORT")
[ "$MODE" = "dev" ] && BACKEND_ARGS+=(--reload)

( cd "$ROOT/backend" && exec "$PY" "${BACKEND_ARGS[@]}" ) >"$RUN_DIR/backend.log" 2>&1 &
BACKEND_PID=$!
echo "$BACKEND_PID" >"$RUN_DIR/backend.pid"

if wait_for_http "http://$HOST:$BACKEND_PORT/health" 45; then
  say "backend" "ready on http://$HOST:$BACKEND_PORT (pid $BACKEND_PID)"
else
  echo "--- last 20 lines of $RUN_DIR/backend.log ---"; tail -20 "$RUN_DIR/backend.log"
  "$ROOT/scripts/stop.sh" >/dev/null 2>&1
  die "backend did not become healthy within 45s."
fi

# --- Vite dev server (dev mode only) ---------------------------------------
if [ "$MODE" = "dev" ]; then
  # --host pins Vite to the same interface we health-check; without it Vite binds
  # "localhost", which resolves to ::1 on Windows and never answers on 127.0.0.1.
  ( cd "$ROOT/frontend" && exec npm run dev -- --host "$HOST" --port "$FRONTEND_PORT" --strictPort ) \
    >"$RUN_DIR/frontend.log" 2>&1 &
  FRONTEND_PID=$!
  echo "$FRONTEND_PID" >"$RUN_DIR/frontend.pid"

  if wait_for_http "http://$HOST:$FRONTEND_PORT/" 45; then
    say "frontend" "ready on http://$HOST:$FRONTEND_PORT (pid $FRONTEND_PID)"
  else
    echo "--- last 20 lines of $RUN_DIR/frontend.log ---"; tail -20 "$RUN_DIR/frontend.log"
    "$ROOT/scripts/stop.sh" >/dev/null 2>&1
    die "Vite dev server did not start within 45s."
  fi
fi

# --- Summary ---------------------------------------------------------------
echo
if [ "$MODE" = "dev" ]; then
  echo "Open http://$HOST:$FRONTEND_PORT   (hot reload; /api and /health proxy to :$BACKEND_PORT)"
  echo "Note: the service worker only runs in production builds — use --prod to test offline/PWA."
else
  echo "Open http://$HOST:$BACKEND_PORT   (backend serves the built PWA)"
fi
echo "API docs: http://$HOST:$BACKEND_PORT/docs"
echo "Logs:     $RUN_DIR/backend.log, $RUN_DIR/frontend.log"
echo "Stop:     ./scripts/stop.sh"

if [ "$FOREGROUND" -eq 1 ]; then
  trap 'echo; echo "Stopping..."; "$ROOT/scripts/stop.sh"; exit 0' INT TERM
  echo
  echo "Running in the foreground — Ctrl+C to stop."
  wait
fi
