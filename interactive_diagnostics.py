"""Interactive diagnostics layer. Extends documentary lookup without inventing facts."""
from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path

from document_resolver import DocumentResolver
from i18n_engine import lang_of, need_more_block, t

ROOT = Path(__file__).resolve().parent

STOP = {
    "the", "a", "an", "of", "and", "or", "to", "in", "on", "is", "are", "was",
    "be", "for", "with", "from", "at", "it", "this", "that", "not", "no",
    "making", "make", "strange", "very", "too", "has", "have", "does", "do",
    "el", "la", "los", "las", "de", "un", "una", "es", "hay", "que", "se",
    "le", "les", "en", "y", "o", "del", "al",
}

SYN = {
    "noise": "noisy", "ruido": "noisy", "noisy": "noisy",
    "vibration": "vibrat", "vibrates": "vibrat", "vibra": "vibrat",
    "overheat": "temperature", "overheats": "temperature", "hot": "temperature",
    "caliente": "temperature", "heat": "temperature",
    "slipping": "slip", "slips": "slip", "belt": "belt",
    "motor": "motor", "fan": "fan", "pump": "pump", "oil": "oil",
    "laser": "laser", "conveyor": "conveyor", "grinder": "grinder",
    "crusher": "crusher", "glass": "glass", "weak": "power",
    "power": "power", "slow": "slow", "smell": "smell", "burning": "smell",
    "stops": "stop", "stopped": "stop", "intermittent": "intermittent",
    "alarm": "alarm", "falla": "fault", "fault": "fault",
    "failure": "fault", "working": "work", "work": "work",
    "malfunction": "fault", "stopped": "stop", "unusual": "noisy",
    "sound": "noisy", "slipping": "slip", "turning": "work",
    "grinding": "noisy", "squealing": "noisy", "rattling": "noisy",
    "knocking": "noisy", "humming": "noisy", "shaking": "vibrat",
    "spinning": "work", "giro": "work", "banda": "belt", "correa": "belt",
}

CLASS_RULES = [
    ("alarm", ("alarm", "reading error", "fault")),
    ("noise", ("noise", "noisy", "ruido")),
    ("vibration", ("vibrat", "shaking", "shake")),
    ("overheating", ("overheat", "temperature", "hot", "caliente")),
    ("loss_of_power", ("power", "weak", "slow")),
    ("intermittent", ("intermittent", "sometimes")),
    ("mechanical", ("motor", "belt", "fan", "ram", "needle", "conveyor", "bearing")),
    ("hydraulic", ("oil", "pump", "hydraulic", "cylinder", "leak")),
    ("electrical", ("wire", "sensor", "encoder", "plc", "heater")),
    ("pneumatic", ("air", "pneumatic")),
    ("control", ("automatic", "plc", "mode")),
    ("component", ("motor", "fan", "pump", "laser", "grinder")),
    ("symptom", ("noise", "vibrat", "smell", "stop", "hot", "grind", "shake")),
    ("mechanical", ("grind", "slip", "shake", "spin")),
]


def _load(name):
    p = ROOT / name
    if not p.exists():
        return {}
    return json.loads(p.read_text(encoding="utf-8"))


def _now():
    return datetime.now(timezone.utc).isoformat()


def tokens(text: str) -> set[str]:
    n = (text or "").lower()
    n = n.replace("á", "a").replace("é", "e").replace("í", "i").replace("ó", "o").replace("ú", "u")
    parts = re.findall(r"[a-z0-9]+", n)
    out = set()
    for p in parts:
        if p in STOP or len(p) < 3:
            continue
        out.add(SYN.get(p, p))
        out.add(p)
    return out


def classify_text(text: str) -> list[str]:
    n = (text or "").lower()
    found = []
    for label, keys in CLASS_RULES:
        if any(k in n for k in keys):
            found.append(label)
    if not found:
        found.append("unknown")
    seen, out = set(), []
    for x in found:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out


class DocumentCatalog:
    def __init__(self):
        self.resolver = DocumentResolver()
        self.docs = self.resolver.documents

    def resolve(self, document_name, page) -> dict:
        row = self.resolver.resolve(document_name=document_name, page=page)
        if row.get("page") is None:
            return {
                "document_id": row.get("document_id"),
                "document_name": row.get("document_name") or document_name,
                "short_name": row.get("short_name"),
                "page": None,
                "page_label": None,
                "section": None,
                "pdf_url": None,
                "status": row.get("status") or "PENDING_DOCUMENT_HOSTING",
                "hosting_status": row.get("hosting_status") or "PENDING_DOCUMENT_HOSTING",
                "reference_type": row.get("reference_type") or "official_documentation",
                "viewer_target": None,
                "available": False,
            }
        row.setdefault("status", row.get("hosting_status") or "PENDING_DOCUMENT_HOSTING")
        return row


