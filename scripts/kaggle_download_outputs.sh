#!/usr/bin/env bash
# Download training logs + adapter outputs into kaggle/outputs/ (gitignored — never in the public repo).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
command -v kaggle >/dev/null || { echo "BLOCKED: kaggle CLI not installed/authenticated"; exit 1; }
USER=$(kaggle config view 2>/dev/null | grep -oP 'username: \K\S+')
KERNEL="${1:-$USER/lamer-konekte-train-qlora}"
OUT="$ROOT/kaggle/outputs/$(date +%Y%m%d_%H%M%S)"
mkdir -p "$OUT"
kaggle kernels output "$KERNEL" -p "$OUT"
echo "outputs in $OUT — next: run held-out evaluation (kaggle/notebooks/evaluate_adapter.ipynb)"
