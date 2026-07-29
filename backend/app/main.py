from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException
from sqlmodel import Session

from app.api.routes import router
from app.core.config import get_settings
from app.core.logging import configure, new_request_id
from app.db.session import get_engine, init_db
from app.pillars.routes import build_pillar_router
from app.pillars.energy import register_energy
from app.pillars.tourism import prewarm_tourism_sites, register_tourism
from app.services.marine.client import prewarm_demo_locations

log = logging.getLogger(__name__)


def _run_marine_prewarm() -> None:
    """Runs on a worker thread — never blocks the event loop or app readiness."""
    with Session(get_engine()) as session:
        prewarm_demo_locations(session)
    log.info("Marine cache pre-warm finished")


def _run_tourism_prewarm() -> None:
    """Tourism site cache (Workstream 2), same worker-thread contract.

    Eight named sites x two endpoints, staggered inside the helper. Separate
    task from the marine pre-warm so one slow host cannot delay the other.
    """
    prewarm_tourism_sites()
    log.info("Tourism cache pre-warm finished")


def create_app() -> FastAPI:
    settings = get_settings()
    configure(settings.log_level)
    app = FastAPI(
        title="Lamer Konekte API",
        description=("Morisyen-first multimodal catch-recording assistant. "
                     "Species suggestions and regulatory checks must be confirmed against official sources."),
        version="1.0.0",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_methods=["*"], allow_headers=["*"],
    )

    @app.middleware("http")
    async def request_id_middleware(request: Request, call_next):
        rid = new_request_id()
        response = await call_next(request)
        response.headers["X-Request-ID"] = rid
        return response

    @app.on_event("startup")
    async def startup() -> None:
        init_db()
        if settings.marine_prewarm_on_startup:
            # Fire-and-forget on a worker thread: readiness (and /health) must
            # never wait on a live Open-Meteo round trip. Worst case (network
            # down/slow) previously blocked boot for up to ~60s here.
            asyncio.create_task(asyncio.to_thread(_run_marine_prewarm))
            asyncio.create_task(asyncio.to_thread(_run_tourism_prewarm))
        log.info("Lamer Konekte backend started (provider default: %s)", settings.provider_mode)

    app.include_router(router)
    # Workstream 2: attach the tourism pillar before the router is built, so
    # mount_all() picks it up. Registering does not enable it — PILLARS_ENABLED
    # still gates the routes (503 until listed).
    register_tourism()
    register_energy()
    app.include_router(build_pillar_router())

    dist = Path(__file__).resolve().parents[2] / "frontend" / "dist"
    if dist.exists():
        # SPA fallback. StaticFiles(html=True) serves index.html for "/" but
        # returns a JSON 404 for any deeper client-side route, so opening
        # /sea, /authority or /verify/<id> directly used to fail. That is fatal
        # for /verify/<id> in particular: it is the QR-code landing page, so a
        # buyer scanning a certificate arrives by deep link every time. (It only
        # appeared to work in the browser because the service worker served a
        # cached index.html once the PWA had been visited at least once.)
        #
        # Unknown paths therefore fall through to index.html and let the router
        # decide. Real 404s for missing API routes are unaffected: the API
        # router is registered above this mount and wins.
        class SPAStaticFiles(StaticFiles):
            async def get_response(self, path: str, scope):  # type: ignore[override]
                try:
                    return await super().get_response(path, scope)
                except StarletteHTTPException as exc:
                    # StaticFiles RAISES 404 rather than returning it, so this
                    # has to be caught, not status-checked.
                    if exc.status_code != 404:
                        raise
                    # Never mask a missing asset or a missing API route as the
                    # app shell - a broken image, script or endpoint must still
                    # report 404, or debugging becomes guesswork. Only
                    # extensionless non-API paths (i.e. client routes) fall
                    # through to the SPA.
                    if "." in Path(path).name:
                        raise
                    # NOTE: on Windows StaticFiles hands us OS-native separators
                    # ("api\\does-not-exist"), so a startswith("api/") check
                    # passes on Linux and silently fails on every dev machine.
                    # Compare the first path segment instead.
                    parts = Path(path).parts
                    if parts and parts[0].lower() in {"api", "health", "docs", "redoc", "openapi.json"}:
                        raise
                    return await super().get_response("index.html", scope)

        app.mount("/", SPAStaticFiles(directory=dist, html=True), name="frontend")
    return app


app = create_app()
