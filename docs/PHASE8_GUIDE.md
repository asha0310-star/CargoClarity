# Phase 8 — Deployment and Reliability: Step-by-Step Guide

## Outcome

Phase 8 packages CargoClarity as a single web product. FastAPI serves both the API and dashboard, which removes cross-origin configuration from the demo path. The release adds a Docker image, a Render deployment blueprint, standard cloud `PORT` support, health checks, request IDs, payload limits, mutation rate limiting, same-origin content security policy, bounded AI timeouts, progress UI, degraded-AI messaging, and secret-safe defaults.

The included participant dataset is synthetic hackathon data. Local runtime state and `.env` secrets are excluded from Git, archives, and container build context.

## Step 1 — Run the release gate locally

```bash
cd "/Users/abdulhakimshaon/Desktop/Averis/CargoClarity/CargoClarity"
source .venv/bin/activate
pytest
cargoclarity fixtures
python tools/run_phase2_smoke.py
python tools/generate_submission.py
```

Required results are a fully passing test suite, `7/7 fixtures passed`, `failures=[]`, and a submission report with `valid: true` and `record_count: 520`.

## Step 2 — Run the production command locally

Use the production binding without changing source code:

```bash
APP_ENV=production \
API_HOST=0.0.0.0 \
PORT=8000 \
CARGOCLARITY_DISABLE_DOTENV=1 \
cargoclarity-api
```

Open:

```text
http://127.0.0.1:8000/
```

The root redirects to `/dashboard/`. Check health separately:

```bash
curl -i http://127.0.0.1:8000/api/v1/health
```

Confirm the response is `200 OK`, version `1.0.0`, and includes an `X-Request-ID` header.

## Step 3 — Understand AI behavior in deployment

AI assistance is optional per request. Normal deterministic processing continues when no provider key is configured. The dashboard displays `AI assistance: Degraded` rather than hiding the condition.

To use Gemini in a deployment, configure these platform secrets and variables:

```text
AI_PROVIDER=gemini
AI_API_BASE=https://generativelanguage.googleapis.com/v1beta/openai/
AI_MODEL=gemini-2.5-flash
GEMINI_API_KEY=<platform secret>
AI_TIMEOUT_SECONDS=30
```

Never add the real key to `.env.example`, `render.yaml`, source code, screenshots, logs, or Git. The Render blueprint marks `GEMINI_API_KEY` as a secret that must be supplied in the platform dashboard.

## Step 4 — Build the Docker image

Docker Desktop must be running. Then run:

```bash
docker build -t cargoclarity:1.0.0 .
```

The `.dockerignore` file excludes local secrets, virtual environments, runtime state, reports, deliverables, answer keys, scorer files, and organizer-only folders.

## Step 5 — Run the container locally

```bash
docker run --rm \
  -p 8000:8000 \
  -e PORT=8000 \
  -e CARGOCLARITY_DISABLE_DOTENV=1 \
  cargoclarity:1.0.0
```

Then open:

```text
http://127.0.0.1:8000/
```

The container runs as a non-root user and stores demo runtime state under `/tmp/cargoclarity`.

## Step 6 — Deploy using the Render blueprint

The repository contains `render.yaml`. To create a durable public prototype:

1. Push a clean repository to a safe GitHub repository after removing the known forbidden history described in `README.md`.
2. Sign in to Render.
3. Choose **New +** and **Blueprint**.
4. Connect the clean CargoClarity repository.
5. Select the detected `render.yaml` blueprint.
6. Keep the free plan for the prototype.
7. Add `GEMINI_API_KEY` only if an eligible Gemini project is available. Leaving it empty keeps the deterministic product functional.
8. Create the service and wait for the health check to pass.
9. Open the assigned Render URL.

The application root redirects to the dashboard. The health path is `/api/v1/health`.

## Step 7 — Verify the public URL from a fresh browser

Open a private/incognito browser window and visit the public URL. Confirm that no local login, cookie, extension, or cached asset is required.

Complete this exact path:

1. Open the Inbox.
2. Select **Verify inbox**.
3. Wait for the progress banner to complete.
4. Search for `email_001` and inspect its clean comparison.
5. Search for `email_016` and inspect its escalation reason.
6. Open source evidence.
7. Record an unresolved or override decision with a reviewer name and rationale.
8. Open the Audit trail and confirm the event.
9. Open Reports.
10. Download the submission JSON.

## Step 8 — Check degraded AI behavior

Deploy without `GEMINI_API_KEY` or temporarily remove it from a test deployment. Refresh the dashboard. The navigation footer must display:

```text
AI assistance  Degraded
```

Normal rules-only verification, review, audit, reports, and export must still work. Selecting **Use AI assist** must fail safely or fall back without corrupting the deterministic result.

## Step 9 — Check reliability controls

The release includes:

| Control | Behavior |
|---|---|
| Health check | `/api/v1/health` reports data, runtime-store, and AI state |
| Request ID | Every response includes `X-Request-ID` |
| Body limit | Requests over `API_MAX_BODY_BYTES` receive `413` |
| Mutation rate limit | Excess workflow mutations receive `429` |
| Content Security Policy | Browser content and connections are same-origin only |
| Clickjacking protection | `X-Frame-Options: DENY` |
| MIME sniffing protection | `X-Content-Type-Options: nosniff` |
| AI timeout | Provider calls are bounded by `AI_TIMEOUT_SECONDS` |
| Deterministic fallback | Provider failure cannot silently replace the core result |
| Batch progress | Full-inbox work exposes total, completed, failed, and percentage |

The in-memory rate limiter and JSON runtime store are intentionally prototype components. A production multi-instance deployment should replace them with shared Redis and PostgreSQL services.

## Step 10 — Run the secret and forbidden-file scan

```bash
find . -type f \
  \( -iname '*ground*truth*' -o -iname '*answer*key*' -o -iname '*score_cli*' \) \
  -not -path './.git/*'

git ls-files .env .runtime/api_state.json
```

Both commands should print no files. Also inspect the container context with:

```bash
git status --short
```

Only intended source and documentation changes should appear before commit.

## Step 11 — Reset the public demo

The prototype store is intentionally disposable. Restarting a free-tier instance may reset `/tmp/cargoclarity/api_state.json`. This is acceptable for synthetic demo data and should be described honestly.

For durable multi-user production, use the PostgreSQL schema described in the architecture documentation and private object storage for documents.

## Step 12 — Approve Phase 8

Phase 8 passes when the product starts from the documented command, the root opens the dashboard, the health endpoint works, the complete demo path works from a fresh browser, AI unavailability is visible and safe, security headers and limits are present, the Docker/Render configuration contains no secrets, and the repository contains no organizer-only data.
