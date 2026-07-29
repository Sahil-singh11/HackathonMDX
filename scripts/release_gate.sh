#!/usr/bin/env bash
# Public-release gate — every check must pass before the repo goes public.
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
# Venv layout differs by OS: bin/python (POSIX) vs Scripts/python.exe (Windows).
if [ -x backend/.venv/bin/python ]; then PY=backend/.venv/bin/python;
else PY=backend/.venv/Scripts/python.exe; fi
FAIL=0
say() { printf "%-46s %s\n" "$1" "$2"; }
check() { if [ "$2" -eq 0 ]; then say "$1" "PASS"; else say "$1" "FAIL"; FAIL=1; fi; }

# 1-2 secret scan: working tree + history
PATTERN='AIza[0-9A-Za-z_\-]{20,}|-----BEGIN( RSA)? PRIVATE KEY|ghp_[0-9A-Za-z]{30,}'
git grep -IlE "$PATTERN" -- . ':!scripts/release_gate.sh' >/dev/null 2>&1; check "secret scan (working tree)" $((! $?))
git log --all -p -- . 2>/dev/null | grep -qE "$PATTERN"; check "secret scan (git history)" $((! $?))

# 3 .env ignored
git check-ignore .env >/dev/null 2>&1; check ".env is gitignored" $?

# 5-7 private media / audio / precise coordinates
git ls-files | grep -qE '^data/raw/|^data/audio/|\.wav$|\.mp3$'; check "no raw/audio media tracked" $((! $?))

# 8 image licences: every tracked media file must have redistribution yes in the manifest
"$PY" - <<'EOF'
import csv, subprocess, sys
rows = {r["path"]: r for r in csv.DictReader(open("data/manifests/species_images.csv"))}
tracked = subprocess.run(["git", "ls-files", "data/demo"], capture_output=True, text=True).stdout.split()
bad = [t for t in tracked if t.endswith((".jpg", ".png")) and rows.get(t, {}).get("redistribution_permission", "yes") != "yes"]
sys.exit(1 if bad else 0)
EOF
check "tracked media licences permit redistribution" $?

# 9 large files
BIG=$(git ls-files | while read -r f; do [ -f "$f" ] && [ "$(stat -c%s "$f")" -gt 104857600 ] && echo "$f"; done)
[ -z "$BIG" ]; check "no tracked files >100MB" $?

# 10-13 local DBs / caches / weights
git ls-files | grep -qE '\.sqlite3$|\.gguf$|\.safetensors$|node_modules/|__pycache__/'; check "no DBs/weights/caches tracked" $((! $?))

# 14 README
grep -q "Lamer Konekte" README.md; check "README present and branded" $?

# 15 tests
(cd backend && "../$PY" -m pytest tests -q >/dev/null 2>&1); check "backend test suite" $?

# 16 frontend build
(cd frontend && npm run build >/dev/null 2>&1); check "frontend production build" $?

# 17 notebooks valid
"$PY" - <<'EOF'
import json, pathlib, sys
try:
    for p in pathlib.Path("kaggle/notebooks").glob("*.ipynb"):
        json.loads(p.read_text())
except Exception:
    sys.exit(1)
EOF
check "notebook JSON validity" $?

# 18 writeup word count
"$PY" scripts/check_writeup_count.py >/dev/null; check "writeup <= 1500 words" $?

# key not in built frontend
! grep -rq "AIza" frontend/dist 2>/dev/null; check "no key material in frontend dist" $?

echo
if [ "$FAIL" -eq 0 ]; then
  echo "RELEASE GATE: ALL CHECKS PASSED — safe to make the repository public."
else
  echo "RELEASE GATE: FAILURES PRESENT — do NOT make the repository public."
fi
exit $FAIL
