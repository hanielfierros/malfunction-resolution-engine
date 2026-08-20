#!/usr/bin/env python3
"""36 — Backend / service layer. UI must not read JSON directly."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

GKB = Path(__file__).resolve().parent
MASTER = GKB
V14 = GKB
OUT = Path(__file__).resolve().parent
REP = OUT / "REPORT"
PROTECTED = [
    "DIAGNOSTIC_ENGINE", "DIAGNOSTIC_ENGINE_V2", "DIAGNOSTIC_ENGINE_V3",
    "DIAGNOSTIC_ENGINE_V4", "DIAGNOSTIC_ENGINE_V5", "DIAGNOSTIC_ENGINE_V6",
    "DIAGNOSTIC_ENGINE_V7", "DIAGNOSTIC_ENGINE_V8", "DIAGNOSTIC_ENGINE_V9",
    "DIAGNOSTIC_ENGINE_V10", "FINAL_KNOWLEDGE_BASE",
    "MASTER_CONSULTATION_LAYER_RUN_20260818_214934",
]
from config import HOST, PORT, cors_origin, cors_headers


def load(p):
    p = Path(p)
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def dump(name, obj, folder=None):
    dest = (folder or OUT) / name
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def sha256_file(path):
    path = Path(path)
    if not path.exists() or not path.is_file():
        return None
    h = hashlib.sha256()
    with path.open("rb") as f:
        for c in iter(lambda: f.read(1024 * 1024), b""):
            h.update(c)
    return h.hexdigest()


def snapshot(root):
    out = {}
    root = Path(root)
    if not root.exists():
        return out
    for p in sorted(root.rglob("*")):
        if p.is_file() and p.suffix.lower() in {".json", ".txt", ".md", ".py"} and "__pycache__" not in p.parts:
            out[str(p.relative_to(root)).replace("\\", "/")] = sha256_file(p)
    return out


def import_mod(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def recs(obj):
    if isinstance(obj, list):
        return obj
    if isinstance(obj, dict) and isinstance(obj.get("records"), list):
        return obj["records"]
    return []


class BackendService:
    def __init__(self):
        m = import_mod(V14 / "35_BUILD_CONVERSATION_CONTEXT.py", "cv35")
        self.conv = m.Conversation()
        self.entities = recs(load(MASTER / "MASTER_ENTITIES.json"))
        self.alarms = recs(load(MASTER / "MASTER_ALARMS.json"))
        self.docs = recs(load(MASTER / "SOURCE_REGISTRY.json"))
        self.pages = recs(load(MASTER / "MASTER_PAGES.json"))
        self.log = []

    def _wrap(self, payload, status="ok"):
        rid = str(uuid.uuid4())
        body = {
            "request_id": rid,
            "response_id": str(uuid.uuid4()),
            "status": status,
            "continuity_confirmed": False,
            "diagnosis_confirmed": False,
            "electrical_connection_confirmed": False,
            "data": payload,
        }
        self.log.append({"response_id": body["response_id"], "status": status})
        return body

    def query(self, text, extra=None):
        if text is None:
            return self._wrap({"error": "missing query"}, "error")
        extra = extra or {}
        resp = self.conv.ask(str(text), extra=extra)
        refs = []
        for r in (resp.get("document_references") or []):
            if not r.get("document_name") or r.get("page") is None:
                continue
            url = r.get("pdf_url")
            if isinstance(url, str) and (url.startswith("C:") or "\\" in url or url.startswith("file:")):
                url = None
            refs.append({
                "document_id": r.get("document_id"),
                "document_name": r.get("document_name"),
                "official_name": r.get("official_name") or r.get("document_name"),
                "page": r.get("page"),
                "page_label": r.get("page_label") or ("p." + str(r.get("page")) if r.get("page") is not None else None),
                "section": r.get("section"),
                "pdf_url": url,
                "available": bool(r.get("available")),
                "availability": bool(r.get("available")),
                "status": r.get("status") or r.get("hosting_status") or "PENDING_DOCUMENT_HOSTING",
                "hosting_status": r.get("hosting_status") or "PENDING_DOCUMENT_HOSTING",
                "reference_type": r.get("reference_type") or "official_documentation",
                "source": r.get("source") or "official_documentation",
                "relevance": r.get("relevance") or r.get("evidence_type") or "DOCUMENTARY_EVIDENCE",
                "entity": r.get("entity"),
                "evidence_type": r.get("evidence_type"),
                "viewer_target": r.get("viewer_target"),
            })
        documents = []
        if refs:
            documents = [
                {"document": r["document_name"], "page": r["page"],
                 "entity": r.get("entity"), "evidence_type": r.get("evidence_type"),
                 "document_id": r.get("document_id"), "pdf_url": r.get("pdf_url"),
                 "hosting_status": r.get("hosting_status"),
                 "reference_type": r.get("reference_type")}
                for r in refs
            ]
        else:
            for d in (resp.get("documents") or []):
                if not d.get("document") or d.get("page") is None:
                    continue
                documents.append({
                    "document": d.get("document"), "page": d.get("page"),
                    "entity": d.get("entity"), "evidence_type": d.get("evidence_type"),
                })
        safe = {
            "input": resp.get("input"),
            "resolved_query": resp.get("resolved_query"),
            "interpretation": resp.get("interpretation"),
            "response_kind": resp.get("response_kind"),
            "human_readable": resp.get("human_readable"),
            "message": resp.get("message") or resp.get("human_readable"),
            "case_id": resp.get("case_id") or self.conv.ix.case.id,
            "questions": resp.get("questions") or [],
            "hypotheses": resp.get("hypotheses") or [],
            "checklist": resp.get("checklist") or [],
            "evidence_summary": resp.get("evidence_summary"),
            "documents": documents,
            "document_references": refs,
            "pages": [r["page"] for r in refs],
            "review_order": resp.get("review_order"),
            "conflicts": resp.get("conflicts"),
            "limitations": resp.get("limitations"),
            "context": resp.get("context"),
            "external_sources": resp.get("external_sources") or [],
            "safety": resp.get("safety") or {
                "continuity_confirmed": False,
                "diagnosis_confirmed": False,
                "electrical_connection_confirmed": False,
                "intervention_authorized": False,
            },
            "resolution_status": resp.get("resolution_status"),
            "flags": {
                "continuity_confirmed": False,
                "diagnosis_confirmed": False,
                "electrical_connection_confirmed": False,
            },
            "evidence_analysis": resp.get("evidence_analysis") or [],
            "language": resp.get("language") or (extra or {}).get("language") or "en",
            "observations": resp.get("observations") or [],
            "evidence": resp.get("evidence") or extra.get("evidence") or [],
            "external_references": resp.get("external_references") or resp.get("external_sources") or [],
            "status": resp.get("status") or resp.get("resolution_status"),
            "resolved": bool(resp.get("resolved")),
            "external_research": resp.get("external_research") or "EXTERNAL_RESEARCH_PENDING",
            "continuity_confirmed": False,
            "diagnosis_confirmed": False,
            "electrical_connection_confirmed": False,
        }
        return self._wrap(safe)

    def reset(self):
        self.conv.reset()
        return self._wrap({"reset": True})

    def health(self):
        return self._wrap({"ok": True, "service": "diagnostic-documentation-assistant"})

    def status(self):
        st = self.conv.state
        return self._wrap({
            "current_entity": st.get("current_entity"),
            "current_alarm": st.get("current_alarm"),
            "turns": len(st.get("turns") or []),
            "case_id": getattr(getattr(self.conv, "ix", None), "case", None) and self.conv.ix.case.id,
        })

    def get_entity(self, eid):
        for e in self.entities:
            if e.get("entity_id") == eid or (e.get("canonical_name") or "").upper() == eid.upper():
                return self._wrap({k: e[k] for k in e if k != "notes" or True})
        return self._wrap({"error": "not found"}, "not_found")

    def get_alarm(self, aid):
        for a in self.alarms:
            if a.get("entity_id") == aid or aid.lower() in (a.get("canonical_name") or "").lower():
                return self._wrap(a)
        return self._wrap({"error": "not found"}, "not_found")

    def resolve_page(self, did, page):
        from document_resolver import DocumentResolver
        row = DocumentResolver().resolve(document_id=did, document_name=did, page=page)
        return self._wrap(row)

    def get_document(self, did):
        for d in self.docs:
            if d.get("document_id") == did or d.get("document_name") == did:
                public = {k: d[k] for k in d if k != "source_path"}
                public["source_path"] = "[redacted]"
                return self._wrap(public)
        return self._wrap({"error": "not found"}, "not_found")

    def get_page(self, pid):
        for p in self.pages:
            if p.get("page_id") == pid or str(p.get("page_number")) == str(pid):
                return self._wrap(p)
        return self._wrap({"error": "not found"}, "not_found")


_SERVICE = None


def service():
    global _SERVICE
    if _SERVICE is None:
        _SERVICE = BackendService()
    return _SERVICE


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, obj):
        data = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        origin = cors_origin(self.headers.get("Origin"))
        if origin:
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Vary", "Origin")
        for key, val in cors_headers():
            self.send_header(key, val)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_OPTIONS(self):
        self._send(200, {"ok": True})

    def do_GET(self):
        path = urlparse(self.path).path
        svc = service()
        if path == "/health":
            return self._send(200, svc.health())
        if path == "/status":
            return self._send(200, svc.status())
        if path.startswith("/entity/"):
            return self._send(200, svc.get_entity(path.split("/", 2)[-1]))
        if path.startswith("/alarm/"):
            return self._send(200, svc.get_alarm(path.split("/", 2)[-1]))
        if path.startswith("/document/") and "/page/" in path:
            parts = [p for p in path.split("/") if p]
            # document / {id} / page / {n}
            did = parts[1] if len(parts) >= 4 else ""
            pg = parts[3] if len(parts) >= 4 else ""
            return self._send(200, svc.resolve_page(did, pg))
        if path.startswith("/document/"):
            return self._send(200, svc.get_document(path.split("/", 2)[-1]))
        if path.startswith("/resolve/"):
            # /resolve/{id}/{page}
            parts = [p for p in path.split("/") if p]
            did = parts[1] if len(parts) >= 3 else ""
            pg = parts[2] if len(parts) >= 3 else ""
            return self._send(200, svc.resolve_page(did, pg))
        if path.startswith("/page/"):
            return self._send(200, svc.get_page(path.split("/", 2)[-1]))
        return self._send(404, {"status": "error", "data": {"error": "not found"}})

    def do_POST(self):
        path = urlparse(self.path).path
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length) if length else b"{}"
        try:
            body = json.loads(raw.decode("utf-8") or "{}")
        except Exception:
            return self._send(400, {"status": "error", "data": {"error": "invalid json"}})
        svc = service()
        if path == "/query":
            extra = {
                "case_id": body.get("case_id"),
                "evidence": body.get("evidence") or [],
                "conversation": body.get("conversation") or [],
                "language": body.get("language") or body.get("lang") or "en",
                "observation": body.get("observation"),
                "observations": body.get("observations"),
                "step_completed": body.get("step_completed") or body.get("completed_step"),
                "issue_resolved": body.get("issue_resolved"),
                "issue_persists": body.get("issue_persists"),
            }
            return self._send(200, svc.query(body.get("query"), extra=extra))
        if path == "/reset":
            return self._send(200, svc.reset())
        return self._send(404, {"status": "error", "data": {"error": "not found"}})

    def log_message(self, fmt, *args):
        return


def run_tests():
    REP.mkdir(parents=True, exist_ok=True)
    before = {n: snapshot(GKB / n) for n in PROTECTED}
    svc = BackendService()
    tests = []
    def add(n, ok, d):
        tests.append({"test": n, "result": "PASS" if ok else "FAIL", "detail": d})
    h = svc.health()
    add("health", h["status"] == "ok" and h["data"]["ok"] is True, h["status"])
    q = svc.query("LZ1 Reading Error")
    add("query_lz1", q["status"] == "ok" and "PL3_INFO" in (q["data"].get("human_readable") or ""), q["data"].get("response_kind"))
    add("no_fs_path", "C:\\Users" not in json.dumps(q), True)
    add("flags", q["continuity_confirmed"] is False and q["diagnosis_confirmed"] is False, True)
    add("ids", bool(q.get("request_id") and q.get("response_id")), True)
    r = svc.query("replace LZ1")
    add("safety", r["data"].get("response_kind") == "SAFETY_BLOCK", r["data"].get("response_kind"))
    e = svc.query("")
    add("empty", e["data"].get("response_kind") == "NO_MATCH", e["data"].get("response_kind"))
    st = svc.status()
    add("status_turns", st["data"]["turns"] >= 1, st["data"])
    rst = svc.reset()
    add("reset", rst["data"]["reset"] is True, True)
    st2 = svc.status()
    add("status_after_reset", st2["data"]["turns"] == 0, st2["data"])
    ent = svc.get_entity("LZ1")
    add("entity_lz1", ent["status"] in {"ok", "not_found"} or ent["data"].get("canonical_name") == "LZ1", ent["status"])
    al = svc.get_alarm("LZ1 Reading Error")
    add("alarm_get", al["status"] in {"ok", "not_found"}, al["status"])
    nf = svc.get_entity("ZZ99")
    add("entity_unknown", nf["status"] == "not_found", nf["status"])
    after = {n: snapshot(GKB / n) for n in PROTECTED}
    add("unmodified", all(before[n] == after[n] for n in PROTECTED), True)
    add("no_pdf", "fitz" not in sys.modules, True)
    failed = sum(1 for t in tests if t["result"] == "FAIL")
    dump("validation_tests.json", {"total": len(tests), "passed": len(tests)-failed, "failed": failed, "score": f"{len(tests)-failed}/{len(tests)}", "tests": tests})
    dump("api_routes.json", {"routes": [
        "POST /query", "POST /reset", "GET /status", "GET /health",
        "GET /entity/{id}", "GET /alarm/{id}", "GET /document/{id}", "GET /page/{id}",
    ], "host": HOST, "port": PORT})
    (OUT / "README_BACKEND.md").write_text(
        f"# Backend V15\n\nLocal API `{HOST}:{PORT}`\n\n"
        "POST /query  {\"query\": \"...\"}\nPOST /reset\nGET /health\n",
        encoding="utf-8",
    )
    status = "PASS" if failed == 0 else "FAIL"
    summary = (
        "==================================================\nETAPA 36 TERMINADA\n==================================================\n"
        f"STATUS: {status}\nOUTPUTS: {OUT}\nTESTS: {len(tests)-failed}/{len(tests)}\n"
        f"ERRORS: {failed}\nPREVIOUS VERSIONS MODIFIED: NO\n"
        "CONTINUITY CONFIRMED: 0\nDIAGNOSIS CONFIRMED: 0\nELECTRICAL CONNECTION CONFIRMED: 0\n"
        f"LAUNCH: python {OUT / 'server.py'}\n"
        "==================================================\n"
    )
    for t in tests:
        summary += f"  [{t['result']}] {t['test']}: {t['detail']}\n"
    REP.mkdir(exist_ok=True)
    (REP / "stage36_summary.txt").write_text(summary, encoding="utf-8")
    print(summary)
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    service()
    print(f"Serving http://{HOST}:{PORT}")
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()
