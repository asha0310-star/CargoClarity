# Phase 4 — Backend Workflow: Setup and Review Guide

## What this phase does

Phase 4 wraps the existing CargoClarity deterministic engine and optional Ollama/Gemini adapter in a small FastAPI backend. The API supports the nine workflow actions required by the hackathon guide: list emails, retrieve one email, ingest records, start processing, inspect job status, return comparisons, preview attachment evidence, submit a review, retry processing, and export evaluation JSON.

The local implementation uses a file-backed JSON runtime store under `.runtime/api_state.json`. This keeps the prototype durable across local server restarts without introducing a database migration before the dashboard phase. The processing worker uses FastAPI background tasks. This is sufficient for the hackathon prototype; a production deployment would move the work to a dedicated queue and relational database.

The backend does not duplicate classification, extraction, normalization, comparison, or AI logic. It calls the Phase 2/3 pipeline and stores the resulting report. The deterministic comparison engine remains the final decision authority.

## What changed

| File | Purpose |
|---|---|
| `src/cargoclarity/api.py` | FastAPI application and versioned routes |
| `src/cargoclarity/api_schemas.py` | Explicit request models and validation rules |
| `src/cargoclarity/api_store.py` | Local durable store, jobs, reviews, audit events, summaries, and exports |
| `tests/test_phase4_api.py` | End-to-end API workflow and security tests |
| `pyproject.toml` | FastAPI, Uvicorn, HTTPX, and API command dependencies |
| `.gitignore` | Ignores `.runtime` local state |

## API routes implemented

| Method | Route | Purpose |
|---|---|---|
| `GET` | `/api/v1/health` | Check service and dependency status |
| `GET` | `/api/v1/emails` | List and filter inbox records |
| `GET` | `/api/v1/emails/{email_id}` | Get one email and attachment metadata |
| `POST` | `/api/v1/emails/ingest` | Ingest records and optionally queue processing |
| `POST` | `/api/v1/emails/{email_id}/process` | Start processing |
| `GET` | `/api/v1/jobs/{job_id}` | Inspect processing status and result |
| `GET` | `/api/v1/emails/{email_id}/comparison` | Get the explainable comparison |
| `GET` | `/api/v1/emails/{email_id}/attachments/{attachment_id}/preview` | Get safe text evidence |
| `POST` | `/api/v1/emails/{email_id}/review` | Record a confirm, override, or unresolved decision |
| `POST` | `/api/v1/emails/{email_id}/retry` | Create a new processing attempt |
| `GET` | `/api/v1/reports/summary` | Return category, status, review, and processing counts |
| `GET` | `/api/v1/reports/export?format=json` | Return evaluation-compatible JSON |

## Step 1 — Open the project

Open Terminal and run:

```bash
cd "/Users/abdulhakimshaon/Desktop/Averis/CargoClarity/CargoClarity"
```

Confirm the path:

```bash
pwd
```

It should end with:

```text
/Averis/CargoClarity/CargoClarity
```

## Step 2 — Activate the environment

Run:

```bash
source .venv/bin/activate
```

If the environment does not exist, create it:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

## Step 3 — Install the Phase 4 dependencies

Run:

```bash
python -m pip install --upgrade pip
python -m pip install -e '.[test,ai,api]'
```

The `api` extra installs FastAPI, Uvicorn, and HTTPX. The `ai` extra keeps the configured Ollama or Gemini adapter available. You do not need a cloud API key when the local `.env` uses Ollama.

## Step 4 — Run the full automated test suite

Run:

```bash
pytest
```

Expected result:

```text
29 passed
```

The tests include the 24 Phase 2/3 tests plus five API workflow and safety tests. They use a temporary state file, so they do not change your normal `.runtime/api_state.json`.

If any test fails, stop and provide the complete output before starting the server.

## Step 5 — Run the original deterministic checks

Run:

```bash
cargoclarity fixtures
```

Expected result:

```text
7/7 fixtures passed
```

Then run:

```bash
python tools/run_phase2_smoke.py
```

The final line must be:

```text
failures=[]
```

These checks confirm that adding the API did not change the deterministic engine.

## Step 6 — Start the local API server

Run:

```bash
cargoclarity-api
```

Keep this Terminal window open. The server listens at:

```text
http://127.0.0.1:8000
```

Open a second Terminal window and return to the project:

```bash
cd "/Users/abdulhakimshaon/Desktop/Averis/CargoClarity/CargoClarity"
source .venv/bin/activate
```

The API automatically loads the participant bundle and makes the 520 email records available. It does not process all 520 emails at startup.

To stop the server, return to the first Terminal window and press:

```text
Control + C
```

## Step 7 — Check service health

In the second Terminal window, run:

