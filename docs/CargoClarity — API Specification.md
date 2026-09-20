# CargoClarity — API Specification

## 1. API conventions

The backend exposes a versioned REST API under `/api/v1`. Requests and responses use JSON unless a file upload or report download is explicitly indicated. Authentication uses a bearer token in deployed environments. All identifiers are opaque UUIDs except the source `email_id`, which remains available for dataset evaluation.

Errors use the following shape:

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "The attachment cannot be processed.",
    "request_id": "req_123"
  }
}
```

Long-running operations return a processing job and do not block the browser request.

## 2. Core endpoints

### `GET /api/v1/health`

Returns service health and dependency status.

```json
{
  "status": "ok",
  "version": "1.0.0",
  "dependencies": {"database": "ok", "object_storage": "ok", "ai": "degraded"}
}
```

### `GET /api/v1/emails`

Lists inbox records. Supported query parameters are `category`, `status`, `needs_review`, `search`, `page`, and `page_size`.

Response:

```json
{
  "items": [
    {
      "id": "uuid",
      "source_email_id": "email_004",
      "subject": "TO CONFIRM DOCS ...",
      "sender": "docs@example.com",
      "category": "BL_COMPARISON",
      "status": "MISMATCH",
      "needs_review": false,
      "updated_at": "2026-09-20T04:00:00Z"
    }
  ],
  "page": 1,
  "page_size": 25,
  "total": 520
}
```

### `GET /api/v1/emails/{email_id}`

Returns the email, attachments, latest processing run, and summary fields. The response does not expose provider secrets or unrestricted storage paths.

### `POST /api/v1/emails/ingest`

Ingests one or more email records from a trusted source. The server deduplicates by workspace and source email ID.

Request:

```json
{
  "source": "dataset",
  "emails": [
    {
      "source_email_id": "email_004",
      "sender": "docs@example.com",
      "subject": "TO CONFIRM DOCS ...",
      "body": "Please compare the SI and draft BL.",
      "attachments": ["attachments/email_004_SI.txt", "attachments/email_004_BL.txt"]
    }
  ]
}
```

Response: `202 Accepted` with created email IDs and job IDs.

### `POST /api/v1/emails/{email_id}/process`

Starts or restarts processing. The optional body can specify `force`, `parser_version`, or `use_ai`.

Response:

```json
{
  "job_id": "uuid",
  "email_id": "uuid",
  "status": "QUEUED"
}
```

### `GET /api/v1/jobs/{job_id}`

Returns progress, stage, error information, and the resulting processing run when complete.

### `POST /api/v1/batches/process`

Starts a bounded background verification run for every currently unprocessed email. The body accepts `force` and `use_ai`; AI remains opt-in and deterministic fallback remains active. The response contains `batch_id`, `status`, and `total`.

### `GET /api/v1/batches/{batch_id}`

Returns batch status, stage, processed count, failure count, total, percentage, and timestamps. The dashboard uses this endpoint to display progress without blocking the interface.

### `GET /api/v1/emails/{email_id}/comparison`

Returns the full explainable comparison.

```json
{
  "email_id": "email_004",
  "category": "BL_COMPARISON",
  "status": "MISMATCH",
  "review_reason": null,
  "has_defect": true,
  "defect_fields": ["consignee"],
  "fields": [
    {
      "field_name": "consignee",
      "result": "MISMATCH",
      "confidence": 0.97,
      "confidence_band": "HIGH",
      "si": {"raw_value": "...", "normalized_value": "...", "evidence": "..."},
      "bl": {"raw_value": "...", "normalized_value": "...", "evidence": "..."},
      "comparison_method": "normalized_exact",
      "explanation": "The consignee names identify different organizations."
    }
  ],
  "processing": {"parser_version": "1.0.0", "model": "provider/model", "completed_at": "..."}
}
```

### `GET /api/v1/emails/{email_id}/attachments/{attachment_id}/preview`

Returns a safe preview or a short-lived signed download URL. The API must reject path traversal and must not make source files public by default.

### `POST /api/v1/emails/{email_id}/review`

Records a human decision.

Request:

```json
{
  "decision": "OVERRIDDEN",
  "corrected_status": "MISMATCH",
  "corrected_fields": [
    {"field_name": "gross_weight_kg", "result": "MISMATCH", "si_value": 22000, "bl_value": 24000}
  ],
  "reason": "The BL table clearly shows 24,000 kg; extraction was initially uncertain."
}
```

Response returns the updated final status and audit event ID.

### `GET /api/v1/emails/{email_id}/reviews`

Returns the append-only human decision history. Every item includes reviewer, timestamp, decision, machine status, prior effective status, new effective status, corrected fields, and rationale.

### `GET /api/v1/emails/{email_id}/audit`

Returns processing and review events for one email in reverse chronological order.

### `GET /api/v1/audit`

Returns the workspace audit stream for the operations workbench. Review events include actor, prior state, new state, and reason; machine events remain separate.

### `POST /api/v1/emails/{email_id}/retry`

Retries a failed or reviewable processing stage. The prior attempt remains in history.

### `GET /api/v1/reports/summary`

Returns counts by category, status, review reason, and processing health.

### `GET /api/v1/reports/export?format=json`

Returns the evaluation-compatible JSON object keyed by source email ID. Each value contains `category`, `status`, `review_reason`, `defect_fields`, and `has_defect`. CSV may be added for human reporting, but JSON is the required format.

## 3. Classification contract

Valid categories are `BL_COMPARISON`, `SI_REQUEST`, `INVOICE_QUERY`, `GENERAL`, and `SPAM`. Classification responses must include `confidence`, `signals`, and `decided_by`. If classification confidence is below the configured threshold, the UI should show the case as ambiguous while still selecting the best category for routing.

## 4. Comparison contract

Valid field names are `shipper`, `consignee`, `notify_party`, `port_of_loading`, `port_of_discharge`, `container_count`, and `gross_weight_kg`. Valid field results are `MATCH`, `MISMATCH`, and `UNCERTAIN`. A comparison must not claim `MISMATCH` when either required value is unavailable or unreadable.

## 5. Security requirements for the API

The API must authenticate every non-health request, authorize workspace membership, validate uploaded content, rate-limit processing and AI calls, redact secrets from logs, and return a request ID for support. CORS should allow only the deployed frontend origin.

## References

[1]: ./Functional%20Requirements.md "CargoClarity Functional Requirements"
[2]: ./System%20Architecture.md "CargoClarity System Architecture"
[3]: ./Database%20Design.md "CargoClarity Database Design"
[4]: ./UI%20UX%20Specification.md "CargoClarity UI/UX Specification"
[5]: ./Security%20%26%20Privacy.md "CargoClarity Security and Privacy"
