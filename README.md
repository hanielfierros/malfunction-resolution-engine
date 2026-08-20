# Malfunction Resolution Engine

Document-grounded API for the Malfunction Resolution Platform.

**Department of Applied Aeronautical Engineering** · Omni Recycling

This repository is the official backend that the PWA calls over HTTPS. The PWA must not read Knowledge Base JSON files directly.

## 1. What it is

A documentary **and conversational** consultation engine for the Machinex Linear Baler PL3 / PL3Z / B-130 (project 6080241001). It looks up alarms, tags, symptoms, and free text against a validated consultation layer and returns documented pages, evidence types, review routes, follow-up questions, and conservative hypotheses.

It is **not** a confirming diagnostician. It does not confirm a failed part, electrical continuity, or authorization to work. UI strings can be requested in English, Spanish, or French (`language` on `/query`); official document names and tags are not translated. PDF `pdf_url` remains unset until HTTPS hosting exists.

## 2. Purpose

Give maintenance personnel a conservative, source-backed orientation:

- which official document to open
- which page is cited
- what kind of evidence that citation is
- what the documentation does **not** confirm

## 3. Architecture

```
PWA (GitHub Pages)
  ↓  HTTPS  POST /query
malfunction-resolution-engine
  ↓
MASTER consultation indexes
  ↓
validated documentation references
```

Runtime chain (unchanged from the validated engine):

`BackendService` → `Conversation` → `ResponseController` → `EvidenceComposer` → `QueryEngine` → MASTER JSON

## 4. What it consults

The packaged `MASTER_*` JSON files (Master Consultation Layer run `20260818_214934`), including alarms, tags, electrical *page* references, evidence, conflicts, and the query index.

It does **not** open original PDFs, run OCR, or call an external LLM.

## 5. Run locally

Requires **Python 3.10+** (developed on 3.14; hosting image `3.12`).

```
python main.py
```

Default: `http://127.0.0.1:8765/`

First start loads the Knowledge Base (about 20–40 seconds). Keep the process running.

## 6. Environment variables

| Variable | Default | Meaning |
|---|---|---|
| `HOST` | `127.0.0.1` | Bind address. Use `0.0.0.0` on a host. |
| `PORT` | `8765` | Listen port. Hosting platforms inject `PORT`. |
| `ENVIRONMENT` | `development` | `development` or `production` |
| `ALLOWED_ORIGINS` | localhost PWA ports + `https://hanielfierros.github.io` | Comma-separated CORS origins. **Do not use `*` in production.** |
| `KB_DIR` | repository root | Optional override for JSON location |

Copy `.env.example`. Never commit `.env`. There are no API keys in this project.

## 7. `GET /health`

Returns HTTP 200 and JSON:

```json
{ "status": "ok", "data": { "ok": true, "service": "diagnostic-documentation-assistant" } }
```

Flags `continuity_confirmed`, `diagnosis_confirmed`, and `electrical_connection_confirmed` are always `false`.

## 8. Query endpoint

`POST /query`

```json
{ "query": "LZ1 Reading Error" }
```

Also: `POST /reset`, `GET /status`, `GET /entity/{id}`, `GET /alarm/{id}`, `GET /document/{id}`, `GET /page/{id}`.

Document paths in `GET /document` are redacted.

## 9. Connect the PWA

1. Deploy this API on HTTPS (Render is prepared via `render.yaml` / `Procfile`).
2. Set `ALLOWED_ORIGINS` to the GitHub Pages origin (`https://hanielfierros.github.io` is already in the default list).
3. In the PWA Settings (or `config.js` `backendUrl`) put the HTTPS origin of this API. No keys.

## 10. Safety

The engine **may**: classify a query, return documented pages, order review routes, keep conversation context, surface conflicts, mark information as unconfirmed, and block unsafe phrasing.

The engine **must not**: invent cables, terminals, I/O, pages, tags, or procedures; treat `TEXT_LABEL` / `PAGE_REFERENCE` / `HINT` as continuity; assert a failed component because it appears in an alarm; recommend replacement, bypass, jumper, or disconnection; replace LOTO or a qualified person.

## 11. Limitations

- Documentary match ≠ physical condition.
- Confidence is documentary strength, not failure probability.
- User observations stay user observations.
- External AI, if added later, must be labeled as external and must not rewrite these rules.

## 12. Documentary diagnosis rules

`continuity_confirmed = false`  
`diagnosis_confirmed = false`  
`electrical_connection_confirmed = false`  

unless a future, separately validated layer proves otherwise. This release never sets them true.

## 13. Deploy

Render (closest fit for this stdlib HTTP server):

1. Create a Web Service from this repository.
2. Build: `pip install -r requirements.txt`
3. Start: `python main.py`
4. Set `HOST=0.0.0.0`, `ENVIRONMENT=production`, `ALLOWED_ORIGINS=<PWA origin>`.

`PORT` is provided by the host.

## 14. Repository layout

Production files live at the repository root: `main.py`, `config.py`, engine modules `32_`–`36_`, `MASTER_*.json`, `README.md`, `requirements.txt`, `render.yaml`, `Procfile`.

## 15. License

See `LICENSE_PLACEHOLDER.txt`. Choose a license before making the repository public.

---

Department of Applied Aeronautical Engineering  
Omni Recycling
