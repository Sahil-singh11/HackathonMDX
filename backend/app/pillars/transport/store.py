"""Capped rolling store for AIS observations.

Two bounds, both enforced on every write, because either one alone leaks:

* **A time window** (`TRANSPORT_AIS_RETENTION_MINUTES`) keeps the brief about
  *recent* traffic. Without it a vessel that left yesterday still counts.
* **A row cap** (`TRANSPORT_AIS_MAX_ROWS`) is the disk bound. A busy feed can
  produce thousands of messages inside the time window, so the window alone
  does not bound the file — and this app ships as a single SQLite file on a
  small instance.

Pruning runs inside the same transaction as the insert, so the invariant holds
after every write rather than depending on a sweeper task that might not be
running. That costs one DELETE per batch, which is the right trade at this
scale.

Demo reset **does** clear this table (decided deliberately — see
`docs/DECISION_LOG.md` and the Task 4b PR body). Rationale: `/api/demo/reset`
exists to make the demo repeatable, and a brief still showing vessels from a
previous run has no other way to be cleared. Nothing is lost by clearing it —
with the collector running the window refills from the live feed within
seconds, and with the synthetic seed it is re-seeded on the next request.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Iterable, Optional

from sqlalchemy import delete
from sqlmodel import Session, select

from app.core.config import get_settings
from app.models.entities import AisPosition
from app.pillars.transport.ais import AisObservation


def _naive_utc(dt: datetime) -> datetime:
    """SQLite round-trips datetimes without tzinfo; compare on one footing.

    The existing marine cache hit exactly this (see services/marine/client.py):
    comparing a tz-aware `datetime.now(timezone.utc)` against a naive column
    value raises TypeError at runtime, not at import.
    """
    return dt.replace(tzinfo=None) if dt.tzinfo else dt


def to_rows(observations: Iterable[AisObservation], data_kind: str,
            received_at: Optional[datetime] = None) -> list[AisPosition]:
    stamp = received_at or datetime.now(timezone.utc)
    return [
        AisPosition(
            mmsi=o.mmsi, received_at=stamp, time_utc=o.time_utc,
            latitude=o.latitude, longitude=o.longitude,
            nav_status=o.nav_status, sog_knots=o.sog_knots, cog_degrees=o.cog_degrees,
            ship_name=o.ship_name, ship_type_code=o.ship_type_code,
            destination=o.destination, eta_utc=o.eta_utc, draught_m=o.draught_m,
            data_kind=data_kind,
        )
        for o in observations
    ]


def prune(session: Session, *, now: Optional[datetime] = None) -> int:
    """Enforce both bounds. Returns how many rows were removed."""
    settings = get_settings()
    reference = _naive_utc(now or datetime.now(timezone.utc))
    cutoff = reference - timedelta(minutes=settings.transport_ais_retention_minutes)

    removed = 0
    stale = session.exec(select(AisPosition).where(AisPosition.received_at < cutoff)).all()
    for row in stale:
        session.delete(row)
        removed += 1
    if removed:
        session.flush()

    cap = max(0, settings.transport_ais_max_rows)
    total = len(session.exec(select(AisPosition.id)).all())
    if cap and total > cap:
        # Oldest first, keeping the newest `cap` rows. Ordered explicitly by
        # (received_at, id) so the eviction set is deterministic when a batch
        # of rows shares one received_at — which is the normal case here.
        doomed = session.exec(
            select(AisPosition.id)
            .order_by(AisPosition.received_at, AisPosition.id)  # type: ignore[arg-type]
            .limit(total - cap)
        ).all()
        if doomed:
            session.exec(delete(AisPosition).where(AisPosition.id.in_(doomed)))  # type: ignore[attr-defined]
            removed += len(doomed)
    return removed


def record(session: Session, observations: Iterable[AisObservation], data_kind: str,
           *, now: Optional[datetime] = None) -> int:
    """Insert observations, then prune. Returns the number inserted."""
    rows = to_rows(observations, data_kind, received_at=now)
    for row in rows:
        session.add(row)
    session.flush()
    prune(session, now=now)
    session.commit()
    return len(rows)


def latest_per_vessel(session: Session, *, now: Optional[datetime] = None) -> list[AisPosition]:
    """Most recent in-window row per MMSI, nearest-port-first ordering applied
    by the caller. Rows outside the retention window are never returned even if
    a prune has not run yet, so a stale read cannot outlive the window."""
    settings = get_settings()
    reference = _naive_utc(now or datetime.now(timezone.utc))
    cutoff = reference - timedelta(minutes=settings.transport_ais_retention_minutes)

    rows = session.exec(
        select(AisPosition).where(AisPosition.received_at >= cutoff)
    ).all()
    newest: dict[int, AisPosition] = {}
    for row in rows:
        seen = newest.get(row.mmsi)
        if seen is None or (row.time_utc, row.received_at) >= (seen.time_utc, seen.received_at):
            newest[row.mmsi] = row
    return list(newest.values())


def clear(session: Session) -> None:
    """Drop every stored position. Called by /api/demo/reset."""
    session.exec(delete(AisPosition))
    session.commit()