class LexicalKnowledge:
    """Phrase matching against documented names only."""

    def __init__(self):
        def recs(obj):
            if isinstance(obj, list):
                return obj
            if isinstance(obj, dict) and isinstance(obj.get("records"), list):
                return obj["records"]
            return []

        self.alarms = recs(_load("MASTER_ALARMS.json"))
        self.procs = recs(_load("MASTER_PROCEDURES.json"))
        self.syms = recs(_load("MASTER_SYMPTOMS.json"))
        self.comps = recs(_load("MASTER_COMPONENTS.json"))
        self.corpus = []
        for coll, kind in (
            (self.alarms, "alarm"),
            (self.procs, "procedure"),
            (self.comps, "component"),
        ):
            for e in coll:
                name = e.get("canonical_name") or ""
                self.corpus.append({
                    "kind": kind,
                    "name": name,
                    "tok": tokens(name),
                    "pages": e.get("source_pages") or [],
                    "entity_id": e.get("entity_id"),
                    "evidence_ids": e.get("evidence_ids") or [],
                })

    def match(self, text: str, limit=8) -> list[dict]:
        q = tokens(text)
        if not q:
            return []
        scored = []
        for row in self.corpus:
            overlap = q & row["tok"]
            if not overlap:
                continue
            # require a content token, not only 'fault'/'alarm'
            content = overlap - {"fault", "alarm", "error", "reading", "documented", "action"}
            if not content and len(overlap) < 2:
                continue
            score = len(content) * 2 + len(overlap)
            # phrase containment bonus
            nl = row["name"].lower()
            ql = (text or "").lower()
            if len(nl) >= 10 and nl in ql:
                score += 8
            if score < 2:
                continue
            hit = dict(row)
            hit["score"] = score
            hit["overlap"] = sorted(overlap)
            scored.append(hit)
        scored.sort(key=lambda x: -x["score"])
        # de-dupe names
        seen, out = set(), []
        for s in scored:
            if s["name"] in seen:
                continue
            seen.add(s["name"])
            out.append(s)
            if len(out) >= limit:
                break
        return out


QUESTION_KEYS = [
    ("when", "q_when"),
    ("continuous", "q_continuous"),
    ("load", "q_load"),
    ("noise", "q_noise"),
    ("vibration", "q_vibration"),
    ("heat", "q_heat"),
    ("alarm", "q_alarm"),
    ("power", "q_power"),
    ("recent", "q_recent"),
    ("restart", "q_restart"),
    ("where", "q_where"),
    ("speed", "q_speed"),
    ("obstruction", "q_obstruction"),
    ("subsystem", "q_subsystem"),
    ("stopped", "q_stopped"),
    ("sudden", "q_sudden"),
]


class Case:
    def __init__(self):
        self.id = str(uuid.uuid4())
        self.status = "OPEN"
        self.initial_report = None
        self.conversation = []
        self.observations = []
        self.components = []
        self.symptoms = []
        self.alarms = []
        self.questions_asked = []
        self.answers = []
        self.evidence = []
        self.photos = []
        self.audio = []
        self.hypotheses = []
        self.tests = []
        self.checklist = []
        self.completed_steps = []
        self.documents = []
        self.pages = []
        self.external_sources = []
        self.safety_flags = {
            "continuity_confirmed": False,
            "diagnosis_confirmed": False,
            "electrical_connection_confirmed": False,
        }
        self.resolution_status = "OPEN"
        self.final_resolution = None
        self.classes = []
        self.pending_question = None
        self.pending_question_key = None
        self.language = "en"
        self.confidence = "INSUFFICIENT_EVIDENCE"

    def to_public(self):
        return {
            "case_id": self.id,
            "status": self.status,
            "resolution_status": self.resolution_status,
            "initial_report": self.initial_report,
            "turns": len(self.conversation),
        }


