"""External technical research layer.

Official documentation always outranks internet sources.
This module does not perform live web search at query time
(PENDING PRODUCTION INFRASTRUCTURE). It only shapes payloads
if an approved external record is supplied by a future service.
"""
from __future__ import annotations


PENDING = "EXTERNAL_RESEARCH_PENDING"


def research_status():
    return {
        "status": PENDING,
        "reference_type": "EXTERNAL_REFERENCE",
        "note": "Live web/API research is not configured. Official documentation is used first. PENDING INFRASTRUCTURE.",
        "results": [],
    }


def normalize_external(records) -> list[dict]:
    out = []
    for r in records or []:
        if not isinstance(r, dict):
            continue
        url = r.get("url") or r.get("URL")
        if not isinstance(url, str) or not url.startswith("https://"):
            continue
        if "C:\\" in url or url.startswith("file:"):
            continue
        out.append({
            "title": r.get("title") or "External technical reference",
            "url": url,
            "source": r.get("source") or "unknown",
            "retrieved_date": r.get("retrieved_date"),
            "relevance": r.get("relevance"),
            "applicability": r.get("applicability") or "Not confirmed as manufacturer procedure",
            "reference_type": "EXTERNAL_REFERENCE",
        })
    return out
