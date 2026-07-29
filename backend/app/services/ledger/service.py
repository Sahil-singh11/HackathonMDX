"""Append-only hash chain over confirmed catch records.

WHAT THIS PROVES: a record has not been altered or removed since it was logged.
WHAT IT DOES NOT PROVE: that the original claim (species, weight, location) was
true. It is a tamper-evidence mechanism, not a truth oracle — every surface that
displays a verification result must say so plainly.

Design notes:
- Local and centralised. There is no distributed consensus and no blockchain; a
  party with write access to this database could rebuild the whole chain. It
  raises the cost of silent edits, which is the honest claim to make for it.
- Canonical serialisation is sorted-key JSON so the same record always hashes
  identically across machines and Python versions.
"""
from __future__ import annotations

import hashlib
import json

from sqlmodel import Session, select

from app.models.entities import CatchRecord, LedgerEntry

GENESIS_HASH = "0" * 64

# What the chain commits to. Deliberately excludes mutable/derived fields
# (legal_note wording, analysis_id) so that re-running a rule check does not
# invalidate history — only the substantive catch facts are sealed.
SEALED_FIELDS = (
    "id", "species_id", "measured_length_cm", "count",
    "capture_date", "fishing_area", "latitude_rounded", "longitude_rounded",
)


def canonical_payload(record: CatchRecord) -> str:
    return json.dumps(
        {f: getattr(record, f) for f in SEALED_FIELDS},
        sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str,
    )


def payload_hash(record: CatchRecord) -> str:
    return hashlib.sha256(canonical_payload(record).encode("utf-8")).hexdigest()


def compute_entry_hash(seq: int, record_id: str, payload_sha256: str, prev_hash: str) -> str:
    return hashlib.sha256(f"{seq}|{record_id}|{payload_sha256}|{prev_hash}".encode()).hexdigest()


def head(session: Session) -> LedgerEntry | None:
    return session.exec(select(LedgerEntry).order_by(LedgerEntry.seq.desc())).first()  # type: ignore[union-attr]


def append_record(session: Session, record: CatchRecord) -> LedgerEntry:
    """Seal one catch record onto the chain. Idempotent per record_id."""
    existing = session.exec(select(LedgerEntry).where(LedgerEntry.record_id == record.id)).first()
    if existing:
        return existing

    tip = head(session)
    seq = (tip.seq + 1) if tip and tip.seq is not None else 1
    prev = tip.entry_hash if tip else GENESIS_HASH
    p_hash = payload_hash(record)

    entry = LedgerEntry(
        seq=seq, record_id=record.id, payload_sha256=p_hash, prev_hash=prev,
        entry_hash=compute_entry_hash(seq, record.id, p_hash, prev),
    )
    session.add(entry)
    session.commit()
    session.refresh(entry)
    return entry


def entry_for_record(session: Session, record_id: str) -> LedgerEntry | None:
    return session.exec(select(LedgerEntry).where(LedgerEntry.record_id == record_id)).first()


def verify_chain(session: Session) -> dict:
    """Walk the chain from genesis and report the FIRST break with its record.

    Detects: edited record content, a deleted record, a rewritten link, and a
    tampered entry hash. Returns a structure the officer UI can render directly.
    """
    entries = session.exec(select(LedgerEntry).order_by(LedgerEntry.seq)).all()  # type: ignore[arg-type]
    if not entries:
        return {"status": "empty", "entries": 0, "verified_through": 0, "broken_at": None,
                "detail": "No catch records have been sealed onto the ledger yet."}

    expected_prev = GENESIS_HASH
    for idx, e in enumerate(entries, start=1):
        def broken(reason: str, detail: str) -> dict:
            return {"status": "broken", "entries": len(entries), "verified_through": idx - 1,
                    "broken_at": {"seq": e.seq, "record_id": e.record_id, "reason": reason},
                    "detail": detail}

        if e.seq != idx:
            return broken("sequence_gap",
                          f"Expected sequence {idx} but found {e.seq} — an entry was removed or reordered.")
        if e.prev_hash != expected_prev:
            return broken("prev_hash_mismatch",
                          f"Entry {e.seq} does not link to the previous entry — the chain was rewritten here.")
        if compute_entry_hash(e.seq, e.record_id, e.payload_sha256, e.prev_hash) != e.entry_hash:
            return broken("entry_hash_mismatch",
                          f"Entry {e.seq}'s own hash does not match its contents — the entry was tampered with.")

        record = session.get(CatchRecord, e.record_id)
        if record is None:
            return broken("record_missing",
                          f"Catch record {e.record_id} was deleted after being sealed at entry {e.seq}.")
        if payload_hash(record) != e.payload_sha256:
            return broken("record_modified",
                          f"Catch record {e.record_id} was edited after being sealed at entry {e.seq}.")

        expected_prev = e.entry_hash

    return {"status": "intact", "entries": len(entries), "verified_through": len(entries),
            "broken_at": None,
            "detail": f"All {len(entries)} entries verified from genesis. No record has been altered since it was logged."}


def backfill(session: Session) -> int:
    """Seal any pre-existing records that predate the ledger. Returns how many."""
    sealed = {e.record_id for e in session.exec(select(LedgerEntry)).all()}
    rows = session.exec(select(CatchRecord).order_by(CatchRecord.created_at)).all()  # type: ignore[arg-type]
    added = 0
    for r in rows:
        if r.id not in sealed:
            append_record(session, r)
            added += 1
    return added
