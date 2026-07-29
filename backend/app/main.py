from __future__ import annotations

import logging
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlmodel import Session

from app.api.routes import router
from app.core.config import get_settings
from app.core.logging import configure, new_request_id
from app.db.session import get_engine, init_db
from app.services.marine.client import prewarm_demo_locations

log = logging.getLogger(__name__)


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
    def startup() -> None:
        init_db()
        with Session(get_engine()) as session:
            prewarm_demo_locations(session)
        log.info("Lamer Konekte backend started (provider default: %s)", settings.provider_mode)

    app.include_router(router)

    dist = Path(__file__).resolve().parents[2] / "frontend" / "dist"
    if dist.exists():
        app.mount("/", StaticFiles(directory=dist, html=True), name="frontend")
    return app


app = create_app()
