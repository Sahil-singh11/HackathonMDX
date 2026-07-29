"""aisstream.io coverage probe for Port Louis, Mauritius.

Run BEFORE approving a live-collector timebox. Answers one question: does
aisstream currently have receiver coverage near Port Louis? The three boxes
separate the two explanations that a silent stream could otherwise conflate —
"our key or subscription is wrong" and "there is no receiver out there".

RESULT ON RECORD (30 Jul 2026, ~01:45 MUT)

    Port Louis box   [[-20.35, 57.25], [-19.90, 57.75]]   0 messages in 120 s
    Mascarene box    [[-25, 50], [-15, 65]]               0 messages in 120 s
    Global box       [[-90, -180], [90, 180]]             5 messages in < 15 s
                     (PositionReport, StaticDataReport, StandardClassBPositionReport)

Key valid, subscription accepted cleanly, global stream flowing. The gap is
REGIONAL RECEIVER COVERAGE, not the service and not the key. That is why the
Marine Transport pillar ships schema-accurate synthetic data labelled
data_kind="synthetic", and why the live collector is deliberately unimplemented
rather than half-built: there is nothing for it to collect. Re-run this probe to
find out whether that has changed.

Usage:
    export AISSTREAM_API_KEY='...'   (leading space keeps it out of shell history)
    backend/.venv/bin/python backend/scripts/ais_coverage_probe.py

Requires `websockets`. Makes real network calls, so it is a script and never a
test — the default suite is offline by design and its socket guard would block
this outright.
"""
import asyncio
import json
import os
import sys
import time

import websockets

KEY = os.environ.get("AISSTREAM_API_KEY", "")
URL = "wss://stream.aisstream.io/v0/stream"
# Bounding boxes are [[lat_sw, lon_sw], [lat_ne, lon_ne]] pairs.
PORT_LOUIS = [[[-20.35, 57.25], [-19.90, 57.75]]]  # harbour + NW approach
WIDE = [[[-25.00, 50.00], [-15.00, 65.00]]]        # Mascarene basin (coverage check)
GLOBAL = [[[-90.0, -180.0], [90.0, 180.0]]]        # is the stream alive at all?


async def probe(label: str, boxes, seconds: int) -> int:
    print(f"\n-- {label}: listening {seconds}s (Ctrl-C to stop early) --")
    count = 0
    try:
        async with websockets.connect(URL) as ws:
            # Subscription must be sent within ~3 s of connecting.
            await ws.send(json.dumps({"APIKey": KEY, "BoundingBoxes": boxes}))
            deadline = time.monotonic() + seconds
            while time.monotonic() < deadline:
                try:
                    raw = await asyncio.wait_for(ws.recv(), timeout=max(0.1, deadline - time.monotonic()))
                except asyncio.TimeoutError:
                    break
                msg = json.loads(raw)
                if any(k.lower() == "error" for k in msg):
                    print("SERVER ERROR:", msg)
                    return -1
                meta = msg.get("MetaData") or msg.get("Metadata") or {}
                count += 1
                if count <= 12:
                    name = str(meta.get("ShipName", "")).strip() or "-"
                    lat = meta.get("latitude", meta.get("Latitude", "?"))
                    lon = meta.get("longitude", meta.get("Longitude", "?"))
                    print(f"{count:>3}. {msg.get('MessageType', '?'):<18} {name:<22} "
                          f"MMSI {meta.get('MMSI', '?')}  ({lat}, {lon})")
    except Exception as exc:  # noqa: BLE001 — a probe reports, it doesn't crash
        print("CONNECTION PROBLEM:", type(exc).__name__, exc)
        return -1
    print(f"-- {label}: {count} message(s) --")
    return count


async def main() -> None:
    if not KEY:
        sys.exit("Set AISSTREAM_API_KEY first (leading-space export), then rerun.")
    pl = await probe("PORT LOUIS box", PORT_LOUIS, 120)
    if pl > 0:
        print("\nVERDICT: Port Louis coverage EXISTS. GO on the live collector — "
              "the live tier is worth building.")
        return
    if pl < 0:
        print("\nVERDICT: key or format problem — fix the key before blaming coverage.")
        return

    wide = await probe("WIDE Mascarene box", WIDE, 120)
    if wide > 0:
        print("\nVERDICT: key + format WORK, but no receiver near Port Louis right now. "
              "Either approve a wider box (coverage_note must say so) or ship synthetic-labelled.")
        return
    if wide < 0:
        print("\nVERDICT: key or format problem — fix the key before blaming coverage.")
        return

    # Both regional boxes silent. One question left, and it is the one that
    # decides whether the finding is about aisstream or about us: is the stream
    # producing anything at all? A short listen is enough — a live global feed
    # answers in seconds.
    glob = await probe("GLOBAL box (liveness control)", GLOBAL, 20)
    if glob > 0:
        print("\nVERDICT: global stream FLOWING, both regional boxes silent — regional "
              "receiver coverage gap, confirmed NOT a key or service problem. Ship "
              "synthetic-labelled and leave the collector unimplemented; there is "
              "nothing for it to collect.")
    elif glob == 0:
        print("\nVERDICT: silent even globally — the service or the account is the "
              "problem, not Mauritian coverage. Do not conclude anything about "
              "regional receivers from this run.")
    else:
        print("\nVERDICT: key or format problem — fix the key before blaming coverage.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nstopped.")