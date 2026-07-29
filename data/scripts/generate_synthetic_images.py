#!/usr/bin/env python3
"""Generate synthetic quality-test images (safe to redistribute, MIT).

Creates in data/demo/synthetic/: sharp reference, blurred, dark, overexposed,
tiny, and an invalid 'not-a-photo' text image, plus a non-image file for MIME
tests. Adds manifest rows (platform=synthetic, licence=MIT).
"""
from __future__ import annotations

import csv
import hashlib
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data" / "demo" / "synthetic"
MANIFEST = ROOT / "data" / "manifests" / "species_images.csv"

FIELDS = [
    "path", "species_id", "scientific_name", "english_name", "morisyen_name",
    "platform", "observation_id", "source_url", "media_url", "creator",
    "licence", "licence_url", "locality", "date", "sha256", "split",
    "redistribution_permission", "notes",
]


def base_scene() -> Image.Image:
    """A simple high-detail fish-on-deck style scene (texture for blur metrics)."""
    rng = np.random.default_rng(42)
    arr = (rng.integers(60, 200, (480, 640, 3))).astype(np.uint8)
    img = Image.fromarray(arr)
    d = ImageDraw.Draw(img)
    d.ellipse([140, 160, 500, 320], fill=(180, 190, 205), outline=(30, 40, 60), width=4)
    d.polygon([(500, 240), (590, 180), (590, 300)], fill=(160, 170, 185))
    d.ellipse([190, 210, 220, 240], fill=(20, 20, 30))
    for x in range(160, 480, 24):
        d.arc([x, 180, x + 40, 300], 300, 60, fill=(120, 130, 150), width=2)
    return img


def save(img: Image.Image, name: str, note: str, rows: list[dict]) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    p = OUT / name
    img.save(p, quality=90)
    sha = hashlib.sha256(p.read_bytes()).hexdigest()
    rows.append({
        "path": str(p.relative_to(ROOT)), "species_id": "n/a",
        "scientific_name": "n/a", "english_name": "synthetic test image",
        "morisyen_name": "n/a", "platform": "synthetic", "observation_id": "",
        "source_url": "", "media_url": "", "creator": "Team Ctrl200 (generated)",
        "licence": "MIT", "licence_url": "https://opensource.org/licenses/MIT",
        "locality": "", "date": "2026-07-29", "sha256": sha,
        "split": "quality_test", "redistribution_permission": "yes", "notes": note,
    })


def main() -> None:
    rows: list[dict] = []
    scene = base_scene()
    save(scene, "sharp.jpg", "sharp reference", rows)
    save(scene.filter(ImageFilter.GaussianBlur(8)), "blurry.jpg", "blur variant", rows)
    save(Image.eval(scene, lambda v: v // 5), "dark.jpg", "underexposed variant", rows)
    save(Image.eval(scene, lambda v: min(255, v + 140)), "overexposed.jpg", "overexposed variant", rows)
    save(scene.resize((40, 30)), "tiny.jpg", "too-small variant", rows)
    txt = Image.new("RGB", (640, 480), (250, 250, 250))
    d = ImageDraw.Draw(txt)
    for y in range(40, 460, 28):
        d.line([(40, y), (600, y)], fill=(80, 80, 80), width=2)
    save(txt, "not_a_catch.jpg", "invalid subject (document-like)", rows)
    (OUT / "not_an_image.txt").write_text("this is not an image\n")

    existing: dict[str, dict] = {}
    if MANIFEST.exists():
        with open(MANIFEST, newline="") as f:
            existing = {r["sha256"]: r for r in csv.DictReader(f)}
    for r in rows:
        existing[r["sha256"]] = r
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    with open(MANIFEST, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(existing.values())
    print(f"synthetic set written to {OUT}; manifest now {len(existing)} rows")


if __name__ == "__main__":
    main()
