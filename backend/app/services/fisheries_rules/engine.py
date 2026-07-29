"""Deterministic fisheries rule engine.

Hard guarantees:
- Only runs on a CONFIRMED species with measured_length_cm (never AI estimates).
- Rules are versioned + source-attributed (data/rules/species_rules.json).
- Missing / ambiguous / unverified-value rules => `unknown`.
- Every result carries the official-verification notice.
"""
from __future__ import annotations

import json
from datetime import date
from functools import lru_cache

from app.core.config import get_settings
from app.core.limitations import RULE_VERIFY_NOTICE
from app.schemas.analysis import LegalCheck


@lru_cache
def load_rules() -> list[dict]:
    path = get_settings().data_dir / "rules" / "species_rules.json"
    with open(path, encoding="utf-8") as f:
        return json.load(f)["rules"]


def _in_window(d: date, mm_dd_from: str, mm_dd_to: str) -> bool:
    fm, fd = (int(x) for x in mm_dd_from.split("-"))
    tm, td = (int(x) for x in mm_dd_to.split("-"))
    start = (fm, fd)
    end = (tm, td)
    cur = (d.month, d.day)
    if start <= end:
        return start <= cur <= end
    return cur >= start or cur <= end  # wraps the year end


def check_confirmed_catch(species_id: str, measured_length_cm: float | None, capture_date: date) -> LegalCheck:
    rules = [r for r in load_rules() if r["species_id"] == species_id and r["rule_type"] != "historical_note"]
    if not rules:
        return LegalCheck(status="unknown", rule=None, source_id=None, verification_status="unavailable",
                          note=f"No rule on record for this species. {RULE_VERIFY_NOTICE}")

    for r in rules:
        if r["rule_type"] == "seasonal_closure":
            if r.get("verification_status") not in ("provisional", "verified"):
                continue
            if _in_window(capture_date, r["closed_from"], r["closed_to"]):
                return LegalCheck(
                    status="closed_season", rule=r["rule_id"], source_id=r.get("source_id"),
                    verification_status=r.get("verification_status"),
                    note=f"{r.get('note', '')} {RULE_VERIFY_NOTICE}".strip(),
                )

    for r in rules:
        if r["rule_type"] == "minimum_size":
            if r.get("minimum_length_cm") is None or r.get("verification_status") == "unavailable":
                return LegalCheck(status="unknown", rule=r["rule_id"], source_id=r.get("source_id"),
                                  verification_status=r.get("verification_status", "unavailable"),
                                  note=f"{r.get('note', '')} {RULE_VERIFY_NOTICE}".strip())
            if measured_length_cm is None:
                return LegalCheck(status="unknown", rule=r["rule_id"], source_id=r.get("source_id"),
                                  verification_status=r.get("verification_status"),
                                  note=f"Measured length required for this rule. {RULE_VERIFY_NOTICE}")
            if measured_length_cm < float(r["minimum_length_cm"]):
                return LegalCheck(status="below_minimum_size", rule=r["rule_id"], source_id=r.get("source_id"),
                                  verification_status=r.get("verification_status"),
                                  note=f"{r.get('note', '')} {RULE_VERIFY_NOTICE}".strip())

    # No rule blocked the catch. Only claim `allowed` when at least one evaluable rule existed.
    evaluable = [r for r in rules if r.get("verification_status") in ("provisional", "verified")]
    if evaluable:
        vs = evaluable[0].get("verification_status")
        return LegalCheck(status="allowed", rule=evaluable[0]["rule_id"], source_id=evaluable[0].get("source_id"),
                          verification_status=vs,
                          note=f"No closure or size rule triggered on {capture_date.isoformat()}. {RULE_VERIFY_NOTICE}")
    return LegalCheck(status="unknown", rule=rules[0]["rule_id"], source_id=rules[0].get("source_id"),
                      verification_status=rules[0].get("verification_status", "unavailable"),
                      note=f"{rules[0].get('note', '')} {RULE_VERIFY_NOTICE}".strip())
