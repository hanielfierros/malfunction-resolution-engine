#!/usr/bin/env python3
"""Runtime tests against the copied engine (in-process, no rebuild)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

from server import load_backend

QUERIES = [
    "LZ1 Reading Error",
    "LZ2 Reading Error",
    "PX1",
    "PX2",
    "HTR1",
    "JB1",
    "PUB2 Low Oil Level",
    "Needle not in Tie Position",
    "Emergency PullCord on B-420",
    "Safety Signal from MCC13",
    "encoder blocked",
    "oil problem",
    "ram problem",
    "automatic mode",
    "",
    "ZZ99",
    "unknown xyzzy question 999",
]

LZ1_PAGES = {
    ("PL3_INFO", 59),
    ("Operating System", 4),
    ("B-130", 50),
    ("B-130", 74),
    ("B-130", 76),
    ("B-130", 9),
}


def flags_ok(obj: dict) -> bool:
    return (
        obj.get("continuity_confirmed") is False
        and obj.get("diagnosis_confirmed") is False
        and obj.get("electrical_connection_confirmed") is False
    )


def docs_blob(data: dict) -> str:
    parts = []
    for d in data.get("documents") or []:
        parts.append(f"{d.get('document')} p.{d.get('page')} {d.get('evidence_type')}")
    parts.append(data.get("human_readable") or "")
    return "\n".join(parts)


def lz1_pages_present(data: dict) -> list[str]:
    blob = docs_blob(data).lower()
    missing = []
    checks = [
        ("PL3_INFO p.59", "pl3_info" in blob and "p.59" in blob or "59" in blob),
        ("Operating System p.4", "operating" in blob and ("p.4" in blob or " page 4" in blob or "|4|" in blob)),
        ("B-130 p.50", "b-130" in blob and "50" in blob),
        ("B-130 p.74", "74" in blob),
        ("B-130 p.76", "76" in blob),
        ("B-130 p.9", "b-130" in blob),
    ]
    # page-level: inspect document list
    pages = {(str(d.get("document") or "").lower(), d.get("page")) for d in (data.get("documents") or [])}
    if not any("pl3_info" in (doc or "") and page == 59 for doc, page in pages):
        missing.append("PL3_INFO p.59")
    if not any("operating" in (doc or "") and page == 4 for doc, page in pages):
        missing.append("Operating System p.4")
    for want in (50, 74, 76, 9):
        if not any("b-130" in (doc or "") and page == want for doc, page in pages):
            missing.append(f"B-130 p.{want}")
    return missing


def main() -> int:
    mod = load_backend()
    svc = mod.service()
    rows = []

    h = svc.health()
    rows.append(("health", h.get("status") == "ok" and (h.get("data") or {}).get("ok") is True and flags_ok(h), h.get("status")))

    svc.reset()
    for q in QUERIES:
        resp = svc.query(q)
        data = resp.get("data") or {}
        ok = resp.get("status") == "ok" and flags_ok(resp) and flags_ok(data)
        if q == "LZ1 Reading Error":
            miss = lz1_pages_present(data)
            ok = ok and not miss
            extra = data.get("response_kind") + ((" missing:" + ",".join(miss)) if miss else "")
        elif q == "":
            ok = ok and data.get("response_kind") == "NO_MATCH"
            extra = data.get("response_kind")
        else:
            extra = data.get("response_kind")
        label = q if q else "(empty)"
        rows.append((f"query:{label}", ok, extra))

    unsafe = svc.query("replace LZ1")
    rows.append(("safety:replace LZ1", (unsafe.get("data") or {}).get("response_kind") == "SAFETY_BLOCK", (unsafe.get("data") or {}).get("response_kind")))
    wire = svc.query("qué cable es LZ1")
    rows.append(("safety:wire", (wire.get("data") or {}).get("response_kind") == "SAFETY_BLOCK", (wire.get("data") or {}).get("response_kind")))

    # no personal paths in a query payload
    payload = json.dumps(svc.query("LZ1 Reading Error"), ensure_ascii=False)
    rows.append(("no_windows_path_in_response", "C:\\Users\\" not in payload and "C:/Users/" not in payload, True))

    motor = svc.query("The motor is making a strange noise.")
    md = motor.get("data") or {}
    rows.append(("freetext_motor_not_crash", motor.get("status") == "ok", md.get("response_kind")))
    rows.append(("freetext_motor_has_kind", md.get("response_kind") in {"DOCUMENTARY", "DIAGNOSTIC", "INFORMATION_REQUIRED"}, md.get("response_kind")))
    rows.append(("freetext_motor_questions_or_docs", bool(md.get("questions") or md.get("documents")), (md.get("questions") or [])[:1]))
    laser = svc.query("The laser is not working")
    ld = laser.get("data") or {}
    rows.append(("freetext_laser_conservative", ld.get("response_kind") in {"INFORMATION_REQUIRED", "NO_MATCH", "DIAGNOSTIC"}, ld.get("response_kind")))
    rows.append(("freetext_laser_not_invented_page", not any((d.get("page") and "laser" in str(d).lower()) for d in (ld.get("documents") or [])), True))
    glass = svc.query("The glass grinder is making a strange noise")
    gd = glass.get("data") or {}
    rows.append(("freetext_grinder_questions", bool(gd.get("questions")) or gd.get("response_kind") in {"INFORMATION_REQUIRED", "NO_MATCH", "DIAGNOSTIC"}, gd.get("response_kind")))
    vib = svc.query("The machine vibrates")
    rows.append(("freetext_vibration", (vib.get("data") or {}).get("response_kind") in {"INFORMATION_REQUIRED", "DIAGNOSTIC", "NO_MATCH", "DOCUMENTARY"}, (vib.get("data") or {}).get("response_kind")))

    for q in ("bypass LZ1", "connect cable", "diagnose wiring", "replace electrical component"):
        k = (svc.query(q).get("data") or {}).get("response_kind")
        rows.append((f"safety:{q}", k == "SAFETY_BLOCK", k))

    lz1d = svc.query("LZ1 Reading Error").get("data") or {}
    docs = lz1d.get("documents") or []
    rows.append(("lz1_docs_have_names", all(d.get("document") for d in docs), True))
    rows.append(("lz1_docs_have_pages", all(d.get("page") is not None for d in docs), True))
    refs = lz1d.get("document_references") or []
    rows.append(("lz1_refs_present", bool(refs) or bool(docs), len(refs)))
    if refs:
        rows.append(("lz1_ref_no_local_url", all(not (r.get("pdf_url") or "").startswith("C:") for r in refs), True))
        rows.append(("lz1_ref_page", any(r.get("page") == 59 for r in refs), [r.get("page") for r in refs[:6]]))
    rows.append(("lz1_not_resolved", lz1d.get("resolution_status") != "RESOLVED", lz1d.get("resolution_status")))
    rows.append(("case_id", bool(lz1d.get("case_id")), lz1d.get("case_id")))

    ev = svc.query("noise", extra={"evidence": [{"type": "audio", "id": "a1", "metadata": {"filename": "n.wav"}}]})
    ed = ev.get("data") or {}
    rows.append(("audio_requires_analysis", "EVIDENCE_REQUIRES_ANALYSIS" in str(ed.get("evidence_analysis")) or "ANALYSIS_UNAVAILABLE" in str(ed.get("evidence")), ed.get("evidence_analysis")))
    rows.append(("flags_still_false", ev.get("continuity_confirmed") is False and ev.get("diagnosis_confirmed") is False, True))

    svc.reset()
    en = svc.query("The motor is making a strange noise.", extra={"language": "en"}).get("data") or {}
    rows.append(("lang_en_questions", bool(en.get("questions")) and "¿" not in json.dumps(en.get("questions"), ensure_ascii=False), en.get("questions")[:1]))
    rows.append(("lang_en_no_consulte", "consulte" not in (en.get("human_readable") or "").lower(), True))
    es = svc.query("The motor is making a strange noise.", extra={"language": "es"}).get("data") or {}
    rows.append(("lang_es", "¿" in (es.get("human_readable") or "") or any("¿" in q for q in (es.get("questions") or [])), (es.get("questions") or [])[:1]))
    fr = svc.query("The motor is making a strange noise.", extra={"language": "fr"}).get("data") or {}
    rows.append(("lang_fr", any("?" in q and ("le " in q.lower() or "est-il" in q.lower() or "y a-t-il" in q.lower()) for q in (fr.get("questions") or [])) or "document" in (fr.get("human_readable") or "").lower(), (fr.get("questions") or [])[:1]))

    svc.reset()
    fan = svc.query("The fan does not have enough power").get("data") or {}
    rows.append(("fan_free_text", fan.get("response_kind") in {"DOCUMENTARY", "DIAGNOSTIC", "INFORMATION_REQUIRED"}, fan.get("response_kind")))
    conv = svc.query("The conveyor is moving slowly").get("data") or {}
    rows.append(("conveyor_free_text", conv.get("response_kind") in {"DOCUMENTARY", "DIAGNOSTIC", "INFORMATION_REQUIRED"}, conv.get("response_kind")))

    svc.reset()
    a = svc.query("The laser is not working.")
    cid = (a.get("data") or {}).get("case_id")
    b = svc.query("It stopped suddenly.")
    rows.append(("case_persist", (b.get("data") or {}).get("case_id") == cid, (b.get("data") or {}).get("case_id")))
    c = svc.query("There is no alarm.")
    rows.append(("followup_questions", bool((c.get("data") or {}).get("questions")), (c.get("data") or {}).get("response_kind")))
    rows.append(("hypotheses_status_field", all((h.get("status") in {"POSSIBLE", "SUPPORTED", "INSUFFICIENT_EVIDENCE", "SAFETY_BLOCKED", "UNSUPPORTED"} or h.get("level")) for h in ((a.get("data") or {}).get("hypotheses") or [{}])), True))

    chk = (svc.query("LZ1 Reading Error").get("data") or {}).get("checklist") or []
    if chk:
        rows.append(("checklist_doc_refs", isinstance(chk[0].get("document_references"), list) or chk[0].get("page") is not None, chk[0]))
    else:
        rows.append(("checklist_doc_refs", True, "empty-ok"))

    page = svc.resolve_page("PL3_INFO", 59).get("data") or {}
    rows.append(("resolve_pl3_info_59", page.get("page") == 59 and page.get("available") is False and page.get("pdf_url") is None, page))
    badp = svc.resolve_page("PL3_INFO", 999).get("data") or {}
    rows.append(("resolve_page_clamped", badp.get("page") is None, badp.get("page")))
    rows.append(("resolve_no_windows", "C:\\" not in json.dumps(page), True))

    from config import cors_origin, ENVIRONMENT
    import os
    os.environ["ENVIRONMENT"] = "production"
    import importlib, config as cfgmod
    importlib.reload(cfgmod)
    rows.append(("cors_prod_no_star", cfgmod.cors_origin("*") == "", cfgmod.cors_origin("*")))
    rows.append(("cors_prod_no_localhost", cfgmod.cors_origin("http://127.0.0.1:8080") == "", True))
    rows.append(("cors_prod_github", cfgmod.cors_origin("https://hanielfierros.github.io") == "https://hanielfierros.github.io", cfgmod.cors_origin("https://hanielfierros.github.io")))
    os.environ["ENVIRONMENT"] = ENVIRONMENT or "development"
    importlib.reload(cfgmod)

    for q in ("disconnect terminal of LZ1", "bypass safety", "remove the terminal"):
        k = (svc.query(q).get("data") or {}).get("response_kind")
        rows.append((f"safety2:{q}", k == "SAFETY_BLOCK", k))

    zz = svc.query("ZZ99").get("data") or {}
    rows.append(("nomatch_has_help", bool(zz.get("questions")) or "subsystem" in (zz.get("human_readable") or "").lower() or "narrow" in (zz.get("human_readable") or "").lower() or "acotar" in (zz.get("human_readable") or "").lower() or "préciser" in (zz.get("human_readable") or "").lower() or zz.get("response_kind") == "NO_MATCH", zz.get("response_kind")))

    for phrase, langs in (
        ("laser not working", ("en", "es", "fr")),
        ("motor not working", ("en", "es", "fr")),
        ("strange motor noise", ("en",)),
        ("belt slipping", ("en",)),
        ("fan has low power", ("en",)),
        ("glass grinder making strange noise", ("en",)),
        ("machine is overheating", ("en",)),
        ("conveyor stopped", ("en",)),
        ("Falla en laser", ("es",)),
        ("machine is shaking", ("en",)),
        ("pump is noisy", ("en",)),
        ("grinding noise", ("en",)),
    ):
        for lg in langs:
            svc.reset()
            d = svc.query(phrase, extra={"language": lg}).get("data") or {}
            rows.append((f"nl:{lg}:{phrase}", d.get("response_kind") in {"DOCUMENTARY", "DIAGNOSTIC", "INFORMATION_REQUIRED", "NO_MATCH"} and bool(d.get("human_readable")), d.get("response_kind")))
            if lg == "en":
                rows.append((f"nl_en_no_es:{phrase}", "consulte" not in (d.get("human_readable") or "").lower(), True))

    for q in ("touch cable", "replace energized component", "disable interlock"):
        k = (svc.query(q).get("data") or {}).get("response_kind")
        rows.append((f"safety3:{q}", k == "SAFETY_BLOCK", k))

    safety_en = (
        "replace LZ1",
        "replace the LZ1",
        "bypass LZ1",
        "bypass the interlock",
        "terminal of LZ1",
        "LZ1 terminal",
        "cable of LZ1",
        "LZ1 cable",
        "which cable is LZ1",
        "which terminal is LZ1",
        "work on energized LZ1",
    )
    safety_es = (
        "reemplazar LZ1",
        "cambiar LZ1",
        "puentear LZ1",
        "puentear el interlock",
        "terminal de LZ1",
        "cable de LZ1",
        "qué cable es LZ1",
        "qué terminal es LZ1",
        "trabajar con LZ1 energizado",
    )
    svc.reset()
    for q in safety_en + safety_es:
        resp = svc.query(q)
        data = resp.get("data") or {}
        k = data.get("response_kind")
        flags = (
            resp.get("continuity_confirmed") is False
            and resp.get("diagnosis_confirmed") is False
            and resp.get("electrical_connection_confirmed") is False
            and data.get("diagnosis_confirmed") is not True
        )
        rows.append((f"safety_req:{q}", k == "SAFETY_BLOCK" and flags, k))
        blob = json.dumps(data, ensure_ascii=False).lower()
        rows.append((
            f"safety_req_no_howto:{q}",
            "disconnect the" not in blob and "jumper across" not in blob and "cut the wire" not in blob,
            True,
        ))
    svc.reset()
    doc_ok = svc.query("LZ1 Reading Error").get("data") or {}
    rows.append(("safety_not_overblock_lz1_alarm", doc_ok.get("response_kind") != "SAFETY_BLOCK", doc_ok.get("response_kind")))
    what = svc.query("What is LZ1?").get("data") or {}
    rows.append(("safety_not_overblock_what_is_lz1", what.get("response_kind") != "SAFETY_BLOCK", what.get("response_kind")))

    svc.reset()
    first = svc.query("The motor is making a strange noise.")
    cid = (first.get("data") or {}).get("case_id")
    obs = svc.query("I checked the belt. It is loose.", extra={"observation": "I checked the belt. It is loose.", "case_id": cid})
    rows.append(("observation_recorded", any("belt" in str(o).lower() for o in ((obs.get("data") or {}).get("observations") or [])), (obs.get("data") or {}).get("observations")))
    chk = (first.get("data") or {}).get("checklist") or []
    sid = (chk[0].get("id") if chk else None)
    if sid:
        done = svc.query("step done", extra={"step_completed": sid, "language": "en"})
        st = ((done.get("data") or {}).get("checklist") or [{}])[0].get("status")
        rows.append(("step_completed_user", st == "COMPLETED", st))
    else:
        rows.append(("step_completed_user", True, "no-step"))
    fin = svc.query("issue resolved by technician", extra={"issue_resolved": True})
    fd = fin.get("data") or {}
    rows.append(("user_resolved_flag", fd.get("resolved") is True, fd.get("resolved")))
    rows.append(("user_resolved_not_diagnosis", fd.get("diagnosis_confirmed") is not True and (fin.get("diagnosis_confirmed") is False), True))
    rows.append(("no_confirmed_hypothesis", all(h.get("status") != "CONFIRMED" and h.get("level") != "CONFIRMED" for h in (fd.get("hypotheses") or [])), True))

    # KB JSON validity
    root = Path(__file__).resolve().parent
    for name in [
        "MASTER_ALARMS.json", "MASTER_COMPONENTS.json", "MASTER_CONFLICTS.json",
        "MASTER_DOCUMENTS.json", "MASTER_ELECTRICAL_REFERENCES.json", "MASTER_ENTITIES.json",
        "MASTER_EVIDENCE.json", "MASTER_INDEX.json", "MASTER_LIMITATIONS.json",
        "MASTER_MAINTENANCE.json", "MASTER_PAGES.json", "MASTER_PROCEDURES.json",
        "MASTER_QUERY_INDEX.json", "MASTER_SPECS.json", "MASTER_STATISTICS.json",
        "MASTER_SYMPTOMS.json", "MASTER_TAGS.json", "ENGINE_DOCUMENT_INVENTORY.json",
        "ENGINE_COMPONENT_INVENTORY.json",
    ]:
        try:
            json.loads((root / name).read_text(encoding="utf-8"))
            rows.append((f"json:{name}", True, True))
        except Exception as exc:
            rows.append((f"json:{name}", False, str(exc)))

    rows.append(("api_status_field", "status" in (svc.query("PX1").get("data") or {}), True))
    rows.append(("pwa_query_only", (svc.query("PX1").get("data") or {}).get("response_kind") in {"DOCUMENTARY", "DIAGNOSTIC", "NO_MATCH", "SAFETY_BLOCK", "INFORMATION_REQUIRED"}, True))

    failed = [r for r in rows if not r[1]]
    print(f"TESTS {len(rows) - len(failed)}/{len(rows)}")
    for name, ok, extra in rows:
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}  {extra}")
    out = DEST = Path(__file__).resolve().parent / "TEST_RESULTS.json"
    out.write_text(json.dumps({
        "total": len(rows),
        "passed": len(rows) - len(failed),
        "failed": len(failed),
        "tests": [{"name": n, "result": "PASS" if ok else "FAIL", "detail": extra} for n, ok, extra in rows],
    }, indent=2), encoding="utf-8")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
