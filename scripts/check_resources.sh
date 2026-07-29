#!/usr/bin/env bash
# One-shot resource report (WSL/Linux). No secrets, no device IDs.
set -u
echo "=== Lamer Konekte resource check — $(date '+%Y-%m-%d %H:%M:%S %Z') ==="
echo "--- RAM ---"
free -h
echo "--- CPU (1/5/15 min load, $(nproc) logical cores) ---"
uptime
echo "--- Disk ---"
df -h / | tail -1
echo "--- NVIDIA GPU / VRAM ---"
if command -v nvidia-smi >/dev/null 2>&1; then
  nvidia-smi --query-gpu=name,memory.total,memory.used,utilization.gpu --format=csv,noheader
else
  echo "nvidia-smi not available"
fi
echo "--- Python processes ---"
pgrep -af python | grep -v "pgrep" || echo "(none)"
echo "--- Node processes ---"
pgrep -af node | grep -v "pgrep" || echo "(none)"
echo "--- Model-related processes (llama/gguf/transformers/uvicorn) ---"
ps -eo pid,rss,comm,args --sort=-rss | grep -iE "llama|gguf|transformers|torch|uvicorn" | grep -v grep || echo "(none)"
