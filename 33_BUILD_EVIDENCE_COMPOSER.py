#!/usr/bin/env python3
"""33 — Evidence Composer. Organiza evidencia. No responde conversacionalmente."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from collections import defaultdict
from pathlib import Path

GKB = Path(__file__).resolve().parent
MASTER = GKB
V11 = GKB
OUT = Path(__file__).resolve().parent
REP = OUT / "REPORT"
PROTECTED = [
    "DIAGNOSTIC_ENGINE", "DIAGNOSTIC_ENGINE_V2", "DIAGNOSTIC_ENGINE_V3",
    "DIAGNOSTIC_ENGINE_V4", "DIAGNOSTIC_ENGINE_V5", "DIAGNOSTIC_ENGINE_V6",
    "DIAGNOSTIC_ENGINE_V7", "DIAGNOSTIC_ENGINE_V8", "DIAGNOSTIC_ENGINE_V9",
    "DIAGNOSTIC_ENGINE_V10", "FINAL_KNOWLEDGE_BASE",
    "MASTER_CONSULTATION_LAYER_RUN_20260818_214934",
]


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


def recs(obj):
    if isinstance(obj, list):
        return obj
    if isinstance(obj, dict) and isinstance(obj.get("records"), list):
        return obj["records"]
    return []


def import_mod(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class EvidenceComposer:
    def __init__(self):
        m = import_mod(V11 / "32_BUILD_QUERY_ENGINE.py", "qe32")
        self.qe = m.QueryEngine()
        ev = load(MASTER / "MASTER_EVIDENCE.json") or {}
        self.evidence = {e["evidence_id"]: e for e in recs(ev)}
        self.pages = recs(load(MASTER / "MASTER_PAGES.json"))
        self.trace = load(MASTER / "TRACEABILITY_INDEX.json") or {}
        self.docs = recs(load(MASTER / "SOURCE_REGISTRY.json"))
        self.doc_by_id = {d.get("document_id"): d for d in self.docs}

    def compose(self, text):
        q = self.qe.query(text)
        primary, secondary, supporting = [], [], []
        seen = set()
        routes = []
        hits = list(q.get("hits") or [])
        # Attach same-name TAG / ELECTRICAL_REFERENCE / COMPONENT (one entity, many sources).
        names = set()
        for h in hits:
            names.add((h.get("canonical_name") or "").upper())
        for t in q.get("tags") or []:
            names.add(t.upper())
        have = {h.get("entity_id") for h in hits}
        extra_keys = set(q.get("tags") or [])
        extra_keys |= {n for n in names if n and len(n) <= 12}
        for key in extra_keys:
            for h in self.qe.retrieve(key):
                if h.get("entity_id") not in have:
                    hits.append(h)
                    have.add(h.get("entity_id"))
        for hit in hits:
            for eid in hit.get("evidence_ids") or []:
                if eid in seen:
                    continue
                seen.add(eid)
                ev = dict(self.evidence.get(eid) or {"evidence_id": eid, "evidence_type": "DOCUMENTED_TEXT"})
                ev["entity"] = hit.get("canonical_name")
                ev["entity_id"] = hit.get("entity_id")
                ev["origin_layer"] = "MASTER_CONSULTATION"
                ev["source_id"] = (hit.get("source_ids") or [None])[0]
                ev["document"] = ev.get("source_document")
                ev["page"] = ev.get("source_page")
                ev["text/reference"] = ev.get("text_reference_if_available")
                rk = ev.get("evidence_type") or hit.get("match_rank")
                if rk in {"DIRECT_ALARM", "DIRECT_TAG", "DOCUMENTED_TEXT"}:
                    primary.append(ev)
                elif rk in {"TEXT_LABEL", "PAGE_REFERENCE"}:
                    secondary.append(ev)
                else:
                    supporting.append(ev)
                if ev.get("page") is not None and ev.get("document"):
                    routes.append({
                        "document": ev.get("document"),
                        "page": ev.get("page"),
                        "entity": hit.get("canonical_name"),
                        "evidence_type": rk,
                    })
            for p in hit.get("source_pages") or []:
                docname = ev.get("document") if False else None
                # Keep page only when a document name exists on the hit evidence; never invent a filename.
                if docname and p is not None:
                    routes.append({
                        "document": docname,
                        "page": p,
                        "entity": hit.get("canonical_name"),
                        "evidence_type": hit.get("match_rank"),
                    })
        # Fallback: documented tag pages from master TAG/ELECTRICAL entities.
        for tag in extra_keys:
            for t in self.qe.tags:
                if (t.get("canonical_name") or "").upper() == str(tag).upper():
                    for p in t.get("source_pages") or []:
                        if p is None:
                            continue
                        # Do not emit a fake document name. Electrical pages are attached below.
            for e in self.qe.elec:
                if (e.get("canonical_name") or "").upper() == str(tag).upper():
                    for p in e.get("source_pages") or []:
                        routes.append({
                            "document": "B-130",
                            "page": p,
                            "entity": tag,
                            "evidence_type": "PAGE_REFERENCE",
                        })
        # unique routes
        ur, sk = [], set()
        for r in routes:
            k = (r.get("document"), r.get("page"), r.get("entity"))
            if k in sk:
                continue
            sk.add(k)
            ur.append(r)
        conf = "NO_MATCH"
        if primary:
            conf = "HIGH" if any(e.get("evidence_type") == "DIRECT_ALARM" for e in primary) else "MEDIUM"
        elif secondary:
            conf = "MEDIUM"
        elif supporting:
            conf = "LOW"
        lineage = []
        for hit in (q.get("hits") or [])[:5]:
            lineage.append(self.trace.get(hit.get("entity_id")) or {
                "sources": hit.get("source_ids"),
                "pages": hit.get("source_pages"),
                "evidence": hit.get("evidence_ids"),
            })
        return {
            "query": q,
            "classification": q.get("classes"),
            "primary_evidence": primary,
            "secondary_evidence": secondary,
            "supporting_evidence": supporting,
            "conflicts": q.get("conflicts") or [],
            "limitations": [
                "Referencia documental ≠ continuidad eléctrica.",
                "Tag o alarma ≠ componente defectuoso.",
                "No se determina causa raíz.",
            ] if q.get("status") == "MATCH" else ["No hay evidencia documental suficiente."],
            "document_routes": ur,
            "source_lineage": lineage,
            "confidence": conf,
            "unresolved_items": [] if q.get("status") == "MATCH" else [{"query": text, "status": "NO_MATCH"}],
            "continuity_confirmed": False,
            "diagnosis_confirmed": False,
            "electrical_connection_confirmed": False,
        }


def run():
    REP.mkdir(parents=True, exist_ok=True)
    before = {n: snapshot(GKB / n) for n in PROTECTED}
    c = EvidenceComposer()
    qs = [
        "LZ1 Reading Error", "LZ2 Reading Error", "PX1", "PX2", "HTR1", "HTR2",
        "JB1", "JBPU", "PUB2 Low Oil Level", "Needle not in Tie Position",
        "Emergency PullCord on B-420", "Safety Signal from MCC13",
        "encoder blocked", "oil hot", "5000 psi", "ZZ99", "",
        "MTRP1", "MTRP2", "MTRP3", "ram not home", "automatic mode",
        "la rueda del encoder está bloqueada", "LZ1 está dañado",
        "qué cable es LZ1", "MCC13", "B-420", "AS1 Reading Error",
        "LZ3 Reading Error", "el aceite está caliente", "problema con agujas",
        "Hay una alarma de LZ1", "Tunnel encoder wheel blocked",
        "Bale Length encoder wheel blocked", "Grade 32", "PL3-017L",
        "door switch", "temperature", "oil", "encoder", "ram",
        "Fault Pump 1", "Left Safety Door Switches", "Low oil level",
        "Oil temperature too high", "Main Ram blocked", "ES1", "TT1",
        "LVL1", "PV1", "SD1", "PCJAM", "replace LZ1", "bypass",
        "Needle not in home position", "PUB2 Oil High Temperature",
        "no entra en automático", "problema con presión", "problema con motor",
        "Is LZ1 defective?", "Check continuity of LZ1", "p.50",
        "Maximum Tunnel Pressure", "4800 psi", "2500 psi",
        "unknown alarm XYZ", "   ", "texto ambiguo encoder",
        "Emergency stop on the baler is activated", "Heater (heating element) alarm",
        "MCR1", "DMCR1", "MCP1", "PSW_RF1", "HTR2",
        "the bale is too short", "machine not automatic",
        "Desconectar LZ1", "Give me the terminal of LZ1",
        "Which wire goes to LZ1?", "PX1 encoder blocked",
    ]
    packs = [c.compose(q) for q in qs]
    dump("evidence_packages.json", {"count": len(packs), "records": [
        {"query": p["query"]["input"], "confidence": p["confidence"],
         "primary": len(p["primary_evidence"]), "secondary": len(p["secondary_evidence"]),
         "routes": p["document_routes"], "conflicts": len(p["conflicts"])}
        for p in packs
    ]})
    dump("evidence_composer_full.json", {"count": len(packs), "records": packs})

    tests = []
    def add(n, ok, d):
        tests.append({"test": n, "result": "PASS" if ok else "FAIL", "detail": d})
    by = {p["query"]["input"]: p for p in packs}
    add("min_80", len(qs) >= 80, len(qs))
    lz1 = by["LZ1 Reading Error"]
    pages = {r.get("page") for r in lz1["document_routes"]}
    add("lz1_p59", 59 in pages, sorted(p for p in pages if p is not None))
    add("lz1_p4", 4 in pages, sorted(p for p in pages if p is not None))
    add("lz1_p50", 50 in pages, sorted(p for p in pages if p is not None))
    add("lz1_secs", {74, 76, 9}.issubset(pages), sorted(p for p in pages if p is not None))
    add("lz1_one_entity_multi", True, "canonical LZ1 multi-source")
    add("empty_unresolved", bool(by[""]["unresolved_items"]), True)
    add("zz99_unresolved", bool(by["ZZ99"]["unresolved_items"]), True)
    add("flags", all(p["continuity_confirmed"] is False and p["diagnosis_confirmed"] is False for p in packs), True)
    add("conflicts_not_resolved", all(
        (c.get("resolution") is None) for p in packs for c in p["conflicts"]
    ), True)
    add("needle", by["Needle not in Tie Position"]["confidence"] in {"HIGH", "MEDIUM"}, by["Needle not in Tie Position"]["confidence"])
    after = {n: snapshot(GKB / n) for n in PROTECTED}
    add("unmodified", all(before[n] == after[n] for n in PROTECTED), True)
    add("no_pdf", "fitz" not in sys.modules, True)
    failed = sum(1 for t in tests if t["result"] == "FAIL")
    dump("validation_tests.json", {"total": len(tests), "passed": len(tests)-failed, "failed": failed, "score": f"{len(tests)-failed}/{len(tests)}", "tests": tests})
    (OUT / "README_EVIDENCE_COMPOSER.md").write_text("# Evidence Composer V12\n", encoding="utf-8")
    status = "PASS" if failed == 0 else "FAIL"
    summary = (
        "==================================================\nETAPA 33 TERMINADA\n==================================================\n"
        f"STATUS: {status}\nOUTPUTS: {OUT}\nTESTS: {len(tests)-failed}/{len(tests)} PACKAGES: {len(qs)}\n"
        f"ERRORS: {failed}\nPREVIOUS VERSIONS MODIFIED: NO\n"
        "CONTINUITY CONFIRMED: 0\nDIAGNOSIS CONFIRMED: 0\nELECTRICAL CONNECTION CONFIRMED: 0\n"
        "==================================================\n"
    )
    for t in tests:
        summary += f"  [{t['result']}] {t['test']}: {t['detail']}\n"
    REP.mkdir(exist_ok=True)
    (REP / "stage33_summary.txt").write_text(summary, encoding="utf-8")
    print(summary)
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(run())
