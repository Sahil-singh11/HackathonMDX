"""AIS message normalisation — aisstream.io v0 envelopes in, flat records out.

Nothing in this module knows or cares whether a message arrived over a live
WebSocket or was read from the committed synthetic file: the envelope shape is
identical, so the same parser serves both and the synthetic path exercises the
real code rather than a fixture-shaped shortcut.

Two AIS facts drive most of the awkwardness here, and both are real:

1. **A position report carries no name, type, destination or ETA.** Those live
   in ShipStaticData, which is broadcast far less often. A vessel is routinely
   visible as a position and an MMSI and nothing else. We keep those vessels and
   report what we do not know, rather than dropping them (which would understate
   congestion) or guessing (which would be a lie).
2. **An AIS ETA has no year.** The field is Month/Day/Hour/Minute, so the year
   has to be inferred; we resolve to the nearest occurrence around the reference
   clock. The "not available" sentinel is Month=0/Day=0/Hour=24/Minute=60, and
   vessels genuinely send it — an unresolvable ETA is normal, not an error.
"""
from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

# Port Louis harbour entrance. Distances in the brief are great-circle from
# here — an approach distance, deliberately not a routed sailing distance.
PORT_LOUIS_LAT = -20.1580
PORT_LOUIS_LON = 57.4880

# ITU-R M.1371 navigational status codes. Only the ones we act on are named;
# anything else stays a number so we never invent a meaning we did not decode.
NAV_STATUS = {
    0: "under way using engine",
    1: "at anchor",
    2: "not under command",
    3: "restricted manoeuvrability",
    4: "constrained by draught",
    5: "moored",
    6: "aground",
    7: "engaged in fishing",
    8: "under way sailing",
    15: "undefined",
}

UNDER_WAY_STATUSES = {0, 8}
ANCHORED_STATUSES = {1}
MOORED_STATUSES = {5}


def ship_type_label(code: Optional[int]) -> str:
    """ITU-R M.1371 ship-and-cargo type code -> coarse label.

    Deliberately coarse: the code's second digit encodes cargo hazard classes
    we have no business interpreting for a port brief. An unmapped or missing
    code returns "unknown" — never a guess.
    """
    if code is None:
        return "unknown"
    if code == 30:
        return "fishing"
    if code in (31, 32, 52):
        return "tug or towing"
    if code == 35:
        return "military"
    if code == 36:
        return "sailing"
    if code == 37:
        return "pleasure craft"
    if code in (50, 51, 53, 55):
        return "service or patrol"
    if 40 <= code <= 49:
        return "high-speed craft"
    if 60 <= code <= 69:
        return "passenger"
    if 70 <= code <= 79:
        return "cargo"
    if 80 <= code <= 89:
        return "tanker"
    return "unknown"


@dataclass(frozen=True)
class AisObservation:
    """One vessel as last seen. Every optional field is genuinely optional."""

    mmsi: int
    latitude: float
    longitude: float
    time_utc: datetime
    nav_status: Optional[int] = None
    sog_knots: Optional[float] = None
    cog_degrees: Optional[float] = None
    ship_name: Optional[str] = None
    ship_type_code: Optional[int] = None
    destination: Optional[str] = None
    eta_utc: Optional[datetime] = None
    draught_m: Optional[float] = None

    @property
    def nav_status_label(self) -> str:
        if self.nav_status is None:
            return "unknown"
        return NAV_STATUS.get(self.nav_status, f"code {self.nav_status}")

    @property
    def ship_type_label(self) -> str:
        return ship_type_label(self.ship_type_code)

    @property
    def distance_nm(self) -> float:
        return haversine_nm(self.latitude, self.longitude, PORT_LOUIS_LAT, PORT_LOUIS_LON)


