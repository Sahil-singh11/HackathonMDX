"""Deterministic port brief — everything the model is NOT allowed to decide.

The division of labour in this pillar is the whole point of it:

* **This module** produces the counts, the ETAs, the ordering and the vessel
  list. Pure functions over stored AIS fields. Same rows in, same brief out.
* **The model** (via `app.inference`) writes prose about that brief and nothing
  else. It never sees a blank page, is never asked for a number, and its output
  is never parsed back into structured data.

`narrative_is_grounded()` enforces the boundary at the output edge rather than
trusting the prompt: any 9-digit identifier in the narrative must be an MMSI we
actually hold. It catches invented *identifiers*, which is the failure that
would matter most to a port officer. It cannot catch invented *prose* — a model
can still describe a busy approach as quiet — which is why the narrative is
labelled advisory and shipped beside the deterministic numbers, never instead
of them.
"""
from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from typing import Iterable, Optional

from app.models.entities import AisPosition
from app.pillars.transport.ais import (ANCHORED_STATUSES, MOORED_STATUSES,
                                       NAV_STATUS, PORT_LOUIS_LAT,
                                       PORT_LOUIS_LON, UNDER_WAY_STATUSES,
                                       haversine_nm, ship_type_label)

PORT_NAME = "Port Louis"
PORT_UNLOCODE = "MUPLU"

# AIS Destination is free text typed by the crew, so it is matched loosely and
# reported verbatim alongside the match. These are the forms actually seen for
# Port Louis; an unmatched destination is never coerced into one.
_PORT_LOUIS_FORMS = {"PORTLOUIS", "PORT LOUIS", "MUPLU", "PLU", "MU PLU", "MUPORTLOUIS"}

APPROACH_RADIUS_NM = 10.0


def _norm_destination(raw: Optional[str]) -> str:
    return re.sub(r"[^A-Z0-9 ]", "", (raw or "").upper()).strip()


def is_bound_for_port_louis(destination: Optional[str]) -> bool:
    norm = _norm_destination(destination)
    if not norm:
        return False
    return norm in _PORT_LOUIS_FORMS or norm.replace(" ", "") in {
        f.replace(" ", "") for f in _PORT_LOUIS_FORMS
    }


def _aware(dt: Optional[datetime]) -> Optional[datetime]:
    if dt is None:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _row_distance_nm(row: AisPosition) -> float:
    return haversine_nm(row.latitude, row.longitude, PORT_LOUIS_LAT, PORT_LOUIS_LON)


def expected_arrivals(rows: Iterable[AisPosition], *, now: datetime,
                      window_hours: int) -> list[dict]:
    """Vessels self-reporting Port Louis with an ETA inside the window.

    Ordered by ETA, then MMSI. Both the filter and the order come from AIS
    fields only — no model input, no heuristic reordering.
    """
    horizon = now + timedelta(hours=window_hours)
    out: list[dict] = []
    for row in rows:
        if not is_bound_for_port_louis(row.destination):
            continue
        eta = _aware(row.eta_utc)
        if eta is None or not (now <= eta <= horizon):
            continue
        out.append({
            "mmsi": row.mmsi,
            "vessel_name": row.ship_name,
            "identity_known": row.ship_name is not None,
            "vessel_type": ship_type_label(row.ship_type_code),
            "nav_status": NAV_STATUS.get(row.nav_status, "unknown") if row.nav_status is not None else "unknown",
            "destination_reported": row.destination,
            "reported_eta_utc": eta.isoformat(),
            "hours_to_reported_eta": round((eta - now).total_seconds() / 3600, 1),
            "distance_nm": _row_distance_nm(row),
            "speed_knots": row.sog_knots,
            "draught_m": row.draught_m,
            "last_seen_utc": (_aware(row.time_utc) or now).isoformat(),
        })
    out.sort(key=lambda a: (a["reported_eta_utc"], a["mmsi"]))
    return out


