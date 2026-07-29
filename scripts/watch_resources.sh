#!/usr/bin/env bash
# Repeat the resource check every N seconds (default 5). Ctrl-C to stop.
INTERVAL="${1:-5}"
while true; do
  clear
  bash "$(dirname "$0")/check_resources.sh"
  sleep "$INTERVAL"
done
