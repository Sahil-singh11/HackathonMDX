"""Per-request provider recording + the additive schema migration (Task 1a).

Covers amendment 2 explicitly: the startup ALTER is idempotent (schema is
inspected first), with a fresh-clone boot test and an existing-DB boot test,
plus confirmation that /api/demo/reset still behaves.
"""
from __future__ import annotations

import tempfile
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlmodel import SQLModel

from app.db.session import ensure_catchrecord_analysis_provider

# Representative pre-Task-1a DDL: catchrecord WITHOUT analysis_provider.
LEGACY_CATCHRECORD_DDL = """
CREATE TABLE catchrecord (
    id VARCHAR NOT NULL PRIMARY KEY,
    analysis_id VARCHAR,
    species_id VARCHAR NOT NULL,
    measured_length_cm FLOAT,
    count INTEGER NOT NULL,
    capture_date VARCHAR NOT NULL,
    fishing_area VARCHAR NOT NULL,
    latitude_rounded FLOAT,
    longitude_rounded FLOAT,
    legal_status VARCHAR NOT NULL,
    legal_rule_id VARCHAR,
    legal_note VARCHAR NOT NULL,
    created_at DATETIME NOT NULL
)
"""


def _columns(engine) -> set[str]:
    with engine.connect() as conn:
        return {row[1] for row in conn.exec_driver_sql("PRAGMA table_info(catchrecord)")}


# ------------------------------------------------------------------ migration

def test_fresh_clone_boot_creates_the_column():
    with tempfile.TemporaryDirectory() as td:
        engine = create_engine(f"sqlite:///{Path(td) / 'fresh.sqlite3'}")
        try:
            from app.models import entities  # noqa: F401 — register tables
            SQLModel.metadata.create_all(engine)
            ensure_catchrecord_analysis_provider(engine)
            assert "analysis_provider" in _columns(engine)
        finally:
            # Windows: the pooled SQLite connection must be closed before
            # TemporaryDirectory can unlink the db file.
            engine.dispose()


def test_existing_db_boot_adds_the_column_and_keeps_rows():
    with tempfile.TemporaryDirectory() as td:
        engine = create_engine(f"sqlite:///{Path(td) / 'legacy.sqlite3'}")
        with engine.connect() as conn:
            conn.exec_driver_sql(LEGACY_CATCHRECORD_DDL)
            conn.exec_driver_sql(
                "INSERT INTO catchrecord (id, species_id, count, capture_date, fishing_area, "
                "legal_status, legal_note, created_at) VALUES ('r1', 'octopus_cyanea', 1, "
                "'2026-07-01', 'Grand Baie', 'unknown', '', '2026-07-01 06:00:00')")
            conn.commit()
        assert "analysis_provider" not in _columns(engine)

        try:
            ensure_catchrecord_analysis_provider(engine)

            assert "analysis_provider" in _columns(engine)
            with engine.connect() as conn:
                row = conn.execute(text(
                    "SELECT species_id, analysis_provider FROM catchrecord WHERE id='r1'")).one()
            assert row[0] == "octopus_cyanea"
            assert row[1] is None  # pre-migration rows honestly record no provider
        finally:
            engine.dispose()


def test_migration_is_idempotent():
    with tempfile.TemporaryDirectory() as td:
        engine = create_engine(f"sqlite:///{Path(td) / 'twice.sqlite3'}")
        with engine.connect() as conn:
            conn.exec_driver_sql(LEGACY_CATCHRECORD_DDL)
            conn.commit()
        try:
            ensure_catchrecord_analysis_provider(engine)
            ensure_catchrecord_analysis_provider(engine)  # second run must be a no-op
            assert "analysis_provider" in _columns(engine)
        finally:
            engine.dispose()


def test_migration_noop_before_table_exists():
    with tempfile.TemporaryDirectory() as td:
        engine = create_engine(f"sqlite:///{Path(td) / 'empty.sqlite3'}")
        try:
            ensure_catchrecord_analysis_provider(engine)  # must not raise
        finally:
            engine.dispose()


# ------------------------------------------------------------------ header

def test_analyse_response_carries_provider_header(client):
    r = client.post("/api/analyse-catch", data={"note": "ki pwason sa?", "provider_mode": "mock"})
    assert r.status_code == 200
    assert r.headers.get("X-Inference-Provider") == "mock:none"
    assert r.json()["provider"]["mode"] == "mock"  # header agrees with the body


def test_quality_gate_short_circuit_also_carries_the_header(client):
    import io
    r = client.post("/api/analyse-catch",
                    files={"image": ("junk.jpg", io.BytesIO(b"definitely not an image"), "image/jpeg")})
    assert r.status_code == 200
    assert r.json()["image_quality"]["status"] == "invalid"
    assert r.headers.get("X-Inference-Provider") == "mock:none"


# ------------------------------------------------------------------ catch-record column

def test_confirmed_record_stores_the_analysis_provider(client):
    r = client.post("/api/analyse-catch", data={"note": "mo'nn gagn enn ourite", "provider_mode": "mock"})
    aid = r.json()["analysis_id"]
    body = client.post(f"/api/analyses/{aid}/confirm", json={
        "confirmed_species_id": "octopus_cyanea", "measured_length_cm": 45.0,
        "capture_date": "2026-07-29"}).json()
    rec = client.get(f"/api/catches/{body['catch_record_id']}").json()
    assert rec["analysis_provider"] == "mock:none"


def test_manual_catch_records_no_provider(client):
    body = client.post("/api/catches", json={
        "confirmed_species_id": "naso_unicornis", "measured_length_cm": 40.0,
        "capture_date": "2026-07-29"}).json()
    rec = client.get(f"/api/catches/{body['catch_record_id']}").json()
    assert rec["analysis_provider"] is None  # no model involved — the honest value


# ------------------------------------------------------------------ demo reset unaffected

def test_demo_reset_still_behaves_after_migration(client):
    client.post("/api/catches", json={"confirmed_species_id": "siganus_sutor",
                                      "measured_length_cm": 25.0, "capture_date": "2026-07-29"})
    r = client.post("/api/demo/reset")
    assert r.status_code == 200
    assert client.get("/api/reports/today").json()["total_records"] == 0


# ------------------------------------------------------------------ socket guard proof

def test_socket_guard_blocks_external_hosts():
    import socket

    import httpx
    with __import__("pytest").raises((httpx.ConnectError, OSError, socket.gaierror)):
        httpx.get("https://example.com", timeout=3)