def congestion(rows: Iterable[AisPosition]) -> dict:
    """Approach-congestion counts. Pure tally over navigational status."""
    rows = list(rows)
    under_way = sum(1 for r in rows if r.nav_status in UNDER_WAY_STATUSES)
    anchored = sum(1 for r in rows if r.nav_status in ANCHORED_STATUSES)
    moored = sum(1 for r in rows if r.nav_status in MOORED_STATUSES)
    within = [r for r in rows if _row_distance_nm(r) <= APPROACH_RADIUS_NM]
    return {
        "vessels_tracked": len(rows),
        "under_way": under_way,
        "at_anchor": anchored,
        "moored": moored,
        "other_or_unknown_status": len(rows) - under_way - anchored - moored,
        "within_approach_radius": len(within),
        "approach_radius_nm": APPROACH_RADIUS_NM,
        "identity_unknown": sum(1 for r in rows if not r.ship_name),
        "note": (
            f"Counts are every vessel in the retention window, tallied by "
            f"AIS navigational status. 'identity_unknown' vessels sent a position "
            f"but no static data, so their name, type, destination and ETA are "
            f"genuinely unknown — they are counted, never named or guessed."
        ),
    }


# Transport-scoped system instruction (decision log 17).
#
# The provider's default is the fisheries catch-assistant instruction, which
# scopes the model to fisher assistance and orders it to "always produce valid
# structured output". Asked for a port brief under that instruction the live
# model refused, in JSON (measured 30 Jul 2026; pinned as a regression test).
# This replaces it for this one call.
#
# Every honesty rule that matters here is restated rather than assumed: the
# caller owns the safety of an instruction it supplies. Nothing below relaxes an
# obligation — it narrows the role and forbids the specific failures this pillar
# can actually produce. The grounding guard still validates whatever comes back.
SYSTEM_INSTRUCTION = """You are a maritime operations analyst writing a short port brief for a human port officer at Port Louis, Mauritius.

WHAT YOU ARE GIVEN
- Vessel counts, expected arrivals, reported ETAs and sea conditions, already computed and already ordered. They are correct. Your job is to describe and reason about them, never to recompute or reorder them.

HARD RULES (never break)
- Use ONLY the vessels, counts, times and conditions supplied in the message. Never add one.
- Never state an MMSI, IMO number or any other identifier.
- Never invent a vessel, a time, a count or a condition.
- ETAs are SELF-REPORTED by vessels over AIS. Say "reported" whenever you mention one. They are not port authority data and not a validated prediction.
- AIS coverage is incomplete, so absence of a vessel is not evidence it is not there. Never imply the list is exhaustive.
- You advise a human officer. Never issue an instruction, a clearance, a berth allocation or an approval.
- Never claim conditions are safe. You may describe them and reason about their operational implications.

OUTPUT — BE BRIEF. This is the hard constraint, not a style note.
- Plain prose. No JSON, no code fences, no headings, no bullet points, no preamble.
- Exactly two short paragraphs separated by a blank line.
- Paragraph 1: AT MOST THREE SENTENCES summarising arrivals and approach congestion.
- Paragraph 2: EXACTLY ONE SENTENCE on operational risk — what the sea state and traffic pattern together mean for berthing and the approach.
- Under 90 words total. An officer reads this between other tasks; a long answer is a worse answer, not a more thorough one."""


def build_prompt(arrivals: list[dict], congestion_summary: dict, conditions: dict,
                 *, window_hours: int, data_kind: str) -> str:
    """The model's entire input. It receives finished numbers and is asked for
    prose about them — never for a count, an ETA, an ordering, or a vessel."""
    lines = [
        f"Port: {PORT_NAME} ({PORT_UNLOCODE}), Mauritius.",
        f"Look-ahead window: next {window_hours} hours.",
        f"Data kind: {data_kind}.",
        "",
        f"EXPECTED ARRIVALS ({len(arrivals)}), already filtered and ordered by reported ETA:",
    ]
    if not arrivals:
        lines.append("  (none in this window)")
    for a in arrivals:
        name = a["vessel_name"] or "identity unknown (position only)"
        lines.append(
            f"  - {name} | type {a['vessel_type']} | reported ETA {a['reported_eta_utc']} "
            f"(in {a['hours_to_reported_eta']} h) | {a['distance_nm']} nm off | "
            f"{a['speed_knots']} kn | status {a['nav_status']}"
        )
    lines += [
        "",
        "APPROACH CONGESTION:",
        f"  vessels tracked {congestion_summary['vessels_tracked']}, "
        f"under way {congestion_summary['under_way']}, "
        f"at anchor {congestion_summary['at_anchor']}, "
        f"moored {congestion_summary['moored']}, "
        f"within {congestion_summary['approach_radius_nm']} nm "
        f"{congestion_summary['within_approach_radius']}, "
        f"identity unknown {congestion_summary['identity_unknown']}",
        "",
        "SEA CONDITIONS at the port approach:",
        f"  wave {conditions.get('wave_height_m')} m, swell {conditions.get('swell_height_m')} m "
        f"at {conditions.get('swell_period_s')} s, sea surface {conditions.get('sea_surface_temperature_c')} C "
        f"(source {conditions.get('source')})",
        "",
        "Write the brief now. AT MOST THREE SENTENCES on arrivals and congestion, "
        "then a blank line, then EXACTLY ONE SENTENCE on operational risk. "
        "Under 90 words total.",
        "",
        "HARD RULES:",
        "- Use ONLY the vessels, counts, times and conditions given above.",
        "- Do NOT state any MMSI, IMO number or identifier.",
        "- Do NOT invent a vessel, a time, or a number that is not above.",
        "- ETAs are self-reported by the vessel over AIS. Say 'reported' when you mention one.",
        "- You are advising a human officer, not issuing an instruction or a clearance.",
        "- No preamble, no headings, no bullet points. Prose only.",
    ]
    return "\n".join(lines)


