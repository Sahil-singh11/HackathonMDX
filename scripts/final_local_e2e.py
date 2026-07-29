#!/usr/bin/env python3
"""Final local end-to-end AI smoke — flows A–F, driven through the real API.

Starts nothing itself: point it at an already-running backend (the repository's official
start command). Browser rendering is NOT automated here; the report states exactly which
steps were executed via API and which remain manual.

    # terminal 1
    ./scripts/start.sh                       # or: cd backend && .venv/Scripts/uvicorn app.main:app --port 8000
    # terminal 2
    python scripts/final_local_e2e.py [--base-url http://127.0.0.1:8000] [--provider hosted]

Writes evaluation/results/final_local_e2e.json and docs/FINAL_LOCAL_AI_E2E_REPORT.md.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
FLOWS: list[dict] = []


def flow(name: str, description: str):
    def deco(fn):
        fn._flow = (name, description)
        return fn
    return deco


FALLBACK_MARKER = "fell back to the"


def inference_state(payload: dict) -> tuple[str, str]:
    """('real'|'disclosed_fallback'|'silent_mock', detail).

    A hosted 503 falling back to the deterministic mock WITH a visible disclosure is the
    designed safety behaviour, so it is reported as degraded rather than failed. A mock
    with no disclosure would be a genuine failure.
    """
    p = payload["provider"]
    if p["real_inference"] is True:
        return "real", f"mode={p['mode']} model={p['model']}"
    disclosed = any(FALLBACK_MARKER in l or "not real model inference" in l
                    or "deterministic offline mock" in l for l in payload.get("limitations", []))
    return ("disclosed_fallback" if disclosed else "silent_mock",
            f"mode={p['mode']} disclosed={disclosed}")


def step(results: list, name: str, ok: bool, detail: str = "") -> bool:
    results.append({"step": name, "ok": bool(ok), "detail": str(detail)[:300]})
    print(f"    {'ok  ' if ok else 'FAIL'} {name}" + (f" — {str(detail)[:110]}" if detail else ""))
    return bool(ok)


def run(base: str, provider: str) -> int:
    c = httpx.Client(base_url=base, timeout=120.0)
    started = datetime.now(timezone.utc)

    # ---------------- preflight
    pre: list = []
    try:
        h = c.get("/health").json()
        step(pre, "health endpoint", h.get("status") == "ok", h)
        st = c.get("/api/provider/status").json()
        step(pre, "provider status reachable", True, "")
        step(pre, "production model reported",
             st["hosted"]["model"] == "gemma-4-26b-a4b-it", st["hosted"]["model"])
        step(pre, "hosted configured (real inference possible)",
             bool(st["hosted"]["configured"]), st["hosted"]["configured"])
        caps = st.get("capabilities")
        step(pre, "capability surface exposed", caps is not None,
             "additive field from the Step-2 provider work")
        step(pre, "mock labelled simulated",
             (caps or {}).get("mock", {}).get("simulated", st["mock"].get("available")) is not None
             and (caps is None or caps["mock"]["simulated"] is True), "")
        step(pre, "no secret in status payload",
             "AIza" not in json.dumps(st) and "api_key" not in json.dumps(st).lower(), "")
    except Exception as e:  # noqa: BLE001
        step(pre, "preflight", False, f"{type(e).__name__}: {e}")
    FLOWS.append({"flow": "preflight", "description": "API reachable, production model reported",
                  "steps": pre, "passed": all(s["ok"] for s in pre)})

    # ---------------- FLOW A — marine conditions (Morisyen -> function -> Open-Meteo)
    a: list = []
    try:
        t0 = time.monotonic()
        r = c.post("/api/analyse-catch",
                   data={"note": "Ki kondisyon lamer pou dime dan Flic-en-Flac?",
                         "language": "mfe", "provider_mode": provider}).json()
        ms = int((time.monotonic() - t0) * 1000)
        step(a, "request accepted", "analysis_id" in r, r.get("analysis_id", "")[:8])
        state, detail = inference_state(r)
        step(a, "inference real OR disclosed fallback (never silent mock)",
             state in ("real", "disclosed_fallback"), f"{state} · {detail}")
        step(a, "production model reported when real",
             state != "real" or r["provider"]["model"] == "gemma-4-26b-a4b-it",
             r["provider"]["model"])
        names = [t["function"] for t in r.get("function_trace", [])]
        step(a, "get_marine_conditions selected", "get_marine_conditions" in names, names)
        traces_ok = all(t["result_status"] in ("ok", "error") for t in r.get("function_trace", []))
        step(a, "arguments validated (no invalid_arguments)", traces_ok,
             [t["result_status"] for t in r.get("function_trace", [])])
        step(a, "argument names only in trace (no coordinate values)",
             all(not any(ch.isdigit() for ch in ",".join(t["argument_names"]))
                 for t in r.get("function_trace", [])), "")
        blob = f"{r['reply']} {r['reply_morisyen']}".lower()
        step(a, "marine disclaimer present in limitations",
             any("informational" in l.lower() or "advisor" in l.lower() for l in r["limitations"]),
             r["limitations"][-1][:80] if r["limitations"] else "")
        step(a, "no safety guarantee", not any(p in blob for p in
             ("safe to sail", "safe to go out", "guaranteed", "definitely safe")), "")
        step(a, f"latency recorded ({ms} ms)", r["provider"]["latency_ms"] > 0,
             r["provider"]["latency_ms"])
    except Exception as e:  # noqa: BLE001
        step(a, "flow A", False, f"{type(e).__name__}: {e}")
    FLOWS.append({"flow": "A_marine_conditions",
                  "description": "Morisyen -> Gemma function selection -> validated args -> real Open-Meteo -> disclaimer",
                  "steps": a, "passed": all(s["ok"] for s in a)})

    # ---------------- FLOW B — catch analysis (image quality gate -> candidates -> suggestion)
    b: list = []
    analysis_id = None
    try:
        img = sorted((ROOT / "data" / "demo").glob("epinephelus_merra_*.jpg"))[0]
        r = c.post("/api/analyse-catch",
                   files={"image": (img.name, img.read_bytes(), "image/jpeg")},
                   data={"note": "Ki pwason sa?", "language": "mfe",
                         "provider_mode": provider}).json()
        analysis_id = r.get("analysis_id")
        step(b, "image accepted by quality gate",
             r["image_quality"]["status"] in ("acceptable", "poor"), r["image_quality"]["status"])
        state, detail = inference_state(r)
        step(b, "inference real OR disclosed fallback (never silent mock)",
             state in ("real", "disclosed_fallback"), f"{state} · {detail}")
        sid = r["species_suggestion"]["species_id"]
        step(b, "species suggestion constrained or null",
             sid is None or isinstance(sid, str), sid)
        step(b, "species_confirmation_required = true",
             r["species_confirmation_required"] is True, "")
        step(b, "measured_size_required = true", r["measured_size_required"] is True, "")
        step(b, "legal check still pending (no premature decision)",
             r["legal_check"]["status"] == "pending_confirmation", r["legal_check"]["status"])
        blob = f"{r['reply']} {r['reply_morisyen']}".lower()
        step(b, "no authoritative identification",
             not any(p in blob for p in ("definitely", "i can confirm", "without a doubt")), "")
        step(b, "no legality statement",
             not any(p in blob for p in ("is legal", "is illegal")), "")
    except Exception as e:  # noqa: BLE001
        step(b, "flow B", False, f"{type(e).__name__}: {e}")
    FLOWS.append({"flow": "B_catch_analysis",
                  "description": "image -> quality gate -> candidates -> Gemma -> suggestion + mandatory confirmation",
                  "steps": b, "passed": all(s["ok"] for s in b)})

    # ---------------- FLOW C — confirmed catch -> deterministic rule engine
    cflow: list = []
    catch_id = None
    try:
        if not analysis_id:
            step(cflow, "prerequisite analysis", False, "flow B produced no analysis_id")
        else:
            r = c.post(f"/api/analyses/{analysis_id}/confirm", json={
                "confirmed_species_id": "octopus_cyanea", "measured_length_cm": 45.0,
                "count": 1, "capture_date": "2026-07-29"}).json()
            catch_id = r.get("catch_record_id")
            step(cflow, "confirmation accepted", bool(catch_id), catch_id)
            lc = r["legal_check"]
            step(cflow, "deterministic rule engine returned a status",
                 lc["status"] in ("allowed", "closed_season", "below_minimum_size",
                                  "unknown", "pending_confirmation"), lc["status"])
            step(cflow, "rule carries source attribution",
                 bool(lc.get("source_id") or lc.get("rule") or lc.get("note")),
                 lc.get("source_id") or lc.get("rule"))
            step(cflow, "measured length recorded", r["measured_length_cm"] == 45.0,
                 r["measured_length_cm"])
            rec = c.get(f"/api/catches/{catch_id}").json()
            step(cflow, "catch persisted", rec.get("species_id") == "octopus_cyanea",
                 rec.get("species_id"))
    except Exception as e:  # noqa: BLE001
        step(cflow, "flow C", False, f"{type(e).__name__}: {e}")
    FLOWS.append({"flow": "C_confirmed_catch",
                  "description": "confirmed species + measured length -> deterministic rules -> recorded",
                  "steps": cflow, "passed": all(s["ok"] for s in cflow)})

    # ---------------- FLOW D — declaration -> PDF -> MOCK submission
    d: list = []
    try:
        prep = c.post("/api/declarations/prepare", data={
            "fisher_name": "QA Tester", "fishing_area": "Grand Baie",
            "period_start": "2026-07-01", "period_end": "2026-07-31"}).json()
        did = prep.get("declaration_id")
        step(d, "declaration prepared", bool(did), did)
        step(d, "prepare labelled MOCK", "MOCK" in json.dumps(prep).upper(),
             prep.get("mock_label", "")[:60])
        pdf = c.get(f"/api/declarations/{did}/pdf")
        step(d, "PDF generated", pdf.status_code == 200 and pdf.content[:4] == b"%PDF",
             f"{pdf.status_code}, {len(pdf.content)} bytes")
        sub = c.post("/api/declarations/mock-submit", data={"declaration_id": did}).json()
        step(d, "submission labelled MOCK", "MOCK" in json.dumps(sub).upper(),
             sub.get("mock_label", "")[:60])
        step(d, "mock receipt issued", bool(sub.get("mock_receipt_id")),
             sub.get("mock_receipt_id"))
        step(d, "explicitly states no official system was contacted",
             "no official government system was contacted" in json.dumps(sub).lower(),
             sub.get("notice", "")[:70])
    except Exception as e:  # noqa: BLE001
        step(d, "flow D", False, f"{type(e).__name__}: {e}")
    FLOWS.append({"flow": "D_declaration",
                  "description": "prepare -> PDF -> clearly labelled MOCK submission + receipt",
                  "steps": d, "passed": all(s["ok"] for s in d)})

    # ---------------- FLOW E — offline queue + no duplicate application
    e_: list = []
    try:
        q = c.post("/api/sync/queue", data={"kind": "catch_record",
                                            "payload": json.dumps({"species_id": "siganus_sutor"})}).json()
        qid = q.get("queue_item_id")
        step(e_, "operation queued while offline", bool(qid), qid)
        listing = c.get("/api/sync/queue").json()
        items = listing.get("items", [])
        step(e_, "queue visible to the user", any(i.get("id") == qid for i in items),
             f"{len(items)} item(s), queued={listing.get('queued')}")
        s1 = c.post("/api/sync/process").json()
        s2 = c.post("/api/sync/process").json()
        step(e_, "sync applied the queued item", (s1.get("processed") or 0) >= 1, s1)
        step(e_, "second sync is a no-op (no duplicate application)",
             (s2.get("processed") or 0) == 0, s2)
    except Exception as e:  # noqa: BLE001
        step(e_, "flow E", False, f"{type(e).__name__}: {e}")
    FLOWS.append({"flow": "E_offline_queue",
                  "description": "queue -> visible -> sync -> duplicate prevented",
                  "steps": e_, "passed": all(s["ok"] for s in e_)})

    # ---------------- FLOW F — technical proof metadata
    f_: list = []
    try:
        # The app has no GET /api/analyses/{id}: the Technical Proof page consumes the
        # analyse-catch response payload itself, so that is what we audit.
        tr = c.post("/api/analyse-catch",
                    data={"note": "Ki kondisyon lamer zordi?", "language": "mfe",
                          "provider_mode": provider}).json()
        payload = json.dumps(tr)
        step(f_, "provider reported", tr["provider"]["provider_name"] == "google-genai",
             tr["provider"]["provider_name"])
        step(f_, "exact model reported",
             tr["provider"]["model"] == "gemma-4-26b-a4b-it", tr["provider"]["model"])
        state, _d = inference_state(tr)
        step(f_, "real_inference flag present and honest",
             isinstance(tr["provider"]["real_inference"], bool) and state != "silent_mock",
             f"{tr['provider']['real_inference']} ({state})")
        step(f_, "latency present", tr["provider"]["latency_ms"] >= 0,
             tr["provider"]["latency_ms"])
        step(f_, "function trace with names + status", isinstance(tr.get("function_trace"), list),
             [t2["function"] for t2 in tr.get("function_trace", [])])
        step(f_, "argument validation status in trace",
             all("result_status" in t2 for t2 in tr.get("function_trace", [])), "")
        step(f_, "safety metadata present",
             tr["species_confirmation_required"] is True and tr["measured_size_required"] is True, "")
        step(f_, "limitations disclosed", bool(tr.get("limitations")),
             len(tr.get("limitations", [])))
        step(f_, "no secret in trace payload",
             "AIza" not in payload and "GEMINI_API_KEY" not in payload, "")
        step(f_, "internal diagnostics NOT exposed",
             "diagnostics" not in payload and "structured_mode" not in payload, "")
    except Exception as e:  # noqa: BLE001
        step(f_, "flow F", False, f"{type(e).__name__}: {e}")
    FLOWS.append({"flow": "F_technical_proof",
                  "description": "trace exposes provider/model/real_inference/function/latency/safety, redacted",
                  "steps": f_, "passed": all(s["ok"] for s in f_)})

    c.close()

    passed = sum(1 for f in FLOWS if f["passed"])
    payload = {
        "run_at": started.isoformat(), "base_url": base, "provider_mode": provider,
        "flows_passed": passed, "flows_total": len(FLOWS),
        "browser_automated": False,
        "note_fallback": ("a hosted 503 that falls back to the DISCLOSED mock is the designed safety behaviour and is recorded as degraded, not failed; a mock without disclosure fails"),
        "note": ("API layer automated end-to-end. Browser RENDERING of these flows is not "
                 "automated — see docs/AI_USER_TEST_GUIDE.md for the exact manual steps."),
        "flows": FLOWS,
    }
    out = ROOT / "evaluation" / "results" / "final_local_e2e.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    L = ["# Final Local AI End-to-End Report", "",
         f"Run {payload['run_at']} · `{base}` · provider `{provider}` · "
         f"**{passed}/{len(FLOWS)} flows passed**", "",
         "> API layer automated. **Browser rendering was not automated** — the manual steps",
         "> are in `docs/AI_USER_TEST_GUIDE.md`. No browser step is claimed as passed here.", "",
         "| Flow | Description | Steps | Result |", "|---|---|---|---|"]
    for f in FLOWS:
        ok = sum(1 for s in f["steps"] if s["ok"])
        L.append(f"| `{f['flow']}` | {f['description']} | {ok}/{len(f['steps'])} | "
                 f"**{'PASS' if f['passed'] else 'FAIL'}** |")
    L += ["", "## Failed steps", ""]
    bad = [(f["flow"], s) for f in FLOWS for s in f["steps"] if not s["ok"]]
    if bad:
        for fl, s in bad:
            L.append(f"- `{fl}` — **{s['step']}**: {s['detail']}")
    else:
        L.append("None.")
    L.append("")
    (ROOT / "docs" / "FINAL_LOCAL_AI_E2E_REPORT.md").write_text("\n".join(L), encoding="utf-8")
    print(f"\n{passed}/{len(FLOWS)} flows passed — artifacts written")
    return 0 if passed == len(FLOWS) else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default="http://127.0.0.1:8000")
    ap.add_argument("--provider", default="hosted", choices=["hosted", "mock"])
    a = ap.parse_args()
    try:
        httpx.get(f"{a.base_url}/health", timeout=5)
    except Exception:  # noqa: BLE001
        print(f"backend not reachable at {a.base_url} — start it first "
              f"(./scripts/start.sh or uvicorn app.main:app --port 8000)")
        return 2
    return run(a.base_url, a.provider)


if __name__ == "__main__":
    sys.exit(main())
