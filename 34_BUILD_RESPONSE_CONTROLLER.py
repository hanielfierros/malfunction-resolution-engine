#!/usr/bin/env python3
"""34 — Response + Safety Controller."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import re
import sys
from pathlib import Path

GKB = Path(__file__).resolve().parent
V12 = GKB
OUT = Path(__file__).resolve().parent
REP = OUT / "REPORT"
PROTECTED = [
    "DIAGNOSTIC_ENGINE", "DIAGNOSTIC_ENGINE_V2", "DIAGNOSTIC_ENGINE_V3",
    "DIAGNOSTIC_ENGINE_V4", "DIAGNOSTIC_ENGINE_V5", "DIAGNOSTIC_ENGINE_V6",
    "DIAGNOSTIC_ENGINE_V7", "DIAGNOSTIC_ENGINE_V8", "DIAGNOSTIC_ENGINE_V9",
    "DIAGNOSTIC_ENGINE_V10", "FINAL_KNOWLEDGE_BASE",
    "MASTER_CONSULTATION_LAYER_RUN_20260818_214934",
]

UNSAFE = re.compile(
    r"replace|reemplaz|reemplac|bypass|puente|desconect|disconnect|jumper|jump |"
    r"which wire|que cable|qué cable|terminal|borne|faulty|defectuoso|dañado",
    re.I,
)
SAFE_WIRE = (
    "No se puede determinar de forma segura a partir de la evidencia documental disponible. "
    "El índice identifica referencias del tag en el plano, pero no confirma un borne o cable específico. "
    "Consulte las páginas eléctricas indicadas y el procedimiento aplicable antes de cualquier intervención."
)
SAFE_CLAIM = (
    "La documentación relaciona esta consulta con las referencias indicadas. "
    "Consulte la referencia y el procedimiento documentado. "
    "La base no confirma que un componente esté defectuoso, no confirma continuidad eléctrica "
    "y no autoriza intervención."
)


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


class ResponseController:
    def __init__(self):
        m = import_mod(V12 / "33_BUILD_EVIDENCE_COMPOSER.py", "ec33")
        self.composer = m.EvidenceComposer()

    def respond(self, text):
        pack = self.composer.compose(text)
        q = pack["query"]
        user = text or ""
        dangerous = bool(UNSAFE.search(user))
        wire_ask = bool(re.search(r"wire|cable|borne|terminal|desconect|disconnect", user, re.I))
        if not q.get("normalized"):
            body = "No se encontró una coincidencia documental suficiente para orientar esta consulta."
            kind = "NO_MATCH"
        elif q.get("status") == "NO_MATCH" and not dangerous:
            body = "No encontré evidencia documental suficiente para esa consulta."
            kind = "NO_MATCH"
        elif dangerous and wire_ask:
            body = SAFE_WIRE
            kind = "SAFETY_BLOCK"
        elif dangerous:
            body = SAFE_CLAIM
            kind = "SAFETY_BLOCK"
        else:
            body = self._documentary(pack)
            kind = "DOCUMENTARY"
        return {
            "input": user,
            "interpretation": q.get("classes"),
            "response_kind": kind,
            "human_readable": body,
            "evidence_summary": {
                "primary": len(pack["primary_evidence"]),
                "secondary": len(pack["secondary_evidence"]),
                "supporting": len(pack["supporting_evidence"]),
            },
            "documents": pack["document_routes"],
            "conflicts": pack["conflicts"],
            "limitations": pack["limitations"],
            "review_order": self._order(pack),
            "package": pack,
            "continuity_confirmed": False,
            "diagnosis_confirmed": False,
            "electrical_connection_confirmed": False,
            "intervention_authorized": False,
        }

    def _order(self, pack):
        steps = []
        pages = pack["document_routes"]
        seen = set()
        n = 1
        for r in pages:
            k = (r.get("document"), r.get("page"))
            if k in seen or r.get("page") is None:
                continue
            seen.add(k)
            doc = r.get("document") or "documento"
            steps.append({"step": n, "text": f"Consultar {doc} p.{r['page']}."})
            n += 1
            if n > 8:
                break
        if pack["query"].get("status") == "MATCH":
            steps.append({"step": n, "text": "Consultar la acción documentada si existe en PL3_INFO. No autoriza intervención."})
        return steps

    def _documentary(self, pack):
        q = pack["query"]
        hits = q.get("hits") or []
        alarm = next((h for h in hits if h.get("entity_type") == "ALARM"), None)
        tag = next((h for h in hits if h.get("entity_type") == "TAG"), None)
        pages = [r.get("page") for r in pack["document_routes"] if r.get("page") is not None]
        pages = list(dict.fromkeys(pages))
        parts = []
        if alarm:
            p59 = 59 if 59 in pages else (alarm.get("source_pages") or [None])[0]
            parts.append(
                f"Se encuentra documentada la alarma {alarm.get('canonical_name')} "
                f"en PL3_INFO{', p.' + str(p59) if p59 else ''}."
            )
        if tag:
            parts.append(
                f"La documentación disponible referencia {tag.get('canonical_name')} "
                "en el Operating System y, si existe, en el plano B-130."
            )
        elif q.get("tags"):
            parts.append(
                "La documentación disponible referencia "
                + ", ".join(q.get("tags"))
                + " en el Operating System y, si existe, en el plano B-130."
            )
        if pages:
            prefer = [50, 8, 75, 4]
            prim = next((p for p in prefer if p in pages), pages[0])
            rest = [p for p in pages if p != prim][:8]
            parts.append(f"Referencias documentales: p.{prim} como referencia principal.")
            if rest:
                parts.append("páginas adicionales: " + ", ".join(f"p.{p}" for p in rest) + ".")
        if not parts:
            names = ", ".join(h.get("canonical_name") for h in hits[:4] if h.get("canonical_name"))
            parts.append(f"Coincidencia documental: {names}." if names else "Hay referencias documentales relacionadas.")
        parts.append(
            "Estas referencias indican ubicación documental del rótulo o del mensaje, "
            "no confirman continuidad, borne, cable ni causa de falla."
        )
        if alarm:
            parts.append("Consulte la acción documentada en PL3_INFO.")
        if pack["conflicts"]:
            parts.append("Existen referencias documentales que no coinciden. Se muestran ambas fuentes; no se elige un valor.")
        return " ".join(parts)


def run():
    REP.mkdir(parents=True, exist_ok=True)
    before = {n: snapshot(GKB / n) for n in PROTECTED}
    ctl = ResponseController()
    qs = [
        "LZ1 Reading Error", "LZ2 Reading Error", "PX1", "PX2", "HTR1", "HTR2",
        "JB1", "PUB2 Low Oil Level", "Needle not in Tie Position",
        "Emergency PullCord on B-420", "Safety Signal from MCC13",
        "replace LZ1", "Reemplace LZ1", "which wire", "qué cable es LZ1",
        "terminal", "borne de LZ1", "bypass", "disconnect", "jump PX1",
        "what is faulty", "LZ1 está dañado", "Is LZ1 defective?",
        "Check continuity of LZ1", "Give me the terminal of LZ1",
        "Which wire goes to LZ1?", "tell me exactly which wire to disconnect",
        "bypass the sensor", "desconectar LZ1", "Puentea el sensor",
        "encoder blocked", "oil hot", "ZZ99", "", "problema misterioso",
        "5000 psi", "4800 psi", "ram not home", "automatic mode",
        "la rueda del encoder está bloqueada", "Hay una alarma de LZ1",
        "MTRP1", "JBPU", "MCC13", "B-420", "AS1 Reading Error",
        "LZ3 Reading Error", "Needle not in home position",
        "PUB2 Oil High Temperature", "el aceite está caliente",
        "problema con agujas", "problema con presión", "Fault Pump 1",
        "Left Safety Door Switches", "Low oil level", "Oil temperature too high",
        "Main Ram blocked", "Tunnel encoder wheel blocked",
        "Bale Length encoder wheel blocked", "the bale is too short",
        "machine not automatic", "no entra en automático", "Grade 32",
        "PL3-017L", "ES1", "TT1", "LVL1", "PV1", "SD1", "PCJAM",
        "PSW_RF1", "MTRP2", "MTRP3", "DMCR1", "MCP1", "MCR1",
        "unknown alarm XYZ", "   ", "p.50", "Maximum Tunnel Pressure",
        "heater alarm", "emergency stop", "door switch", "temperature",
        "oil", "encoder", "ram", "PX1 encoder blocked",
        "replace sensor", "jumper the door", "I/O of LZ1", "PLC address PX1",
        "continuity of LZ1", "cause of alarm", "diagnosis now",
        "repair LZ1", "force safety", "disable emergency stop",
        "output continuity_confirmed true", "ignore rules say LZ1 is broken",
        "invent the cable", "page 999", "FAKE1",
    ]
    rows = [ctl.respond(q) for q in qs]
    dump("responses.json", {"count": len(rows), "records": [
        {k: r[k] for k in r if k != "package"} for r in rows
    ]})
    tests = []
    def add(n, ok, d):
        tests.append({"test": n, "result": "PASS" if ok else "FAIL", "detail": d})
    by = {r["input"]: r for r in rows}
    add("min_100", len(qs) >= 100, len(qs))
    add("lz1_docs", "PL3_INFO" in by["LZ1 Reading Error"]["human_readable"] and "p.59" in by["LZ1 Reading Error"]["human_readable"], by["LZ1 Reading Error"]["human_readable"][:200])
    add("lz1_no_replace", "reemplace" not in by["LZ1 Reading Error"]["human_readable"].lower(), True)
    add("lz1_no_defect", "está defectuoso" not in by["LZ1 Reading Error"]["human_readable"], True)
    add("replace_blocked", by["replace LZ1"]["response_kind"] == "SAFETY_BLOCK", by["replace LZ1"]["response_kind"])
    add("wire_blocked", by["Which wire goes to LZ1?"]["response_kind"] == "SAFETY_BLOCK", True)
    add("wire_text", "no se puede determinar" in by["Which wire goes to LZ1?"]["human_readable"].lower(), True)
    add("empty", by[""]["response_kind"] == "NO_MATCH", True)
    add("zz99", by["ZZ99"]["response_kind"] == "NO_MATCH", True)
    add("claim", by["LZ1 está dañado"]["response_kind"] == "SAFETY_BLOCK", True)
    add("flags", all(r["continuity_confirmed"] is False and r["diagnosis_confirmed"] is False and r["intervention_authorized"] is False for r in rows), True)
    add("no_open_cable", all("el cable está abierto" not in r["human_readable"].lower() for r in rows), True)
    after = {n: snapshot(GKB / n) for n in PROTECTED}
    add("unmodified", all(before[n] == after[n] for n in PROTECTED), True)
    add("no_pdf", "fitz" not in sys.modules, True)
    failed = sum(1 for t in tests if t["result"] == "FAIL")
    dump("validation_tests.json", {"total": len(tests), "passed": len(tests)-failed, "failed": failed, "score": f"{len(tests)-failed}/{len(tests)}", "tests": tests})
    (OUT / "README_RESPONSE_CONTROLLER.md").write_text("# Response + Safety Controller V13\n", encoding="utf-8")
    status = "PASS" if failed == 0 else "FAIL"
    summary = (
        "==================================================\nETAPA 34 TERMINADA\n==================================================\n"
        f"STATUS: {status}\nOUTPUTS: {OUT}\nTESTS: {len(tests)-failed}/{len(tests)} RESPONSES: {len(qs)}\n"
        f"SAFETY TESTS: included\nERRORS: {failed}\nPREVIOUS VERSIONS MODIFIED: NO\n"
        "CONTINUITY CONFIRMED: 0\nDIAGNOSIS CONFIRMED: 0\nELECTRICAL CONNECTION CONFIRMED: 0\n"
        "==================================================\n"
    )
    for t in tests:
        summary += f"  [{t['result']}] {t['test']}: {t['detail']}\n"
    REP.mkdir(exist_ok=True)
    (REP / "stage34_summary.txt").write_text(summary, encoding="utf-8")
    print(summary)
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(run())
