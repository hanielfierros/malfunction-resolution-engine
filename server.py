"""HTTP server entry. Usage: python server.py   or   python main.py"""
from __future__ import annotations

import importlib.util
from http.server import ThreadingHTTPServer
from pathlib import Path

from config import HOST, PORT

_BACKEND = None


def load_backend():
    global _BACKEND
    if _BACKEND is None:
        path = Path(__file__).resolve().parent / "36_BUILD_BACKEND.py"
        spec = importlib.util.spec_from_file_location("be36", path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        _BACKEND = mod
    return _BACKEND


def run() -> None:
    mod = load_backend()
    print("Loading Knowledge Base...")
    mod.service()
    print(f"Malfunction Resolution Engine")
    print(f"Listening on http://{HOST}:{PORT}/")
    print("GET  /health")
    print("POST /query")
    ThreadingHTTPServer((HOST, PORT), mod.Handler).serve_forever()


if __name__ == "__main__":
    run()
