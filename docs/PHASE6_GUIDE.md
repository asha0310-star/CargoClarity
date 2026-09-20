# Phase 6 — Human Review and Audit: Step-by-Step Guide

## Outcome

Phase 6 completes the human-in-the-loop workflow. A reviewer can open every case whose effective result is `NEEDS_REVIEW`, read the reason and source evidence before seeing the decision form, record a named decision, and inspect a separate immutable history of machine and human actions.

The original machine result is never overwritten. A review creates a new effective result and an audit event that records the reviewer, timestamp, prior state, new state, decision, and rationale.

## Step 1 — Start the product

From the repository root, activate the environment and start the API:

```bash
source .venv/bin/activate
cargoclarity-api
```

Open:

```text
http://127.0.0.1:8000/dashboard/
```

## Step 2 — Create reviewable cases

If the inbox has not been processed, click **Verify inbox**. The progress banner reports the total, processed count, failures, and percentage. You can continue browsing while the background batch runs.

To create one reviewable case from Terminal instead, run:

```bash
curl -s -X POST http://127.0.0.1:8000/api/v1/emails/email_016/process \
  -H 'Content-Type: application/json' \
  -d '{"force": true, "use_ai": false}'
```

Copy the returned job ID and inspect it:

```bash
curl -s http://127.0.0.1:8000/api/v1/jobs/JOB_ID | python -m json.tool
```

## Step 3 — Open the Review queue

Select **Review queue** in the left navigation. Every email whose latest effective status is `NEEDS_REVIEW` appears in the queue. Selecting a row loads the case without changing its status.

The detail pane presents information in this order:

1. Why the engine stopped.
2. The uncertain or missing fields.
3. Source-evidence links.
4. Existing human decision history.
5. Decision controls.

This ordering prevents a reviewer from acting before reading the relevant context.

## Step 4 — Inspect evidence

Select **Read source evidence** next to a field, or preview an attachment when the case-level reason concerns a missing or unreadable document. The evidence drawer contains the bounded source excerpt, raw value, normalized value, extraction method, comparison method, and confidence.

Missing evidence remains visibly missing. The application does not synthesize or guess a value.

## Step 5 — Record a decision

Enter the reviewer name and select one of three decisions:

| Decision | Meaning | Effective status rule |
|---|---|---|
| `CONFIRMED` | The source supports the machine decision | Must preserve the machine status |
| `OVERRIDDEN` | The reviewer found a different defensible result | Reviewer selects the corrected status |
| `UNRESOLVED` | The available evidence remains insufficient | Must remain `NEEDS_REVIEW` |

Enter a rationale and select **Record decision**. Every override requires a specific rationale of at least 12 characters. The backend also enforces these rules, so they cannot be bypassed by calling the API directly.

## Step 6 — Verify machine and effective status separation

After recording a decision, open the case in **Inbox**. The decision record shows:

- **Machine result:** the original immutable pipeline result.
- **Effective result:** the latest human-reviewed result.
- **Human decisions:** the number of appended reviews.

An override changes only the effective result. The original run and its evidence remain available.

## Step 7 — Inspect the audit trail

Select **Audit trail**. The event stream includes processing, retries, batch runs, failures, and review decisions. Review events include the actor, case, prior status, new status, reason, and timestamp.

Selecting a case ID opens its decision record. The API equivalents are:

```bash
curl -s http://127.0.0.1:8000/api/v1/audit?limit=100 | python -m json.tool
curl -s http://127.0.0.1:8000/api/v1/emails/email_016/audit | python -m json.tool
curl -s http://127.0.0.1:8000/api/v1/emails/email_016/reviews | python -m json.tool
```

## Step 8 — Test retry

From a review case, select **Retry document processing**. CargoClarity creates a new processing run. Previous runs and reviews remain in state and the retry creates additional audit events.

## Step 9 — Run the Phase 6 regression tests

Run:

```bash
pytest tests/test_phase4_api.py
```

The suite verifies review validation, reviewer attribution, prior and new state, immutable machine output, review history, email-scoped audit history, batch processing, request errors, and dashboard serving.

## Step 10 — Approve Phase 6

Phase 6 passes when a reviewable case can be explained from source evidence, a reviewer can confirm, override, or leave it unresolved, invalid decision transitions are rejected, the machine status remains unchanged, and the audit trail shows the actor, timestamp, prior result, new result, and reason.
