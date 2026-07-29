#!/usr/bin/env bash
# Stop the Lamer Konekte backend and frontend started by ./scripts/start.sh.
#
#   ./scripts/stop.sh           stop whatever is running on the project ports
#   ./scripts/stop.sh --status  report what is running, kill nothing
#
# Safe to run when nothing is running (exits 0). Cleans up PID files either way.
# Env overrides: BACKEND_PORT (8000), FRONTEND_PORT (5173)
set -uo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

BACKEND_PORT="${BACKEND_PORT:-8000}"
FRONTEND_PORT="${FRONTEND_PORT:-5173}"
RUN_DIR="$ROOT/.run"
STATUS_ONLY=0

for arg in "$@"; do
  case "$arg" in
    --status) STATUS_ONLY=1 ;;
    -h|--help) sed -n '2,8p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "stop.sh: unknown option '$arg' (try --help)" >&2; exit 2 ;;
  esac
done

say() { printf '%-24s %s\n' "$1" "$2"; }

case "$(uname -s 2>/dev/null)" in
  MINGW*|MSYS*|CYGWIN*) WINDOWS=1 ;;
  *) WINDOWS=0 ;;
esac

port_pids() {
  local port="$1"
  if command -v lsof >/dev/null 2>&1; then
    lsof -tiTCP:"$port" -sTCP:LISTEN 2>/dev/null
  elif command -v ss >/dev/null 2>&1; then
    ss -lptnH "sport = :$port" 2>/dev/null | grep -oE 'pid=[0-9]+' | cut -d= -f2 | sort -u
  elif command -v netstat >/dev/null 2>&1; then
    netstat -ano 2>/dev/null | tr -d '\r' \
      | awk -v p=":${port}$" '$1=="TCP" && $2 ~ p && $4=="LISTENING" {print $5}' | sort -u
  fi
}

# On Git Bash a PID may be either a Bash job PID or a native Windows PID, and the
# two namespaces are distinct — so ask both before declaring a process dead.
alive() {
  local pid="$1"
  kill -0 "$pid" 2>/dev/null && return 0
  [ "$WINDOWS" -eq 1 ] && tasklist //FI "PID eq $pid" //NH 2>/dev/null | grep -q "\b$pid\b"
}

# Terminate a process and its children: TERM first, then KILL if it survives.
kill_tree() {
  local pid="$1"
  [ -n "$pid" ] || return 0
  alive "$pid" || return 0

  local kids
  kids="$(pgrep -P "$pid" 2>/dev/null)"

  # //T takes the whole tree on Windows; it is a no-op for a Bash-only PID, so the
  # POSIX signals below still run as the fallback.
  [ "$WINDOWS" -eq 1 ] && taskkill //PID "$pid" //T //F >/dev/null 2>&1

  alive "$pid" || return 0
  kill -TERM "$pid" 2>/dev/null
  for kid in $kids; do kill_tree "$kid"; done
  for _ in 1 2 3 4 5 6 7 8 9 10; do
    alive "$pid" || return 0
    sleep 0.5
  done
  kill -KILL "$pid" 2>/dev/null
}

# --- Report ----------------------------------------------------------------
BACK_PIDS="$(port_pids "$BACKEND_PORT")"
FRONT_PIDS="$(port_pids "$FRONTEND_PORT")"

if [ "$STATUS_ONLY" -eq 1 ]; then
  say "backend  :$BACKEND_PORT"  "${BACK_PIDS:-(not running)}"
  say "frontend :$FRONTEND_PORT" "${FRONT_PIDS:-(not running)}"
  exit 0
fi

echo "=== Lamer Konekte — stopping ==="

STOPPED=0

# 1. PID files written by start.sh (kills the process tree, including Vite's child)
for name in backend frontend; do
  pidfile="$RUN_DIR/$name.pid"
  [ -f "$pidfile" ] || continue
  pid="$(tr -dc '0-9' <"$pidfile")"
  if [ -n "$pid" ] && alive "$pid"; then
    kill_tree "$pid"
    say "$name" "stopped (pid $pid)"
    STOPPED=1
  fi
  rm -f "$pidfile"
done

# 2. Port sweep — catches orphans and servers started by hand (uvicorn/npm directly)
for entry in "backend:$BACKEND_PORT" "frontend:$FRONTEND_PORT"; do
  name="${entry%%:*}"; port="${entry##*:}"
  for pid in $(port_pids "$port"); do
    kill_tree "$pid"
    say "$name" "stopped orphan on :$port (pid $pid)"
    STOPPED=1
  done
done

[ "$STOPPED" -eq 0 ] && say "status" "nothing was running"

# 3. Verify the ports actually released
sleep 1
FAIL=0
for entry in "backend:$BACKEND_PORT" "frontend:$FRONTEND_PORT"; do
  name="${entry%%:*}"; port="${entry##*:}"
  remaining="$(port_pids "$port")"
  if [ -n "$remaining" ]; then
    say "$name" "WARNING :$port still held by pid(s): $remaining"
    FAIL=1
  fi
done

rmdir "$RUN_DIR" 2>/dev/null  # removes it only if no logs are left behind

if [ "$FAIL" -eq 0 ]; then
  echo "All project ports are free."
else
  echo "Some ports are still in use — inspect the PIDs above." >&2
fi
exit "$FAIL"
