"""Resolve document_id + page for the PWA viewer. Never invent URLs or pages."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def _load_inv():
    p = ROOT / "ENGINE_DOCUMENT_INVENTORY.json"
    if not p.exists():
        return {"documents": []}
    return json.loads(p.read_text(encoding="utf-8"))


class DocumentResolver:
    def __init__(self):
        inv = _load_inv()
        self.documents = inv.get("documents") or []
        self.by_id = {}
        self.by_name = {}
        for d in self.documents:
            did = d.get("document_id")
            short = (d.get("short_name") or "").lower()
            name = (d.get("document_name") or "").lower()
            if did:
                self.by_id[str(did)] = d
                self.by_id[str(did).upper()] = d
            if short:
                self.by_id[short] = d
                self.by_name[short] = d
            if name:
                self.by_name[name] = d
            if "pl3_info" in name:
                self.by_id["pl3_info"] = d
                self.by_name["pl3_info"] = d
            if "operating" in name:
                self.by_id["operating system"] = d
            if "electrical" in name or "b-130" in name:
                self.by_id["b-130"] = d
                self.by_name["b-130"] = d

    def lookup(self, document_id=None, document_name=None):
        if document_id:
            hit = self.by_id.get(str(document_id)) or self.by_id.get(str(document_id).lower())
            if hit:
                return hit
        if document_name:
            key = str(document_name).lower().strip()
            if key in self.by_name:
                return self.by_name[key]
            for k, v in self.by_name.items():
                if key and (key in k or k in key):
                    return v
        return None

    def valid_page(self, meta, page):
        try:
            n = int(page)
        except (TypeError, ValueError):
            return None
        if n < 1:
            return None
        count = (meta or {}).get("page_count")
        if isinstance(count, int) and count > 0 and n > count:
            return None
        return n

    def resolve(self, document_id=None, document_name=None, page=None) -> dict:
        meta = self.lookup(document_id, document_name)
        page_n = self.valid_page(meta, page) if meta is not None else None
        if page is not None and page_n is None and meta is None:
            page_n = None
        elif page is not None and meta is not None and page_n is None:
            # out of range or invalid — do not invent
            page_n = None
        url = (meta or {}).get("pdf_url")
        if not isinstance(url, str) or not url.startswith("https://"):
            url = None
        if url and ("C:" in url or "\\" in url or url.startswith("file:")):
            url = None
        if page is not None and page_n is None:
            url = None
        available = bool(url) and page_n is not None and meta is not None
        viewer = None
        if available:
            viewer = f"{url}#page={page_n}"
        return {
            "document_id": (meta or {}).get("document_id") or document_id,
            "document_name": (meta or {}).get("document_name") or document_name,
            "short_name": (meta or {}).get("short_name"),
            "page": page_n,
            "page_label": f"p.{page_n}" if page_n else None,
            "section": None,
            "pdf_url": url,
            "viewer_target": viewer,
            "available": available,
            "status": (meta or {}).get("hosting_status") or "PENDING_DOCUMENT_HOSTING",
            "hosting_status": (meta or {}).get("hosting_status") or "PENDING_DOCUMENT_HOSTING",
            "reference_type": (meta or {}).get("reference_type") or "official_documentation",
            "page_count": (meta or {}).get("page_count"),
            "official_name": (meta or {}).get("document_name") or document_name,
            "source": "official_documentation",
            "relevance": "DOCUMENTARY_EVIDENCE",
            "availability": available,
            "section": None,
        }