def haversine_nm(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in nautical miles."""
    r_nm = 3440.065
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return round(2 * r_nm * math.asin(math.sqrt(a)), 2)


_GO_TIME = re.compile(
    r"^(\d{4}-\d{2}-\d{2})[ T](\d{2}:\d{2}:\d{2})(?:\.(\d+))?\s*([+-]\d{4})?(?:\s+\w+)?$"
)


def parse_time_utc(raw: Any) -> Optional[datetime]:
    """Parse aisstream's `MetaData.time_utc` (Go time.String() layout).

    Example: `2026-07-30 07:59:12.418000000 +0000 UTC`. Python's %f tops out at
    six digits, so nanoseconds are truncated rather than handed to strptime,
    which would raise on the full nine.
    """
    if isinstance(raw, datetime):
        return raw if raw.tzinfo else raw.replace(tzinfo=timezone.utc)
    if not isinstance(raw, str) or not raw.strip():
        return None
    m = _GO_TIME.match(raw.strip())
    if not m:
        try:
            dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except ValueError:
            return None
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    date_s, time_s, frac, offset = m.groups()
    micros = int((frac or "0")[:6].ljust(6, "0"))
    dt = datetime.strptime(f"{date_s} {time_s}", "%Y-%m-%d %H:%M:%S").replace(microsecond=micros)
    if offset and offset != "+0000":
        sign = 1 if offset[0] == "+" else -1
        delta = timedelta(hours=int(offset[1:3]), minutes=int(offset[3:5]))
        dt = dt - sign * delta
    return dt.replace(tzinfo=timezone.utc)


def resolve_eta(eta: Any, reference: datetime) -> Optional[datetime]:
    """AIS Eta{Month,Day,Hour,Minute} -> absolute UTC, or None.

    The year is not transmitted, so it is inferred: we take the occurrence
    nearest the reference clock, which keeps a 31 December ETA read on
    1 January from landing eleven months in the past. Returns None for the
    documented "not available" sentinel and for anything that is not a real
    calendar instant — an unknown ETA is a normal AIS outcome and the caller
    reports it as unknown rather than substituting one.
    """
    if not isinstance(eta, dict):
        return None
    try:
        month = int(eta.get("Month", 0))
        day = int(eta.get("Day", 0))
        hour = int(eta.get("Hour", 24))
        minute = int(eta.get("Minute", 60))
    except (TypeError, ValueError):
        return None
    if month == 0 or day == 0 or hour > 23 or minute > 59:
        return None  # documented "not available"
    best: Optional[datetime] = None
    for year in (reference.year - 1, reference.year, reference.year + 1):
        try:
            candidate = datetime(year, month, day, hour, minute, tzinfo=timezone.utc)
        except ValueError:
            continue  # e.g. 29 February in a non-leap year
        if best is None or abs(candidate - reference) < abs(best - reference):
            best = candidate
    return best


def normalise(messages: list[dict], reference: datetime) -> list[AisObservation]:
    """Fold a stream of envelopes into one observation per MMSI.

    Position and static data arrive as separate messages, so they are merged
    per vessel: latest position wins for location, latest static data wins for
    identity. A vessel with position but no static data survives the merge with
    its identity fields left None.
    """
    latest_pos: dict[int, dict] = {}
    latest_static: dict[int, dict] = {}

    for env in messages:
        if not isinstance(env, dict):
            continue
        meta = env.get("MetaData") or {}
        mmsi = meta.get("MMSI")
        if not isinstance(mmsi, int):
            continue
        kind = env.get("MessageType")
        body = (env.get("Message") or {}).get(kind) or {}
        stamp = parse_time_utc(meta.get("time_utc"))
        if stamp is None:
            continue
        entry = {"meta": meta, "body": body, "time": stamp}
        if kind == "PositionReport":
            if mmsi not in latest_pos or stamp >= latest_pos[mmsi]["time"]:
                latest_pos[mmsi] = entry
        elif kind == "ShipStaticData":
            if mmsi not in latest_static or stamp >= latest_static[mmsi]["time"]:
                latest_static[mmsi] = entry

    out: list[AisObservation] = []
    for mmsi, pos in latest_pos.items():
        body, meta = pos["body"], pos["meta"]
        static = latest_static.get(mmsi)
        sbody = static["body"] if static else {}

        name = (sbody.get("Name") or meta.get("ShipName") or "").strip() or None
        destination = (sbody.get("Destination") or "").strip() or None
        ship_type = sbody.get("Type")
        draught = sbody.get("MaximumStaticDraught")

        out.append(AisObservation(
            mmsi=mmsi,
            latitude=float(body.get("Latitude", meta.get("latitude", 0.0))),
            longitude=float(body.get("Longitude", meta.get("longitude", 0.0))),
            time_utc=pos["time"],
            nav_status=body.get("NavigationalStatus"),
            sog_knots=body.get("Sog"),
            cog_degrees=body.get("Cog"),
            ship_name=name,
            ship_type_code=int(ship_type) if isinstance(ship_type, int) else None,
            destination=destination,
            eta_utc=resolve_eta(sbody.get("Eta"), reference),
            draught_m=float(draught) if isinstance(draught, (int, float)) and draught else None,
        ))
    # Deterministic order regardless of dict iteration: nearest port first,
    # MMSI as the tiebreak. Ordering is data, never model output.
    out.sort(key=lambda o: (o.distance_nm, o.mmsi))
    return out


def load_synthetic(path: Path, reference: datetime) -> tuple[list[dict], datetime]:
    """Read the committed synthetic capture and rebase its clock.

    Every timestamp is shifted by ONE constant delta so the newest message
    lands on `reference`, which preserves the exact spacing between messages
    while keeping the fixture usable on any date. Returns the rebased envelopes
    plus the file's declared reference instant, so the caller can say in the
    provenance what it did. ETAs are left untouched — they carry no year and
    are resolved against the rebased clock by `resolve_eta`, which is the same
    thing a live feed requires.
    """
    raw = json.loads(path.read_text(encoding="utf-8"))
    messages = raw.get("messages") or []
    declared = parse_time_utc(raw.get("_reference_utc")) or reference

    stamps = [parse_time_utc((m.get("MetaData") or {}).get("time_utc")) for m in messages]
    newest = max([s for s in stamps if s is not None], default=None)
    if newest is None:
        return messages, declared
    delta = reference - newest

    rebased: list[dict] = []
    for env, stamp in zip(messages, stamps):
        if stamp is None:
            continue
        shifted = dict(env)
        meta = dict(shifted.get("MetaData") or {})
        meta["time_utc"] = (stamp + delta).isoformat()
        shifted["MetaData"] = meta
        rebased.append(shifted)
    return rebased, declared
