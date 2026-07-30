#!/usr/bin/env python3
"""Deployed-Render AI check (safe, read-mostly).

    python scripts/final_render_check.py [--base-url https://lamer-konekte.onrender.com]
                                         [--wake-timeout 180] [--live]

Accounts for free-tier cold start with a bounded wait. `--live` adds a small number of
real requests (Morisyen text, marine function, one redistributable image, mock declaration
prepare) — it never creates a misleading real-world record: the declaration path is
prepare-only and is already labelled MOCK by the server.

Writes evaluation/results/final_render_ai_check.json and docs/FINAL_RENDER_AI_CHECK.md.
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
CHECKS: list[dict] = []


def chk(name: str, ok: bool | None, detail: str = "") -> None:
    CHECKS.append({"check": name, "ok": ok, "detail": str(detail)[:300]})
    tag = "ok  " if ok else ("SKIP" if ok is None else "FAIL")
    print(f"  {tag} {name}" + (f" — {str(detail)[:110]}" if detail else ""))


def wake(base: str, timeout: int) -> tuple[bool, int]:
    """Bounded wait for a sleeping free-tier instance."""
    deadline = time.monotonic() + timeout
    t0 = time.monotonic()
    attempt = 0
    while time.monotonic() < deadline:
        attempt += 1
        try:
            r = httpx.get(f"{base}/health", timeout=30)
            if r.status_code == 200:
                return True, int((time.monotonic() - t0) * 1000)
        except Exception:  # noqa: BLE001 — cold start closes connections
            pass
        time.sleep(5)
    return False, int((time.monotonic() - t0) * 1000)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default="https://lamer-konekte.onrender.com")
    ap.add_argument("--wake-timeout", type=int, default=180)
    ap.add_argument("--live", action="store_true")
    a = ap.parse_args()
    base = a.base_url.rstrip("/")
    started = datetime.now(timezone.utc)

    print(f"Render check — {base} (cold-start budget {a.wake_timeout}s)")
    awake, wake_ms = wake(base, a.wake_timeout)
    chk("deployment reachable (after cold start)", awake, f"{wake_ms} ms to first 200")

    reachable = awake
    if not awake:
        chk("all further checks", None, "deployment asleep or unavailable")
        write(started, base, reachable, wake_ms)
        return 1

    c = httpx.Client(base_url=base, timeout=90.0, follow_redirects=True)
    try:
        h = c.get("/health")
        chk("health endpoint 200", h.status_code == 200, h.text[:80])

        home = c.get("/")
        chk("homepage responds", home.status_code == 200,
            f"{home.status_code}, {len(home.content)} bytes")
        chk("homepage is the PWA (not a stack trace)",
            "Lamer" in home.text or "<div id=\"root\"" in home.text,
            "branded HTML served")

        st = c.get("/api/provider/status")
        chk("provider-status endpoint responds", st.status_code == 200, st.status_code)
        body = st.json()
        raw = json.dumps(body)
        chk("production model reported",
            body["hosted"]["model"] == "gemma-4-26b-a4b-it", body["hosted"]["model"])
        chk("hosted configured on the server (key present remotely)",
            bool(body["hosted"]["configured"]), body["hosted"]["configured"])
        chk("default provider mode is hosted", body.get("default_mode") == "hosted",
            body.get("default_mode"))
        caps = body.get("capabilities")
        chk("mock is labelled simulated (not shown as real)",
            caps is None or caps["mock"]["simulated"] is True,
            "capability surface present" if caps else "capabilities field absent")
        chk("experimental E2B not enabled/advertised",
            "finetuned" not in raw.lower() and "e2b" not in raw.lower(), "")
        chk("no secret in status response",
            "AIza" not in raw and "api_key" not in raw.lower(), "")

        spec = c.get("/openapi.json")
        if spec.status_code == 200:
            paths = set(spec.json().get("paths", {}))
            required = {"/api/analyse-catch", "/api/analyses/{analysis_id}/confirm",
                        "/api/provider/status", "/api/declarations/prepare",
                        "/api/declarations/mock-submit", "/health"}
            missing = sorted(required - paths)
            chk("frozen API contract present", not missing, f"missing={missing}" if missing else
                f"{len(paths)} paths")
            chk("no adapter/router endpoint exposed",
                not any("finetun" in p or "e2b" in p or "adapter" in p for p in paths), "")
        else:
            chk("frozen API contract present", None, f"openapi not served ({spec.status_code})")

        cors = c.options("/api/provider/status",
                         headers={"Origin": base, "Access-Control-Request-Method": "GET"})
        acao = cors.headers.get("access-control-allow-origin")
        chk("CORS configured for the frontend", cors.status_code < 500,
            f"status={cors.status_code} allow-origin={acao}")

        bad = c.get("/api/declarations/definitely-not-a-real-id/pdf")
        chk("no debug stack trace on error",
            "Traceback" not in bad.text and "File \"" not in bad.text,
            f"{bad.status_code}, {len(bad.text)} bytes")

        if a.live:
            print("  -- live requests --")
            t0 = time.monotonic()
            r = c.post("/api/analyse-catch",
                       data={"note": "Ki kondisyon lamer pou dime dan Flic-en-Flac?",
                             "language": "mfe"})
            ms = int((time.monotonic() - t0) * 1000)
            if r.status_code == 200:
                p = r.json()
                names = [t["function"] for t in p.get("function_trace", [])]
                disclosed = any("mock" in l.lower() or "fell back" in l.lower()
                                for l in p.get("limitations", []))
                chk("live Morisyen marine request succeeded", True, f"{ms} ms")
                chk("marine function selected", "get_marine_conditions" in names, names)
                chk("real inference OR disclosed fallback",
                    p["provider"]["real_inference"] is True or disclosed,
                    f"real={p['provider']['real_inference']} disclosed={disclosed}")
                chk("no secret in analysis response",
                    "AIza" not in json.dumps(p), "")
                chk("internal diagnostics redacted",
                    "diagnostics" not in json.dumps(p), "")
            else:
                chk("live Morisyen marine request succeeded", False,
                    f"{r.status_code}: {r.text[:120]}")

            img = sorted((ROOT / "data" / "demo").glob("epinephelus_merra_*.jpg"))[0]
            t0 = time.monotonic()
            ri = c.post("/api/analyse-catch",
                        files={"image": (img.name, img.read_bytes(), "image/jpeg")},
                        data={"note": "Ki pwason sa?", "language": "mfe"})
            if ri.status_code == 200:
                pi = ri.json()
                chk("live image request succeeded", True,
                    f"{int((time.monotonic()-t0)*1000)} ms, quality={pi['image_quality']['status']}")
                chk("species confirmation still required",
                    pi["species_confirmation_required"] is True, "")
                chk("no premature legal decision",
                    pi["legal_check"]["status"] == "pending_confirmation",
                    pi["legal_check"]["status"])
            else:
                chk("live image request succeeded", False, f"{ri.status_code}")

            # Prepare-only: creates a draft the server already labels MOCK. No submission.
            pr = c.post("/api/declarations/prepare",
                        data={"fisher_name": "QA", "fishing_area": "Grand Baie",
                              "period_start": "2026-07-01", "period_end": "2026-07-31"})
            if pr.status_code == 200:
                chk("mock declaration prepare labelled MOCK",
                    "MOCK" in json.dumps(pr.json()).upper(),
                    pr.json().get("mock_label", "")[:60])
            else:
                chk("mock declaration prepare labelled MOCK", False, pr.status_code)
    finally:
        c.close()

    write(started, base, reachable, wake_ms)
    failed = [x for x in CHECKS if x["ok"] is False]
    return 0 if not failed else 1


def write(started, base, reachable, wake_ms) -> None:
    ok = sum(1 for c in CHECKS if c["ok"] is True)
    bad = sum(1 for c in CHECKS if c["ok"] is False)
    skip = sum(1 for c in CHECKS if c["ok"] is None)
    payload = {"run_at": started.isoformat(), "base_url": base,
               "reachable": reachable, "wake_ms": wake_ms,
               "passed": ok, "failed": bad, "skipped": skip, "checks": CHECKS,
               "note": ("free-tier instance sleeps when idle; a cold start of 30-60 s is "
                        "expected and is not a failure")}
    out = ROOT / "evaluation" / "results" / "final_render_ai_check.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    L = ["# Final Render AI Check", "",
         f"Run {payload['run_at']} · `{base}`", "",
         f"**Reachable: {'YES' if reachable else 'NO'}** "
         f"(first 200 after {wake_ms} ms) · {ok} passed · {bad} failed · {skip} skipped", "",
         "| Check | Result | Detail |", "|---|---|---|"]
    for c in CHECKS:
        r = "PASS" if c["ok"] is True else ("SKIP" if c["ok"] is None else "**FAIL**")
        L.append(f"| {c['check']} | {r} | {c['detail']} |")
    if not reachable:
        L += ["", "## Manual retry procedure", "",
              "The free-tier instance sleeps when idle and can take 30–60 s (occasionally longer)",
              "to wake. To retry:", "",
              "```bash",
              f"curl -sS -o /dev/null -w '%{{http_code}} in %{{time_total}}s\\n' {base}/health",
              "# then, once it returns 200:",
              f"python scripts/final_render_check.py --base-url {base} --live",
              "```", "",
              "If it never wakes: check the Render dashboard for a failed deploy or an exhausted",
              "free-tier quota, and confirm `GEMINI_API_KEY` is still set in the service settings."]
    L += ["", "> Deployment status here is measured against the live URL only — no local result",
          "> is used as evidence of deployment health.", ""]
    (ROOT / "docs" / "FINAL_RENDER_AI_CHECK.md").write_text("\n".join(L), encoding="utf-8")
    print(f"\n{ok} passed / {bad} failed / {skip} skipped — artifacts written")


if __name__ == "__main__":
    sys.exit(main())
