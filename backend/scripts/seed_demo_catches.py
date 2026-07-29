#!/usr/bin/env python3
"""Seed realistic demo catches so History and Declaration screens look alive.

Posts a handful of varied catches to the running backend's /api/catches -
the same manual-logging endpoint the app itself uses (Queue > sync), so
seeded rows go through the identical validation and rule-check path as a
real catch. This does NOT touch the DB directly.

Usage (server must already be running, e.g. `uvicorn app.main:app`):

    cd backend && .venv/bin/python scripts/seed_demo_catches.py
    .venv/bin/python scripts/seed_demo_catches.py --base-url http://127.0.0.1:8000
    .venv/bin/python scripts/seed_demo_catches.py --force   # seed again even if catches exist

Dates are relative to today, so the History screen always shows a
freshly-recent spread no matter what day this is run before the demo.
"""
from __future__ import annotations

import argparse
import sys
from datetime import date, timedelta

import httpx

# (species_id, measured_length_cm, count, days_ago, fishing_area)
# Species ids match the 5-species catalogue in data/manifests/species_images.csv.
# Areas are well-known Mauritius lagoon/coastal towns - plausible free-text a
# fisher would type, not real catch coordinates.
SEED_CATCHES: list[tuple[str, float, int, int, str]] = [
    ("octopus_cyanea", 42.0, 1, 9, "Grand Baie lagoon"),
    ("naso_unicornis", 38.0, 2, 8, "Flic-en-Flac reef"),
    ("lethrinus_nebulosus", 34.0, 1, 8, "Mahebourg bay"),
    ("siganus_sutor", 24.0, 3, 7, "Trou aux Biches"),
    ("epinephelus_merra", 22.0, 1, 6, "Blue Bay"),
    ("octopus_cyanea", 37.0, 2, 5, "Grand Baie lagoon"),
    ("naso_unicornis", 44.0, 1, 4, "Flic-en-Flac reef"),
    ("lethrinus_nebulosus", 41.0, 1, 3, "Poste Lafayette"),
    ("siganus_sutor", 27.0, 2, 2, "Mahebourg bay"),
    ("epinephelus_merra", 26.0, 1, 1, "Grand Baie lagoon"),
    ("octopus_cyanea", 49.0, 1, 0, "Flic-en-Flac reef"),
    ("naso_unicornis", 33.0, 3, 0, "Trou aux Biches"),
]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base-url", default="http://127.0.0.1:8000", help="Running backend base URL")
    ap.add_argument("--force", action="store_true", help="Seed even if catches already exist")
    args = ap.parse_args()

    with httpx.Client(base_url=args.base_url, timeout=10) as client:
        try:
            existing = client.get("/api/catches", params={"limit": 200}).json()["catches"]
        except httpx.ConnectError:
            print(f"Could not reach {args.base_url} - is the backend running?", file=sys.stderr)
            return 1

        if existing and not args.force:
            print(f"{len(existing)} catch(es) already exist at {args.base_url} - skipping (use --force to add more).")
            return 0

        today = date.today()
        created = 0
        for species_id, length_cm, count, days_ago, area in SEED_CATCHES:
            capture_date = (today - timedelta(days=days_ago)).isoformat()
            r = client.post("/api/catches", json={
                "confirmed_species_id": species_id,
                "measured_length_cm": length_cm,
                "count": count,
                "capture_date": capture_date,
                "fishing_area": area,
            })
            if r.status_code != 200:
                print(f"  FAILED  {species_id} {capture_date} ({area}): {r.status_code} {r.text}", file=sys.stderr)
                continue
            body = r.json()
            print(f"  seeded  {capture_date}  {species_id:<20} x{count}  {length_cm:>5.1f} cm  "
                 f"{area:<20} -> {body['legal_check']['status']}")
            created += 1

        print(f"\n{created}/{len(SEED_CATCHES)} catches seeded at {args.base_url}.")
        return 0 if created == len(SEED_CATCHES) else 1


if __name__ == "__main__":
    raise SystemExit(main())
