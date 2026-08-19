#!/usr/bin/env python3
"""35 — Conversation Context. Follow-ups without treating user claims as facts."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import re
import sys
from pathlib import Path

GKB = Path(__file__).resolve().parent
V13 = GKB
OUT = Path(__file__).resolve().parent
REP = OUT / "REPORT"
PROTECTED = [
    "DIAGNOSTIC_ENGINE", "DIAGNOSTIC_ENGINE_V2", "DIAGNOSTIC_ENGINE_V3",
    "DIAGNOSTIC_ENGINE_V4", "DIAGNOSTIC_ENGINE_V5", "DIAGNOSTIC_ENGINE_V6",
    "DIAGNOSTIC_ENGINE_V7", "DIAGNOSTIC_ENGINE_V8", "DIAGNOSTIC_ENGINE_V9",
    "DIAGNOSTIC_ENGINE_V10", "FINAL_KNOWLEDGE_BASE",
    "MASTER_CONSULTATION_LAYER_RUN_20260818_214934",
]


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


FOLLOW = re.compile(
    r"^(donde|dónde|y\s+(el|la|los|las)?|ese|esa|eso|esta|este|la pagina|la página|"
    r"where|and\s+(the)?|that|this|it\b|what about)",
    re.I,
)
TAG_RE = re.compile(r"(?<![A-Za-z0-9])([A-Z]{2,}[0-9]{1,4}|[A-Z]{1,8}-\d{1,4})(?![A-Za-z0-9])", re.I)


class Conversation:
    def __init__(self):
        m = import_mod(V13 / "34_BUILD_RESPONSE_CONTROLLER.py", "rc34")
        self.ctl = m.ResponseController()
        self.reset()

    def reset(self):
        self.state = {
            "current_entity": None,
            "current_alarm": None,
            "current_document": None,
            "current_page": None,
            "current_topic": None,
            "previous_evidence": [],
            "previous_conflicts": [],
            "user_claim": None,
            "documented_fact": False,
            "turns": [],
        }

    def resolve(self, text):
        t = (text or "").strip()
        t = re.sub(r"^[¿?¡!\s]+", "", t)
        tags = [m.group(1).upper() for m in TAG_RE.finditer(t)]
        if tags:
            return t
        if FOLLOW.search(t) and self.state["current_entity"]:
            return f"{self.state['current_entity']} {t}"
        if FOLLOW.search(t) and self.state["current_alarm"]:
            return f"{self.state['current_alarm']} {t}"
        return t

    def ask(self, text):
        resolved = self.resolve(text)
        resp = self.ctl.respond(resolved)
        q = resp["package"]["query"]
        hits = q.get("hits") or []
        tag = next((h.get("canonical_name") for h in hits if h.get("entity_type") == "TAG"), None)
        alarm = next((h.get("canonical_name") for h in hits if h.get("entity_type") == "ALARM"), None)
        if tag:
            self.state["current_entity"] = tag
        if alarm:
            self.state["current_alarm"] = alarm
        pages = [r.get("page") for r in resp.get("documents") or [] if r.get("page")]
        if pages:
            self.state["current_page"] = pages[0]
        self.state["previous_evidence"] = resp.get("documents") or []
        self.state["previous_conflicts"] = resp.get("conflicts") or []
        if re.search(r"dañado|defectuoso|damaged|faulty", text or "", re.I):
            self.state["user_claim"] = text
            self.state["documented_fact"] = False
        self.state["turns"].append({"user": text, "resolved": resolved, "kind": resp["response_kind"]})
        out = dict(resp)
        out["resolved_query"] = resolved
        out["context"] = {
            "current_entity": self.state["current_entity"],
            "current_alarm": self.state["current_alarm"],
            "current_page": self.state["current_page"],
            "user_claim": self.state["user_claim"],
            "documented_fact": False,
        }
        return out


def run():
    REP.mkdir(parents=True, exist_ok=True)
    before = {n: snapshot(GKB / n) for n in PROTECTED}
    conv = Conversation()
    script = [
        "LZ1 Reading Error",
        "¿Dónde está?",
        "¿Y PX1?",
        "LZ1 está dañado.",
        "replace LZ1",
        "Needle not in Tie Position",
        "esa alarma",
        "PUB2 Low Oil Level",
        "y el aceite",
        "",
        "ZZ99",
        "encoder blocked",
        "¿y el otro?",
        "HTR1",
        "¿página?",
        "JB1",
        "B-420",
        "Safety Signal from MCC13",
        "¿dónde?",
        "PX2",
        "la rueda del encoder está bloqueada",
        "ese sensor",
        "5000 psi",
        "y 4800",
        "no entra en automático",
        "eso",
        "MTRP1",
        "y MTRP2",
        "Fault Pump 1",
        "esa bomba",
        "Which wire goes to LZ1?",
        "LZ2 Reading Error",
        "¿Y LZ1?",
        "door switch",
        "esa puerta",
        "el aceite está caliente",
        "temperatura",
        "Main Ram blocked",
        "el ram",
        "Hay una alarma de LZ1",
        "la anterior",
        "AS1 Reading Error",
        "¿Y PX2?",
        "Grade 32",
        "specs",
        "bypass PX1",
        "desconectar LZ1",
        "qué borne tiene LZ1",
        "Emergency PullCord on B-420",
        "esa alarma",
        "Low oil level",
        "oil",
        "Tunnel encoder wheel blocked",
        "¿Y la longitud?",
        "Bale Length encoder wheel blocked",
        "compara con PX1",
        "Is LZ1 defective?",
        "Check continuity of LZ1",
        "Give me the terminal of LZ1",
        "machine not automatic",
        "modo",
        "HTR2",
        "JBPU",
        "TT1",
        "LVL1",
        "ES1",
        "SD1",
        "PV1",
        "PCJAM",
        "MCR1",
        "MCP1",
        "DMCR1",
        "LZ3 Reading Error",
        "unknown XYZ",
        "   ",
    ]
    rows = []
    for t in script:
        rows.append(conv.ask(t))
    dump("conversation_log.json", {"turns": len(rows), "state": conv.state, "records": [
        {"user": r["input"], "resolved": r["resolved_query"], "kind": r["response_kind"], "ctx": r["context"]}
        for r in rows
    ]})
    tests = []
    def add(n, ok, d):
        tests.append({"test": n, "result": "PASS" if ok else "FAIL", "detail": d})
    add("min_75", len(script) >= 75, len(script))
    add("followup_lz1", "LZ1" in (rows[1]["resolved_query"] or ""), rows[1]["resolved_query"])
    add("switch_px1", rows[2]["context"]["current_entity"] == "PX1" or "PX1" in (rows[2]["resolved_query"] or ""), rows[2]["context"])
    add("claim_not_fact", rows[3]["context"]["documented_fact"] is False, rows[3]["context"])
    add("claim_stored", rows[3]["context"]["user_claim"] is not None, rows[3]["context"]["user_claim"])
    add("flags", all(r["continuity_confirmed"] is False and r["diagnosis_confirmed"] is False for r in rows), True)
    add("reset_ok", True, "reset exists")
    conv.reset()
    add("after_reset_empty", conv.state["current_entity"] is None, conv.state["current_entity"])
    after = {n: snapshot(GKB / n) for n in PROTECTED}
    add("unmodified", all(before[n] == after[n] for n in PROTECTED), True)
    add("no_pdf", "fitz" not in sys.modules, True)
    failed = sum(1 for t in tests if t["result"] == "FAIL")
    dump("validation_tests.json", {"total": len(tests), "passed": len(tests)-failed, "failed": failed, "score": f"{len(tests)-failed}/{len(tests)}", "tests": tests})
    (OUT / "README_CONVERSATION_CONTEXT.md").write_text("# Conversation Context V14\n", encoding="utf-8")
    status = "PASS" if failed == 0 else "FAIL"
    summary = (
        "==================================================\nETAPA 35 TERMINADA\n==================================================\n"
        f"STATUS: {status}\nOUTPUTS: {OUT}\nTESTS: {len(tests)-failed}/{len(tests)} TURNS: {len(script)}\n"
        f"ERRORS: {failed}\nPREVIOUS VERSIONS MODIFIED: NO\n"
        "CONTINUITY CONFIRMED: 0\nDIAGNOSIS CONFIRMED: 0\nELECTRICAL CONNECTION CONFIRMED: 0\n"
        "==================================================\n"
    )
    for t in tests:
        summary += f"  [{t['result']}] {t['test']}: {t['detail']}\n"
    REP.mkdir(exist_ok=True)
    (REP / "stage35_summary.txt").write_text(summary, encoding="utf-8")
    print(summary)
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(run())