_NINE_DIGITS = re.compile(r"\b\d{9}\b")

# Markers of the fisheries assistant's structured envelope. The hosted provider's
# chat() injects the catch-assistant SYSTEM_INSTRUCTION, which orders the model to
# "always produce valid structured output matching the requested JSON schema" and
# scopes it to fishers. Asked for a port brief, the live model duly refused AND
# wrapped the refusal in that envelope (measured 30 Jul 2026). Prose is what this
# field promises, so an envelope is a failed narrative, not a narrative.
_ENVELOPE_MARKERS = ('"intent"', '"reply_morisyen"', '"reply"', '"call"')


def narrative_is_grounded(text: str, known_mmsis: set[int]) -> tuple[bool, str]:
    """Reject anything that is not grounded prose about this brief.

    Returns (ok, reason). Three failures are caught, in the order they were
    actually observed:

    1. Empty output.
    2. **Structured output instead of prose** — a JSON object or fenced code
       block, or the fisheries envelope's keys. A refusal rendered as JSON must
       never reach a port officer looking like a narrative.
    3. An invented *identifier*: a 9-digit token that is not an MMSI we hold.

    What it still cannot do is verify the prose itself — a model can describe a
    busy approach as quiet and this returns True. That limit is stated on the
    payload rather than hidden here, which is why the narrative ships beside the
    deterministic numbers and never instead of them.
    """
    if not text or not text.strip():
        return False, "model returned an empty narrative"

    stripped = text.strip()
    if stripped.startswith("```") or stripped.startswith("{") or stripped.startswith("["):
        return False, "model returned structured output (JSON or a code block), not prose"
    if sum(marker in stripped for marker in _ENVELOPE_MARKERS) >= 2:
        return False, "model returned the assistant's structured envelope, not a port narrative"

    for token in _NINE_DIGITS.findall(stripped):
        if int(token) not in known_mmsis:
            return False, f"narrative cited identifier {token}, which is not in the AIS data"
    return True, ""


def deterministic_narrative(arrivals: list[dict], congestion_summary: dict,
                            conditions: dict, *, window_hours: int) -> str:
    """Fallback prose assembled from the same numbers, with no model involved.

    Used when the provider is unavailable or its output fails the grounding
    check. It is deliberately flat: a plainly mechanical paragraph is the
    honest signal that no model reasoned over this, and the payload says so via
    `narrative_source`.
    """
    if arrivals:
        first = arrivals[0]
        who = first["vessel_name"] or f"a vessel of unknown identity ({first['vessel_type']})"
        lead = (f"{len(arrivals)} vessel(s) report Port Louis as their destination within the next "
                f"{window_hours} hours; the earliest is {who}, reported ETA "
                f"{first['reported_eta_utc']}.")
    else:
        lead = f"No vessel in the current AIS window reports a Port Louis ETA in the next {window_hours} hours."
    return (
        f"{lead} {congestion_summary['vessels_tracked']} vessel(s) are tracked in the window: "
        f"{congestion_summary['under_way']} under way, {congestion_summary['at_anchor']} at anchor, "
        f"{congestion_summary['moored']} moored, {congestion_summary['identity_unknown']} without "
        f"identifying static data. Reported sea state at the approach: wave "
        f"{conditions.get('wave_height_m')} m, swell {conditions.get('swell_height_m')} m at "
        f"{conditions.get('swell_period_s')} s. No model reasoned over these figures — this "
        f"summary is assembled mechanically from the AIS and marine fields above."
    )
