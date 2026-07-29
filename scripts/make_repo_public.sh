#!/usr/bin/env bash
# Flip the repository to PUBLIC — only after scripts/release_gate.sh passes.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
bash scripts/release_gate.sh || { echo "ABORT: release gate failed"; exit 1; }

git push origin main
# gh 2.4.0 lacks `gh repo edit` — use the REST API directly.
gh api -X PATCH repos/Sahil-singh11/HackathonMDX -F private=false >/dev/null && echo "repository set to PUBLIC"
git tag -f hackathon-submission-v1 && git push -f origin hackathon-submission-v1
echo "verify without login: https://github.com/Sahil-singh11/HackathonMDX"
curl -s -o /dev/null -w "unauthenticated fetch status: %{http_code}\n" https://github.com/Sahil-singh11/HackathonMDX
