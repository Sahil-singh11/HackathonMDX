"""Hash-chain ledger: sealing, tamper detection, and public verification.

The chain's only claim is that a record is unaltered since it was logged, so the
tests that matter are the ones that prove a tamper is CAUGHT and named.
"""
from sqlmodel import Session, select

from app.db.session import get_engine
from app.models.entities import CatchRecord, LedgerEntry
from app.services.ledger import service as ledger


def _new_catch(client, species="octopus_cyanea", length=42.0, count=1, date="2026-07-20"):
    r = client.post("/api/catches", json={
        "confirmed_species_id": species, "measured_length_cm": length,
        "count": count, "capture_date": date, "fishing_area": "Grand Baie lagoon",
    })
    assert r.status_code == 200, r.text
    return r.json()["catch_record_id"]


def test_catch_is_sealed_onto_the_chain(client):
    rid = _new_catch(client)
    body = client.get("/api/ledger").json()
    assert body["count"] == 1
    entry = body["entries"][0]
    assert entry["record_id"] == rid
    assert entry["seq"] == 1
    assert entry["prev_hash"] == ledger.GENESIS_HASH  # genesis link
    assert len(entry["entry_hash"]) == 64


def test_chain_links_each_entry_to_the_previous(client):
    _new_catch(client)
    _new_catch(client, species="naso_unicornis", length=38.0)
    _new_catch(client, species="siganus_sutor", length=24.0)

    entries = client.get("/api/ledger").json()["entries"]
    assert [e["seq"] for e in entries] == [1, 2, 3]
    for prev, nxt in zip(entries, entries[1:]):
        assert nxt["prev_hash"] == prev["entry_hash"]


def test_intact_chain_verifies(client):
    _new_catch(client)
    _new_catch(client, species="naso_unicornis")
    body = client.get("/api/ledger/verify").json()
    assert body["status"] == "intact"
    assert body["entries"] == 2
    assert body["verified_through"] == 2
    assert body["broken_at"] is None


def test_editing_a_sealed_record_is_detected_and_named(client):
    """The core guarantee: silently changing a logged catch breaks verification."""
    _new_catch(client)
    tampered_id = _new_catch(client, species="naso_unicornis", length=38.0)
    _new_catch(client, species="siganus_sutor", length=24.0)
    assert client.get("/api/ledger/verify").json()["status"] == "intact"

    # Edit the record directly in the database, behind the API's back.
    with Session(get_engine()) as s:
        rec = s.get(CatchRecord, tampered_id)
        rec.measured_length_cm = 99.0
        s.add(rec)
        s.commit()

    body = client.get("/api/ledger/verify").json()
    assert body["status"] == "broken"
    assert body["broken_at"]["record_id"] == tampered_id   # names the exact record
    assert body["broken_at"]["reason"] == "record_modified"
    assert body["verified_through"] == 1                    # everything before it still verified


def test_deleting_a_sealed_record_is_detected(client):
    rid = _new_catch(client)
    with Session(get_engine()) as s:
        s.delete(s.get(CatchRecord, rid))
        s.commit()

    body = client.get("/api/ledger/verify").json()
    assert body["status"] == "broken"
    assert body["broken_at"]["reason"] == "record_missing"


def test_rewriting_a_link_is_detected(client):
    _new_catch(client)
    _new_catch(client, species="naso_unicornis")
    with Session(get_engine()) as s:
        e2 = s.exec(select(LedgerEntry).where(LedgerEntry.seq == 2)).first()
        e2.prev_hash = "f" * 64
        s.add(e2)
        s.commit()

    body = client.get("/api/ledger/verify").json()
    assert body["status"] == "broken"
    assert body["broken_at"]["reason"] == "prev_hash_mismatch"


def test_sealing_is_idempotent_per_record(client):
    rid = _new_catch(client)
    with Session(get_engine()) as s:
        rec = s.get(CatchRecord, rid)
        ledger.append_record(s, rec)
        ledger.append_record(s, rec)
    assert client.get("/api/ledger").json()["count"] == 1


def test_rule_recheck_does_not_invalidate_history(client):
    """legal_note/legal_status are not sealed — re-running a rule check must not
    break the chain, or every rules update would invalidate the whole ledger."""
    rid = _new_catch(client)
    with Session(get_engine()) as s:
        rec = s.get(CatchRecord, rid)
        rec.legal_note = "Re-checked against a newer official notice."
        rec.legal_status = "allowed"
        s.add(rec)
        s.commit()
    assert client.get("/api/ledger/verify").json()["status"] == "intact"


def test_empty_chain_reports_empty_not_broken(client):
    body = client.get("/api/ledger/verify").json()
    assert body["status"] == "empty"
    assert body["broken_at"] is None


# --- public certificate verification ---------------------------------------

def test_public_verify_returns_verified_and_states_its_limits(client):
    rid = _new_catch(client)
    body = client.get(f"/api/verify/{rid}").json()
    assert body["verdict"] == "verified"
    assert body["verified"]["species_id"] == "octopus_cyanea"
    assert body["verified"]["ledger_seq"] == 1
    # Must never overclaim: it proves integrity, not truthfulness.
    assert "not_verified" in body and len(body["not_verified"]) >= 3
    assert "does NOT verify" in body["scope_note"]


def test_public_verify_unknown_reference_is_not_found(client):
    body = client.get("/api/verify/does-not-exist").json()
    assert body["verdict"] == "not_found"
    assert "scope_note" in body


def test_public_verify_reports_chain_broken_after_tampering(client):
    rid = _new_catch(client)
    with Session(get_engine()) as s:
        rec = s.get(CatchRecord, rid)
        rec.count = 999
        s.add(rec)
        s.commit()

    body = client.get(f"/api/verify/{rid}").json()
    assert body["verdict"] == "chain_broken"
    assert "changed since it was logged" in body["headline"]


def test_verify_never_claims_legality(client):
    rid = _new_catch(client)
    body = client.get(f"/api/verify/{rid}").json()
    assert body["legal_status_informational"]["note"]
    assert any("legally taken" in n for n in body["not_verified"])


# --- officer submission views ----------------------------------------------

def test_submission_detail_resolves_records_to_ledger_entries(client):
    _new_catch(client, date="2026-07-20")
    _new_catch(client, species="naso_unicornis", date="2026-07-21")
    prep = client.post("/api/declarations/prepare", data={
        "fisher_name": "Test", "fishing_area": "Grand Baie lagoon",
        "period_start": "2026-07-01", "period_end": "2026-07-31"}).json()

    body = client.get(f"/api/submissions/{prep['declaration_id']}").json()
    assert len(body["records"]) == 2
    assert all(r["sealed"] for r in body["records"])
    assert all(r["ledger_seq"] is not None for r in body["records"])
    assert body["chain"]["status"] == "intact"
    assert "MOCK" in body["mock_label"]
    assert "advisory-assisted" in body["officer_action_note"]


def test_submissions_list_is_labelled_mock(client):
    _new_catch(client)
    client.post("/api/declarations/prepare", data={
        "period_start": "2026-07-01", "period_end": "2026-07-31"})
    body = client.get("/api/submissions").json()
    assert body["count"] == 1
    assert "MOCK" in body["mock_label"]
    assert body["submissions"][0]["record_count"] == 1


def test_demo_reset_clears_the_ledger(client):
    """A reset that wiped records but kept the chain would report broken forever."""
    _new_catch(client)
    assert client.get("/api/ledger").json()["count"] == 1
    client.post("/api/demo/reset")
    assert client.get("/api/ledger").json()["count"] == 0
    assert client.get("/api/ledger/verify").json()["status"] == "empty"
