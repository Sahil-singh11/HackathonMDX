#!/usr/bin/env python3
"""Fetch licensed iNaturalist photos for the P0 species.

- Accepts ONLY cc0 / cc-by / cc-by-nc photo licences (rejects all-rights-reserved).
- Streams downloads (no batch in memory), max 4 concurrent species, polite rate limit.
- Writes/updates data/manifests/species_images.csv with full attribution.
- Raw files go to data/raw/ (gitignored). Hero picks (cc0/cc-by only) are copied to
  data/demo/ so they can ship in the public repo with attribution.
- Split assignment is by observation id (leakage-safe): hash(observation_id) % 10
  -> 0-6 train, 7 val, 8-9 test. Hero images are excluded from evaluation splits.
"""
from __future__ import annotations

import csv
import hashlib
import json
import shutil
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw"
DEMO = ROOT / "data" / "demo"
MANIFEST = ROOT / "data" / "manifests" / "species_images.csv"

ALLOWED = {"cc0", "cc-by", "cc-by-nc"}
REDISTRIBUTABLE = {"cc0", "cc-by"}
LICENCE_URLS = {
    "cc0": "https://creativecommons.org/publicdomain/zero/1.0/",
    "cc-by": "https://creativecommons.org/licenses/by/4.0/",
    "cc-by-nc": "https://creativecommons.org/licenses/by-nc/4.0/",
}

SPECIES = {
    "octopus_cyanea": ("Octopus cyanea", "Day octopus", "ourite"),
    "lethrinus_nebulosus": ("Lethrinus nebulosus", "Spangled emperor", "kapitenn"),
    "siganus_sutor": ("Siganus sutor", "Shoemaker spinefoot", "kordonye"),
    "epinephelus_merra": ("Epinephelus merra", "Honeycomb grouper", "vye"),
    "naso_unicornis": ("Naso unicornis", "Bluespine unicornfish", "likorn"),
}

FIELDS = [
    "path", "species_id", "scientific_name", "english_name", "morisyen_name",
    "platform", "observation_id", "source_url", "media_url", "creator",
    "licence", "licence_url", "locality", "date", "sha256", "split",
    "redistribution_permission", "notes",
]


def api(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "LamerKonekte/1.0 (hackathon research)"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def split_for(observation_id: int) -> str:
    h = int(hashlib.sha256(str(observation_id).encode()).hexdigest(), 16) % 10
    return "train" if h <= 6 else ("validation" if h == 7 else "test")


def fetch_species(species_id: str, per_species: int, hero_count: int, rows: list[dict]) -> None:
    sci, en, mfe = SPECIES[species_id]
    q = urllib.parse.urlencode({
        "taxon_name": sci,
        "photo_license": "cc0,cc-by,cc-by-nc",
        "quality_grade": "research",
        "per_page": per_species * 2,
        "order_by": "votes",
    })
    data = api(f"https://api.inaturalist.org/v1/observations?{q}")
    got, heroes = 0, 0
    for obs in data.get("results", []):
        if got >= per_species:
            break
        photos = obs.get("photos") or []
        if not photos:
            continue
        p = photos[0]
        lic = (p.get("license_code") or "").lower()
        if lic not in ALLOWED:
            continue
        media_url = (p.get("url") or "").replace("square", "large")
        if not media_url:
            continue
        obs_id = obs["id"]
        fname = f"{species_id}_{obs_id}.jpg"
        dest = RAW / species_id / fname
        dest.parent.mkdir(parents=True, exist_ok=True)
        try:
            req = urllib.request.Request(media_url, headers={"User-Agent": "LamerKonekte/1.0"})
            with urllib.request.urlopen(req, timeout=30) as r, open(dest, "wb") as f:
                shutil.copyfileobj(r, f)  # streamed, not loaded in memory
        except Exception as e:  # noqa: BLE001 - log and continue
            print(f"  skip {obs_id}: {e}", file=sys.stderr)
            continue
        sha = hashlib.sha256(dest.read_bytes()).hexdigest()
        redis = "yes" if lic in REDISTRIBUTABLE else "no"
        is_hero = heroes < hero_count and lic in REDISTRIBUTABLE
        path = str(dest.relative_to(ROOT))
        split = "hero" if is_hero else split_for(obs_id)
        if is_hero:
            hero_dest = DEMO / fname
            hero_dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(dest, hero_dest)
            path = str(hero_dest.relative_to(ROOT))
            heroes += 1
        rows.append({
            "path": path,
            "species_id": species_id,
            "scientific_name": sci,
            "english_name": en,
            "morisyen_name": f"{mfe} (provisional)",
            "platform": "inaturalist",
            "observation_id": obs_id,
            "source_url": f"https://www.inaturalist.org/observations/{obs_id}",
            "media_url": media_url,
            "creator": (obs.get("user") or {}).get("login", "unknown"),
            "licence": lic,
            "licence_url": LICENCE_URLS[lic],
            "locality": (obs.get("place_guess") or "")[:60],
            "date": obs.get("observed_on") or "",
            "sha256": sha,
            "split": split,
            "redistribution_permission": redis,
            "notes": "hero demo image" if is_hero else "",
        })
        got += 1
        time.sleep(0.6)  # polite rate limit
    print(f"{species_id}: {got} images ({heroes} hero)")


def main() -> None:
    per_species = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    hero_count = int(sys.argv[2]) if len(sys.argv) > 2 else 2
    rows: list[dict] = []
    for sid in SPECIES:
        try:
            fetch_species(sid, per_species, hero_count, rows)
        except Exception as e:  # noqa: BLE001
            print(f"{sid}: FAILED {e}", file=sys.stderr)
        time.sleep(1.0)
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    existing: dict[str, dict] = {}
    if MANIFEST.exists():
        with open(MANIFEST, newline="") as f:
            existing = {r["sha256"]: r for r in csv.DictReader(f)}
    for r in rows:
        existing[r["sha256"]] = r
    with open(MANIFEST, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(existing.values())
    print(f"manifest: {len(existing)} rows -> {MANIFEST}")


if __name__ == "__main__":
    main()
