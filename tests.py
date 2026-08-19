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
    rows.append(("no_windows_path_in_response", "C:\\Users\\hanie" not in payload and "C:/Users/hanie" not in payload, True))

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