```bash
curl -s http://127.0.0.1:8000/api/v1/health | jq
```

You should see an object containing:

```json
{
  "status": "ok",
  "version": "0.4.0",
  "dependencies": {
    "data_source": "ok",
    "runtime_store": "ok",
    "ai": "configured"
  }
}
```

With the current local `.env`, `ai` should be `configured` because Ollama is available. If Ollama is stopped, the API should still start and report `ai` as `degraded`; deterministic processing remains available.

## Step 8 — List emails

Run:

```bash
curl -s "http://127.0.0.1:8000/api/v1/emails?page=1&page_size=5" | jq
```

The response contains:

```json
{
  "items": [],
  "page": 1,
  "page_size": 5,
  "total": 520
}
```

The initial records have no category or comparison status because they have not yet been processed through the API.

You can filter the list:

```bash
curl -s "http://127.0.0.1:8000/api/v1/emails?search=BL&page_size=10" | jq
```

After processing records, these filters are also available:

```bash
curl -s "http://127.0.0.1:8000/api/v1/emails?category=BL_COMPARISON" | jq
curl -s "http://127.0.0.1:8000/api/v1/emails?status=NEEDS_REVIEW" | jq
curl -s "http://127.0.0.1:8000/api/v1/emails?needs_review=true" | jq
```

## Step 9 — Retrieve one email

Run:

```bash
curl -s http://127.0.0.1:8000/api/v1/emails/email_001 | jq
```

The response includes the sender, subject, body, attachment metadata, latest run, current status, and review. It does not expose a public URL or unrestricted filesystem path for an attachment.

Save the first attachment ID for the evidence step:

```bash
ATTACHMENT_ID=$(curl -s http://127.0.0.1:8000/api/v1/emails/email_001 | jq -r '.attachments[0].id')
echo "$ATTACHMENT_ID"
```

## Step 10 — Start processing one email

Use deterministic processing first:

```bash
PROCESS_RESPONSE=$(curl -s -X POST \
  http://127.0.0.1:8000/api/v1/emails/email_001/process \
  -H 'Content-Type: application/json' \
  -d '{"force": true, "use_ai": false}')

echo "$PROCESS_RESPONSE" | jq
JOB_ID=$(echo "$PROCESS_RESPONSE" | jq -r '.job_id')
echo "$JOB_ID"
```

The API returns `202 Accepted` and a job ID. The local background task normally completes quickly.

To use the configured local Ollama model for ambiguous classification, send:

```bash
PROCESS_RESPONSE=$(curl -s -X POST \
  http://127.0.0.1:8000/api/v1/emails/email_016/process \
  -H 'Content-Type: application/json' \
  -d '{"force": true, "use_ai": true}')
JOB_ID=$(echo "$PROCESS_RESPONSE" | jq -r '.job_id')
echo "$PROCESS_RESPONSE" | jq
```

The AI output remains subject to the Phase 3 confidence gate. A low-confidence local response is recorded but does not replace the deterministic route.

## Step 11 — Check the processing job

Run:

```bash
curl -s "http://127.0.0.1:8000/api/v1/jobs/$JOB_ID" | jq
```

The completed job should contain:

```json
{
  "status": "SUCCEEDED",
  "stage": "complete",
  "progress": 100,
  "result": {}
}
```

If a file is missing, unreadable, or unsafe, the job becomes `FAILED` or the comparison becomes `NEEDS_REVIEW` with an explicit reason. It must not silently report a clean match.

## Step 12 — Get the comparison result

Run:

```bash
curl -s http://127.0.0.1:8000/api/v1/emails/email_001/comparison | jq
```

For a clean comparison, inspect:

```text
status = OK
machine_status = OK
defect_fields = []
fields = seven field results
```

For a mismatch, the response includes the defect fields, both SI and BL values, normalized values, evidence, confidence, comparison method, and explanation.

For an `INVOICE_QUERY`, `SI_REQUEST`, `GENERAL`, or `SPAM` email, the comparison is `null` because only `BL_COMPARISON` emails enter the comparison workflow.

## Step 13 — Preview attachment evidence safely

Use the attachment ID from Step 9:

```bash
curl -s \
  "http://127.0.0.1:8000/api/v1/emails/email_001/attachments/$ATTACHMENT_ID/preview" \
  | jq
```

The response contains a bounded text excerpt, parser name, readability status, and a small table sample. The endpoint rejects absolute paths and `..` traversal. It never makes the source file public.

## Step 14 — Record a review decision

After inspecting the comparison and evidence, submit a confirmation:

```bash
curl -s -X POST \
  http://127.0.0.1:8000/api/v1/emails/email_001/review \
  -H 'Content-Type: application/json' \
  -d '{
    "decision": "CONFIRMED",
    "corrected_status": "OK",
    "corrected_fields": [],
    "reason": "Reviewed the source evidence and confirmed the machine result."
  }' | jq
```

