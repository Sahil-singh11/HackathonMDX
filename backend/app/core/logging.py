"""Structured JSON logging with request IDs and secret redaction."""
from __future__ import annotations

import json
import logging
import re
import uuid
from contextvars import ContextVar

request_id_var: ContextVar[str] = ContextVar("request_id", default="-")

_SECRET_RE = re.compile(r"(AIza[0-9A-Za-z_\-]{20,}|(?i:api[_-]?key|token|secret)[\"'=:\s]+[^\s\"']{8,})")


def new_request_id() -> str:
    rid = uuid.uuid4().hex[:12]
    request_id_var.set(rid)
    return rid


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        msg = record.getMessage()
        msg = _SECRET_RE.sub("[REDACTED]", msg)
        payload = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
            "level": record.levelname,
            "logger": record.name,
            "request_id": request_id_var.get(),
            "msg": msg,
        }
        return json.dumps(payload, ensure_ascii=False)


def configure(level: str = "INFO") -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level)


def redact_coords(lat: float | None, lon: float | None) -> str:
    """Coordinates are never logged or traced at full precision."""
    if lat is None or lon is None:
        return "unknown"
    return f"{round(lat, 2)},{round(lon, 2)} (rounded)"
