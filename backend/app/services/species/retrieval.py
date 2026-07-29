"""Species catalogue + candidate retrieval. Gemma only ever sees a shortlist."""
from __future__ import annotations

import json
from functools import lru_cache

from app.core.config import get_settings

MAX_CANDIDATES = 6


@lru_cache
def load_catalogue() -> list[dict]:
    path = get_settings().data_dir / "processed" / "species_catalogue.json"
    with open(path, encoding="utf-8") as f:
        return json.load(f)["species"]


def get_species(species_id: str) -> dict | None:
    return next((s for s in load_catalogue() if s["species_id"] == species_id), None)


def candidates_for(note: str | None = None) -> list[dict]:
    """Keyword-scored shortlist. With no note, the full (small) P0 catalogue is the shortlist."""
    cat = load_catalogue()
    if not note:
        return cat[:MAX_CANDIDATES]
    text = note.lower()
    scored = []
    for sp in cat:
        score = sum(1 for kw in sp["keywords"] if kw.lower() in text)
        scored.append((score, sp))
    scored.sort(key=lambda t: -t[0])
    top = [sp for score, sp in scored if score > 0]
    return (top or cat)[:MAX_CANDIDATES]


def public_candidate(sp: dict) -> dict:
    """The candidate payload shared with the model and the UI."""
    return {
        "species_id": sp["species_id"],
        "scientific": sp["scientific"],
        "english": sp["english"],
        "morisyen": sp["morisyen"],
        "morisyen_status": sp["morisyen_status"],
        "visible_characteristics": sp["visible_characteristics"],
    }
