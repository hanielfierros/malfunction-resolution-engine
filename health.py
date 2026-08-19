"""In-process health check (same payload as GET /health)."""
from server import load_backend


def check() -> dict:
    return load_backend().service().health()


if __name__ == "__main__":
    import json
    print(json.dumps(check(), ensure_ascii=False, indent=2))
