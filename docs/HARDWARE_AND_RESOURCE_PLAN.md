# Hardware & Resource Plan

## Host (Windows laptop)
Ryzen 7 6800H (8C/16T) · 16 GB RAM (~15.2 usable) · RTX 3060 Laptop 6 GB VRAM · ~102 GB free of 477 GB.

## Actual dev environment (WSL2 Ubuntu 22.04)
Only **7.4 GiB RAM** is allocated to the WSL VM (~4.7 available) and 209 GB free vdisk; `nvidia-smi` works (full 6 GB VRAM visible). All memory budgeting below uses the WSL numbers, which are stricter than the host's.

## Budgets
- **VRAM:** peak < 5.5 GB (margin for display/CUDA). 4-bit only, batch 1, small context, one model at a time, free memory between runs.
- **RAM:** keep ≥ 3 GB available ⇒ in WSL that means model experiments must stay under ~4 GB RSS. E2B 4-bit is borderline; E4B locally is effectively out. Do not run local inference + frontend build + dataset processing + Docker simultaneously.
- **CPU:** ≤ 8 workers I/O, ≤ 4 workers OpenCV.
- **Storage:** keep ≥ 25 GB free (comfortable: 209 GB free). Model download budget: ≤ 10 GB total, no duplicate variants, delete failed checkpoints, weights never committed, Kaggle outputs outside the public repo (`kaggle/outputs/`, gitignored).
- **Training:** laptop = smoke tests only; real QLoRA on Kaggle GPU.

## Monitoring
- `scripts/check_resources.sh` / `scripts/check_resources.ps1` — one-shot report: RAM, CPU, disk, GPU + VRAM, python/node/model processes.
- `scripts/watch_resources.sh` / `scripts/watch_resources.ps1` — repeat every 5 s.

No device IDs or product IDs appear in public docs.
