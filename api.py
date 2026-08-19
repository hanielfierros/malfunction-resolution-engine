"""API surface used by the PWA. Contracts match the existing engine."""

ROUTES = [
    "GET /health",
    "GET /status",
    "GET /entity/{id}",
    "GET /alarm/{id}",
    "GET /document/{id}",
    "GET /page/{id}",
    "POST /query",
    "POST /reset",
]

QUERY_BODY = {"query": "LZ1 Reading Error"}