The review is appended to the local state. It does not overwrite the original machine run. The email’s final status uses the corrected status while the comparison retains the machine status.

For a genuine correction, use `OVERRIDDEN`, provide corrected fields, and give a specific reason. Use `UNRESOLVED` when the case cannot be safely resolved.

## Step 15 — Retry processing

Run:

```bash
RETRY_RESPONSE=$(curl -s -X POST \
  http://127.0.0.1:8000/api/v1/emails/email_001/retry)
echo "$RETRY_RESPONSE" | jq
RETRY_JOB_ID=$(echo "$RETRY_RESPONSE" | jq -r '.job_id')
curl -s "http://127.0.0.1:8000/api/v1/jobs/$RETRY_JOB_ID" | jq
```

The previous run remains in the local runtime state. The retry creates a new processing attempt and makes the latest successful attempt explicit.

## Step 16 — View the summary report

Run:

```bash
curl -s http://127.0.0.1:8000/api/v1/reports/summary | jq
```

The response reports the number of loaded emails, processed emails, successful and failed jobs, counts by category, counts by status, review reasons, and recorded reviews.

## Step 17 — Export evaluation JSON

Run:

```bash
curl -s \
  "http://127.0.0.1:8000/api/v1/reports/export?format=json" \
  | jq
```

The `items` object is keyed by source email ID. Each processed email contains:

```json
{
  "category": "BL_COMPARISON",
  "status": "OK",
  "review_reason": null,
  "defect_fields": [],
  "has_defect": false
}
```

Only processed emails appear in the export. This prevents unprocessed records from being mistaken for clean results.

## Step 18 — Test useful API errors

Missing email:

```bash
curl -s -i http://127.0.0.1:8000/api/v1/emails/not_present
```

The response is `404` with the standard error shape:

```json
{
  "error": {
    "code": "NOT_FOUND",
    "message": "...",
    "request_id": "req_..."
  }
}
```

Invalid request:

```bash
curl -s -i -X POST \
  http://127.0.0.1:8000/api/v1/emails/ingest \
  -H 'Content-Type: application/json' \
  -d '{"emails": []}'
```

This returns `422 VALIDATION_ERROR`.

Unsupported export format:

```bash
curl -s -i "http://127.0.0.1:8000/api/v1/reports/export?format=csv"
```

This returns `400 UNSUPPORTED_FORMAT` because Phase 4 implements JSON export only.

## Step 19 — Review local runtime state

The API writes local state to:

```text
.runtime/api_state.json
```

This file is ignored by Git. It contains source records, job results, reviews, and audit events for local review. It is not a replacement for the Phase 5 database design.

To reset the local API state, stop the server and run:

```bash
rm -rf .runtime
```

The next server start will preload the participant inbox again with no processed results.

## Step 20 — Review Phase 4 boundaries

Phase 4 intentionally does not include a frontend dashboard, PostgreSQL migrations, user login, workspace authorization, production queue workers, cloud deployment, or public object storage. The API specification requires those controls for deployment, but the hackathon prototype keeps this phase local and testable. Phase 5 will consume these routes from the dashboard.

The local server has no authentication because it is bound to `127.0.0.1`. Do not expose it publicly or bind it to `0.0.0.0` until authentication, authorization, CORS restrictions, rate limits, and production secret handling are implemented.

## Step 21 — Approve Phase 4

Approve Phase 4 only when all of the following are true:

- `pytest` reports 29 passing tests.
- `cargoclarity fixtures` reports 7/7 passing fixtures.
- The full participant smoke test ends with `failures=[]`.
- `GET /api/v1/health` returns `status: ok`.
- The API can ingest and process `email_001`.
- The job endpoint returns `SUCCEEDED`.
- The comparison endpoint returns seven field results.
- The attachment preview returns bounded evidence.
- A review is recorded without overwriting the machine run.
- Retry creates a new successful attempt.
- Summary and JSON export return usable data.
- Invalid input, missing records, unsupported formats, and path traversal return useful errors.
- `.runtime` and `.env` remain ignored by Git.

Then reply:

```text
Phase 4 approved. Move to Phase 5.
```

## References

[1]: ../docs/CargoClarity — API Specification.md "CargoClarity API Specification"
[2]: ../docs/CargoClarity — Functional Requirements.md "CargoClarity Functional Requirements"
[3]: ../docs/CargoClarity — System Architecture.md "CargoClarity System Architecture"
[4]: ../docs/CargoClarity — Database Design.md "CargoClarity Database Design"
[5]: ../docs/PHASE3_GUIDE.md "CargoClarity Phase 3 review and operation guide"
