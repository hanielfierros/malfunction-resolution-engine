"""Runtime configuration. No secrets. Override with environment variables."""
from __future__ import annotations

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = Path(os.environ.get("KB_DIR", BASE_DIR))

ENVIRONMENT = os.environ.get("ENVIRONMENT", "development").strip() or "development"
HOST = os.environ.get("HOST", "127.0.0.1").strip() or "127.0.0.1"
PORT = int(os.environ.get("PORT", "8765"))

_DEFAULT_ORIGINS = (
    "http://127.0.0.1:8000,"
    "http://localhost:8000,"
    "http://127.0.0.1:8080,"
    "http://localhost:8080,"
    "http://127.0.0.1:5500,"
    "http://localhost:5500,"
    "https://hanielfierros.github.io"
)


def _origins() -> list[str]:
    raw = os.environ.get("ALLOWED_ORIGINS", _DEFAULT_ORIGINS)
    return [x.strip() for x in raw.split(",") if x.strip()]


ALLOWED_ORIGINS = _origins()


def cors_origin(request_origin: str | None) -> str:
    allowed = _origins()
    if ENVIRONMENT == "production":
        allowed = [
            x for x in allowed
            if x != "*" and "127.0.0.1" not in x and "localhost" not in x.lower()
        ]
    elif "*" in allowed:
        return "*"
    if request_origin and request_origin in allowed:
        return request_origin
    return ""


def cors_headers() -> list[tuple[str, str]]:
    return [
        ("Access-Control-Allow-Methods", "GET,POST,OPTIONS"),
        ("Access-Control-Allow-Headers", "Content-Type"),
    ]
