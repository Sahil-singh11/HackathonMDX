#!/usr/bin/env bash
# Push training data (PRIVATE dataset) + QLoRA notebook to Kaggle and start a GPU run.
# Requires: pip install kaggle && ~/.kaggle/kaggle.json (never committed).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
command -v kaggle >/dev/null || { echo "BLOCKED: kaggle CLI not installed/authenticated"; exit 1; }
USER=$(kaggle config view 2>/dev/null | grep -oP 'username: \K\S+' || true)
[ -n "$USER" ] || { echo "BLOCKED: kaggle CLI not authenticated"; exit 1; }

STAGE=$(mktemp -d)
cp "$ROOT"/training/data/{train,validation,test}.jsonl "$STAGE/"
cat > "$STAGE/dataset-metadata.json" <<EOF
{"title": "lamer-konekte-training", "id": "$USER/lamer-konekte-training", "licenses": [{"name": "CC0-1.0"}]}
EOF
kaggle datasets create -p "$STAGE" --dir-mode zip 2>/dev/null || kaggle datasets version -p "$STAGE" -m "update $(date -Iseconds)" --dir-mode zip
echo "private dataset pushed: $USER/lamer-konekte-training"

NB=$(mktemp -d)
cp "$ROOT/kaggle/notebooks/train_gemma4_qlora.ipynb" "$NB/"
cat > "$NB/kernel-metadata.json" <<EOF
{"id": "$USER/lamer-konekte-train-qlora", "title": "lamer-konekte-train-qlora",
 "code_file": "train_gemma4_qlora.ipynb", "language": "python", "kernel_type": "notebook",
 "is_private": true, "enable_gpu": true, "enable_internet": true,
 "dataset_sources": ["$USER/lamer-konekte-training"], "kernel_sources": [], "competition_sources": []}
EOF
kaggle kernels push -p "$NB"
echo "training notebook pushed and started: $USER/lamer-konekte-train-qlora"
echo "monitor with: scripts/kaggle_monitor_training.sh"
