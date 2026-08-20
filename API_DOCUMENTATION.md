# API

Compatible with the existing PWA.

## POST /query

Backward compatible body:

```json
{ "query": "PX1" }
```

Optional additive fields:

```json
{
  "query": "...",
  "language": "en",
  "case_id": "...",
  "observation": "I checked the belt. It is loose.",
  "step_completed": "CHK-001",
  "issue_resolved": false,
  "issue_persists": true,
  "evidence": [
    { "type": "audio", "id": "...", "filename": "...", "mime_type": "audio/wav", "duration": 0 }
  ],
  "conversation": []
}
```

`resolved` in the response is true only when the client sends `issue_resolved: true` (user declaration). It does **not** set `diagnosis_confirmed`.

PDF hosting: `PENDING INFRASTRUCTURE` — `pdf_url` remains null until an HTTPS document URL is configured. No local paths.

`language`: `en` | `es` | `fr`. Default `en`. Official document names and tags are not translated.

Envelope (unchanged wrapper):

```json
{
  "request_id": "...",
  "response_id": "...",
  "status": "ok",
  "continuity_confirmed": false,
  "diagnosis_confirmed": false,
  "electrical_connection_confirmed": false,
  "data": {}
}
```

`data` always includes legacy fields:

- `response_kind`
- `human_readable`
- `documents` (`document`, `page`, `entity`, `evidence_type`)
- `review_order`
- `conflicts`

Additive fields (PWA may ignore them):

- `case_id`
- `message`
- `questions`
- `hypotheses`
- `checklist` (steps may include `document_references: [{document_id, page}]`)
- `document_references` (`document_id`, `document_name`, `page`, `pdf_url`, `status`, `viewer_target`, `available`)
- `observations`
- `evidence`
- `language`
- `external_references`
- `resolution_status`
- `flags`

`pdf_url` is `null` until HTTPS document hosting exists (`PENDING_DOCUMENT_HOSTING`). Local paths are never returned.

`response_kind`: `DOCUMENTARY` | `DIAGNOSTIC` | `INFORMATION_REQUIRED` | `NO_MATCH` | `SAFETY_BLOCK`

Flags remain `false` unless an explicit safe confirmation path exists (none today).

## POST /reset

Clears conversation and case state.

## GET /health

`data.ok = true`

## GET /status

Conversation context plus turn count.

## GET /document/{id}/page/{n}

Resolves a viewer target:

```json
{
  "document_id": "...",
  "document_name": "...",
  "page": 59,
  "pdf_url": null,
  "viewer_target": null,
  "available": false,
  "status": "PENDING_DOCUMENT_HOSTING"
}
```

Pages outside `1..page_count` are not invented (`page: null`).

Also: `GET /entity/{id}`, `GET /alarm/{id}`, `GET /document/{id}`, `GET /page/{id}`.
