#!/usr/bin/env bash
# Poll the training kernel status until it finishes.
set -euo pipefail
command -v kaggle >/dev/null || { echo "BLOCKED: kaggle CLI not installed/authenticated"; exit 1; }
USER=$(kaggle config view 2>/dev/null | grep -oP 'username: \K\S+')
KERNEL="${1:-$USER/lamer-konekte-train-qlora}"
while true; do
  STATUS=$(kaggle kernels status "$KERNEL" 2>&1 | tail -1)
  echo "$(date '+%H:%M:%S') $STATUS"
  case "$STATUS" in
    *complete*|*error*|*cancel*) break ;;
  esac
  sleep 120
done