class InteractiveEngine:
    def __init__(self):
        self.lex = LexicalKnowledge()
        self.catalog = DocumentCatalog()
        self.case = Case()

    def reset(self):
        self.case = Case()

    def ingest_evidence(self, items) -> list[dict]:
        accepted = []
        for it in items or []:
            if not isinstance(it, dict):
                continue
            kind = (it.get("type") or "").lower()
            rec = {
                "type": "photo" if kind in {"photo", "image"} else "audio" if kind == "audio" else kind or "unknown",
                "id": it.get("id") or str(uuid.uuid4()),
                "filename": it.get("filename") or (it.get("metadata") or {}).get("filename"),
                "mime_type": it.get("mime_type") or (it.get("metadata") or {}).get("mime_type") or it.get("mime"),
                "duration": it.get("duration") or (it.get("metadata") or {}).get("duration"),
                "metadata": it.get("metadata") or {},
                "status": "RECEIVED",
                "analysis": "ANALYSIS_UNAVAILABLE",
                "analysis_status": "ANALYSIS_UNAVAILABLE",
                "note": "EVIDENCE_REQUIRES_ANALYSIS",
            }
            accepted.append(rec)
            if rec["type"] == "photo":
                self.case.photos.append(rec)
            elif rec["type"] == "audio":
                self.case.audio.append(rec)
            self.case.evidence.append(rec)
        return accepted

    def _pick_questions(self, text, classes, n=3, lang="en") -> list[str]:
        asked = set(self.case.questions_asked)
        wanted = []
        cl = set(classes)
        if "noise" in cl:
            wanted += ["noise", "load", "speed", "where"]
        if "vibration" in cl:
            wanted += ["vibration", "load", "where"]
        if "overheating" in cl:
            wanted += ["heat", "load"]
        if "loss_of_power" in cl:
            wanted += ["power", "load", "obstruction"]
        if "alarm" not in cl:
            wanted.append("alarm")
        wanted += ["when", "continuous", "sudden", "recent", "restart", "power", "stopped"]
        keymap = dict(QUESTION_KEYS)
        out = []
        for key in wanted:
            ik = keymap.get(key)
            if not ik:
                continue
            q = t(lang, ik)
            if not q or q in asked:
                continue
            out.append(q)
            if len(out) >= n:
                break
        return out

    def _hypotheses(self, matches, lang="en") -> list[dict]:
        hyps = []
        for m in matches[:5]:
            pages = [p for p in (m.get("pages") or []) if p is not None]
            level = "SUPPORTED" if m.get("kind") == "alarm" else "POSSIBLE"
            refs = []
            for p in pages[:4]:
                row = self.catalog.resolve("PL3_INFO", p)
                if row.get("page"):
                    refs.append({"document_id": row.get("document_id") or "PL3_INFO", "page": row["page"]})
            hyps.append({
                "id": m.get("entity_id"),
                "component": m.get("name"),
                "hypothesis": m.get("name"),
                "statement": m.get("name"),
                "status": level,
                "level": level,
                "kind": m.get("kind"),
                "evidence": [
                    {"documented_name": m.get("name"), "pages": pages, "overlap": m.get("overlap")}
                ],
                "required_checks": [t(lang, "chk_desc", name=m.get("name"))],
                "note": t(lang, "hyp_note"),
            })
        if not hyps:
            hyps.append({
                "id": None,
                "component": None,
                "hypothesis": "INSUFFICIENT_EVIDENCE",
                "statement": "INSUFFICIENT_EVIDENCE",
                "status": "INSUFFICIENT_EVIDENCE",
                "level": "INSUFFICIENT_EVIDENCE",
                "kind": None,
                "evidence": [],
                "required_checks": [],
                "note": t(lang, "hyp_note"),
            })
        return hyps

    def _checklist(self, matches, lang="en") -> list[dict]:
        steps = []
        for i, m in enumerate(matches[:6], start=1):
            pages = [p for p in (m.get("pages") or []) if p is not None]
            page = pages[0] if pages else None
            doc_refs = []
            if page is not None:
                row = self.catalog.resolve("PL3_INFO", page)
                if row.get("page"):
                    doc_refs.append({
                        "document_id": row.get("short_name") or row.get("document_id") or "PL3_INFO",
                        "document_name": row.get("document_name"),
                        "page": row["page"],
                    })
            sid = f"CHK-{i:03d}"
            steps.append({
                "id": sid,
                "step_id": sid,
                "title": m.get("name"),
                "description": t(lang, "chk_desc", name=m.get("name")),
                "status": "PENDING",
                "safety_level": "documentary",
                "requires_confirmation": True,
                "safety": t(lang, "chk_safety"),
                "expected_result": t(lang, "chk_expected"),
                "failure_result": t(lang, "chk_fail"),
                "document_reference": doc_refs[0] if doc_refs else None,
                "document_references": doc_refs,
                "page": page,
            })
        return steps

    def document_references(self, documents) -> list[dict]:
        refs = []
        seen = set()
        for d in documents or []:
            name = d.get("document")
            page = d.get("page")
            if not name or page is None:
                continue
            key = (name, page)
            if key in seen:
                continue
            seen.add(key)
            row = self.catalog.resolve(name, page)
            if row.get("page") is None:
                continue
            row["entity"] = d.get("entity")
            row["evidence_type"] = d.get("evidence_type")
            row["official_name"] = row.get("document_name")
            row["source"] = "official_documentation"
            row["relevance"] = d.get("evidence_type") or "DOCUMENTARY_EVIDENCE"
            row["availability"] = bool(row.get("available"))
            refs.append(row)
        return refs

    def apply(self, user_text, documentary: dict, extra=None) -> dict:
        extra = extra or {}
        lang = lang_of(extra.get("language") or extra.get("lang") or self.case.language)
        self.case.language = lang
        text = user_text or ""
        case = self.case
        obs = extra.get("observation") or extra.get("observations")
        if isinstance(obs, str) and obs.strip():
            case.observations.append({"text": obs.strip(), "ts": _now(), "source": "client"})
        elif isinstance(obs, list):
            for item in obs:
                if item:
                    case.observations.append({"text": str(item), "ts": _now(), "source": "client"})
        done_id = extra.get("step_completed") or extra.get("completed_step")
        if done_id:
            for st in case.checklist:
                if st.get("id") == done_id or st.get("step_id") == done_id:
                    st["status"] = "COMPLETED"
                    if done_id not in case.completed_steps:
                        case.completed_steps.append(done_id)
        if extra.get("issue_persists"):
            case.final_resolution = None
        if extra.get("issue_resolved") is True:
            case.final_resolution = "USER_DECLARED"
        low = text.lower()
        if any(x in low for x in ("also ", "además", "aussi ", "already checked", "i checked", "ya revis", "j'ai vérif")):
            case.observations.append({"text": text, "ts": _now()})
        if case.pending_question and text.strip():
            case.answers.append({"question": case.pending_question, "answer": text, "ts": _now()})
        if case.initial_report is None:
            case.initial_report = text
        case.conversation.append({"role": "user", "text": text, "ts": _now()})
        previous_status = case.status
        prior_classes = list(case.classes or [])
        classes = classify_text(text)
        looks_unknown_code = bool(re.match(r"^[A-Za-z]{2,}\d{1,4}$", (text or "").strip()))
        if prior_classes and (text or "").strip() and not looks_unknown_code:
            classes = list(dict.fromkeys(prior_classes + classes))
        case.classes = classes
        matches = self.lex.match(text)
        unknown_equip = (tokens(text) | tokens(case.initial_report or "")) & {"laser", "crusher", "grinder", "glass"}
        if unknown_equip:
            matches = [m for m in matches if tokens(m.get("name") or "") & unknown_equip]
        kind = documentary.get("response_kind")
        evidence_items = extra.get("evidence") or []
        analysis_notes = []
        if evidence_items:
            accepted = self.ingest_evidence(evidence_items)
            analysis_notes.append("EVIDENCE_REQUIRES_ANALYSIS")
            analysis_notes.append(t(lang, "no_binary"))
            for a in accepted:
                a["note"] = t(lang, "no_binary")

        # Never mark RESOLVED
        stripped = (text or "").strip()
        looks_unknown_code = bool(re.match(r"^[A-Za-z]{2,}\d{1,4}$", stripped))
        if not stripped:
            kind = "NO_MATCH"
            case.status = "UNRESOLVED"
            case.resolution_status = "UNRESOLVED"
            questions = []
        elif kind == "SAFETY_BLOCK":
            case.status = "SAFETY_BLOCK"
            case.resolution_status = "SAFETY_BLOCK"
            questions = []
        elif kind == "DOCUMENTARY":
            case.status = "DOCUMENTED_SOLUTION"
            case.resolution_status = "DOCUMENTED_SOLUTION"
            questions = self._pick_questions(text, classes, n=3, lang=lang)
        else:
            is_short_answer = (
                bool(case.pending_question)
                and not looks_unknown_code
                and 0 < len(stripped.split()) <= 12
                and not re.search(r"unknown|xyzzy|mister", stripped, re.I)
                and (
                    bool(re.match(
                        r"^(yes|no|si|sí|only|cuando|when|while|it\b|continuous|intermittent|idle|near|closer)",
                        stripped, re.I,
                    ))
                    or len(stripped.split()) <= 8
                )
            )
            if matches:
                kind = "DIAGNOSTIC"
                case.status = "POSSIBLE_CAUSE"
                case.resolution_status = "POSSIBLE_CAUSE"
                questions = self._pick_questions(text, classes, n=3, lang=lang)
            elif classes != ["unknown"]:
                kind = "INFORMATION_REQUIRED"
                case.status = "INFORMATION_REQUIRED"
                case.resolution_status = "INFORMATION_REQUIRED"
                questions = self._pick_questions(text, classes, n=3, lang=lang)
            elif is_short_answer:
                kind = "INFORMATION_REQUIRED"
                case.status = "INFORMATION_REQUIRED"
                case.resolution_status = previous_status or "INFORMATION_REQUIRED"
                questions = self._pick_questions(text, case.classes or classes, n=3, lang=lang)
            else:
                kind = "NO_MATCH"
                case.status = "UNRESOLVED"
                case.resolution_status = "UNRESOLVED"
                questions = [
                    t(lang, "q_subsystem"),
                    t(lang, "q_stopped"),
                    t(lang, "q_sudden"),
                    t(lang, "q_noise"),
                    t(lang, "q_alarm"),
                ]

        for q in questions:
            if q not in case.questions_asked:
                case.questions_asked.append(q)
        case.pending_question = questions[0] if questions else None
        if kind in {"DIAGNOSTIC", "DOCUMENTARY"}:
            case.hypotheses = self._hypotheses(matches, lang=lang)
            case.confidence = "POSSIBLE" if matches else "INSUFFICIENT_EVIDENCE"
        elif kind == "SAFETY_BLOCK":
            case.hypotheses = [{
                "component": None, "hypothesis": "SAFETY_BLOCKED", "status": "SAFETY_BLOCKED",
                "level": "SAFETY_BLOCKED", "evidence": [], "required_checks": [], "note": t(lang, "safe_claim"),
            }]
            case.confidence = "SAFETY_BLOCKED"
        else:
            case.hypotheses = self._hypotheses([], lang=lang)
            case.confidence = "INSUFFICIENT_EVIDENCE"
        if kind in {"DIAGNOSTIC", "DOCUMENTARY"} and not case.checklist:
            case.checklist = self._checklist(matches if matches else [], lang=lang)

        docs = documentary.get("documents") or []
        refs = self.document_references(docs)
        case.documents = refs
        case.pages = [r["page"] for r in refs if r.get("page") is not None]

        human = documentary.get("human_readable") or ""
        if kind == "SAFETY_BLOCK":
            wire = bool(re.search(r"wire|cable|borne|terminal|desconect|disconnect", text, re.I))
            human = t(lang, "safe_wire" if wire else "safe_claim")
        elif kind == "DIAGNOSTIC":
            names = "; ".join(m["name"] for m in matches[:3])
            human = t(lang, "related", names=names)
            if questions:
                human += questions[0]
            if analysis_notes:
                human += " " + t(lang, "no_binary")
        elif kind == "INFORMATION_REQUIRED":
            human = t(lang, "insufficient")
            if tokens(text) & {"laser", "crusher", "grinder", "glass"}:
                human += t(lang, "not_in_kb")
            if questions:
                human += " " + " ".join(questions[:3])
            else:
                human += t(lang, "ask_detail")
        elif kind == "DOCUMENTARY":
            names = "; ".join(sorted({d.get("entity") or d.get("document") for d in (documentary.get("documents") or []) if d.get("entity") or d.get("document")})[:4])
            pages = ", ".join(f"p.{p}" for p in case.pages[:8])
            human = t(lang, "doc_found", name=names or "documented item")
            if pages:
                human += " " + t(lang, "doc_pages", pages=pages)
            human += " " + t(lang, "doc_action")
            if questions:
                human += " " + " ".join(questions[:3])
        elif kind == "NO_MATCH":
            human = need_more_block(lang)

        if extra.get("audio_hint"):
            human += t(lang, "audio_hint")

        out = dict(documentary)
        out["response_kind"] = kind
        out["human_readable"] = human
        out["case_id"] = case.id
        out["message"] = human
        out["questions"] = questions
        out["hypotheses"] = case.hypotheses
        out["checklist"] = case.checklist
        out["document_references"] = refs
        out["pages"] = case.pages
        out["external_sources"] = []
        out["resolution_status"] = case.resolution_status
        out["safety"] = {
            "continuity_confirmed": False,
            "diagnosis_confirmed": False,
            "electrical_connection_confirmed": False,
            "intervention_authorized": False,
        }
        out["evidence_analysis"] = analysis_notes
        out["language"] = lang
        out["observations"] = case.observations
        out["evidence"] = case.evidence
        out["external_references"] = case.external_sources
        out["status"] = case.status
        out["resolved"] = case.final_resolution == "USER_DECLARED"
        if not case.external_sources:
            out["external_research"] = "EXTERNAL_RESEARCH_PENDING"
        return out
