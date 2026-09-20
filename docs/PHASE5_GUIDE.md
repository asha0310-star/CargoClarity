# Phase 5 — Dashboard: Setup and Review Guide

## What this phase does

Phase 5 adds the first reviewer-facing dashboard to CargoClarity. It is served by the existing FastAPI backend at `/dashboard/`, so the browser uses the same origin as the Phase 4 API. No second frontend server, CORS configuration, or cloud account is required for local review.

The dashboard contains the four views required by the hackathon guide:

1. **Inbox:** searchable and filterable message queue with category, status, attachment state, and review count.
2. **Comparison:** seven-field SI-versus-BL table with raw values, normalized values, confidence, results, and explanations.
3. **Evidence and review:** source excerpts in a drawer, review reason, confirmation or override controls, and retry.
4. **Reports/export:** category distribution, outcome distribution, review reasons, processing health, and evaluation JSON download.

The visual hierarchy is deliberate. The overall status is visible first. Fields requiring attention are visible next. Source evidence and reviewer actions appear after the reason for escalation. `NEEDS_REVIEW` uses amber, confirmed `MISMATCH` uses red, and `OK` uses teal. Every status also has text, so color is not the only signal.

The dashboard is a local hackathon prototype. It does not add authentication, production authorization, a PostgreSQL database, or cloud deployment. The API remains bound to `127.0.0.1`.

## What changed

| File | Purpose |
|---|---|
| `dashboard/index.html` | Dashboard shell and four-view layout |
| `dashboard/styles.css` | Operations-console visual system, status hierarchy, responsive layout, drawer, and focus states |
| `dashboard/app.js` | API integration, inbox filters, processing, comparison, evidence, review, retry, reports, and export |
| `src/cargoclarity/api.py` | Same-origin `/dashboard/` static mount |
| `tests/test_phase4_api.py` | Dashboard route and asset regression test |

## Step 1 — Open the project

Open Terminal and run:

```bash
cd "/Users/abdulhakimshaon/Desktop/Averis/CargoClarity/CargoClarity"
```

Confirm the location:

```bash
pwd
```

The path should end with:

```text
/Averis/CargoClarity/CargoClarity
```

## Step 2 — Activate the existing environment

Run:

```bash
source .venv/bin/activate
```

If the environment does not exist, create it and install the current project:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e '.[test,ai,api]'
```

The dashboard does not require a separate Node.js installation because it is a static frontend served by FastAPI.

## Step 3 — Run the complete test suite

Run:

```bash
pytest
```

Expected result:

```text
30 passed
```

The suite includes deterministic-core tests, AI adapter tests, backend workflow tests, and the dashboard-serving test. A dashboard asset test confirms that the HTML, JavaScript, and CSS are served from the same origin and contain the required reviewer actions.

If this command fails, stop and provide the full error output before starting the dashboard.

## Step 4 — Run the original regression checks

Run:

```bash
cargoclarity fixtures
```

Expected result:

```text
7/7 fixtures passed
```

Then run the participant smoke test:

```bash
python tools/run_phase2_smoke.py
```

The final line must be:

```text
failures=[]
```

These checks confirm that the dashboard does not change the deterministic classification or comparison engine.

## Step 5 — Start the backend and dashboard

Run:

```bash
cargoclarity-api
```

Keep this Terminal window open. The backend and dashboard run at:

```text
http://127.0.0.1:8000
```

The dashboard URL is:

```text
http://127.0.0.1:8000/dashboard/
```

Open that URL in your browser. If the dashboard says **API unavailable**, confirm that `cargoclarity-api` is still running and refresh the page.

To stop the server, return to Terminal and press `Control + C`.

## Step 6 — Check the initial Inbox

When the page opens, you should see:

- A dark left navigation with Inbox, Review queue, Reports, Audit log, and Settings.
- Four summary cards.
- A searchable message queue.
- Category, status, and review-state filters.
- A `Prepare demo cases` action.

The participant inbox is loaded immediately, but messages are not processed automatically. This prevents the dashboard from making hundreds of local processing calls at startup.

The first inbox is therefore expected to show records with `Not processed` status.

## Step 7 — Prepare the demo cases

Click:

```text
Prepare demo cases
```

The dashboard processes five representative participant emails:

| Email | Demonstrates |
|---|---|
| `email_001` | Clean document comparison |
| `email_003` | A comparison route with a different outcome |
| `email_016` | Ambiguous classification and safe deterministic fallback |
| `email_038` | Another document workflow case |
| `email_059` | PDF-based document processing |

The button processes them one at a time and waits for each job to complete. It does not run AI over all 520 records.

After completion, refresh the table if necessary. The dashboard now has examples for the five-minute demo without manually editing data.

## Step 8 — Use Inbox filters

Use the search box to search by:

- Email ID, such as `email_016`.
- Sender.
- Subject text.

Use the category filter to choose:

- `BL comparison`.
- `SI request`.
- `Invoice query`.
- `General`.
- `Spam`.

Use the status filter to show:

- `OK`.
- `Mismatch`.
- `Needs review`.

Use the review-state filter to show only cases needing attention.

The table displays the source email ID, sender, subject, category, status, processing state, updated time, and an Open action. Status labels are always textual as well as color-coded.

## Step 9 — Open a comparison

Click a processed row or its `Open →` action.

The Comparison view shows:

1. The email subject and sender.
2. The overall result first.
3. The machine status and review state.
4. Attachment names and evidence actions.
5. The seven-field table.

The seven fields are:

- Shipper.
- Consignee.
- Notify party.
- Port of loading.
- Port of discharge.
- Container count.
- Gross weight.

Each row shows the SI value, BL value, normalized values, result, confidence, explanation, and a `View evidence` action.

A `MISMATCH` is displayed in red only when the deterministic comparison confirms the difference. Missing, unreadable, or incomplete evidence remains `NEEDS_REVIEW` rather than being represented as a false mismatch.

## Step 10 — Inspect source evidence

Click `View evidence` on any comparison row.

A right-side evidence drawer opens. It shows:

- The field result.
- The comparison method.
- The confidence band.
- The explanation.
- The SI source excerpt.
- The BL source excerpt.
- The raw value.
- The normalized value.
- The extraction method.

You can also click `View evidence` beside an attachment name. That requests the backend’s safe attachment preview endpoint and displays a bounded readable-text excerpt.

Close the drawer with the `×` button, click outside the drawer, or press `Escape`.

## Step 11 — Use the optional AI assist

Open a case with a low-confidence or ambiguous classification, such as `email_016`.

Click:

```text
AI assist
```

The dashboard sends `use_ai: true` to the existing backend. With your current `.env`, the request uses local Ollama.

The Phase 3 safeguards still apply:

- The response must be schema-valid.
- The AI confidence must meet the acceptance threshold.
- Low-confidence AI output falls back to the deterministic result.
- The comparison engine remains deterministic.

If Ollama is not running, the dashboard shows a safe processing error or deterministic fallback state. Start Ollama separately if you want to test the local AI call:

```bash
ollama serve
```

The dashboard does not require AI to run its normal workflow.

## Step 12 — Open the Review queue

Use the left navigation and click:

```text
Review queue
```

If no case is selected, click `Find a review case`. The dashboard asks the API for the first processed case with `needs_review=true`.

The review view leads with:

- Why the case was escalated.
- The relevant review reason.
- The field-level machine explanation.
- Links to the source evidence.
- The original machine result.

This ordering is intentional. The reviewer sees the reason and evidence before the action controls.

## Step 13 — Confirm or override a result

In the Review queue, choose a decision:

- `Confirm machine result` when the source evidence supports the machine result.
- `Override result` when the reviewer finds a correction.
- `Leave unresolved` when the evidence is still insufficient.

Choose the final status:

- `OK`.
- `MISMATCH`.
- `NEEDS_REVIEW`.

Enter a short reason. The dashboard will not save an empty review reason.

Click:

```text
Save review decision
```

The API appends the review. It does not overwrite the original machine run. The dashboard then reloads the case and displays the latest effective status separately from the machine status.

## Step 14 — Retry a case

If processing failed or the source file was temporarily unavailable, click:

```text
Retry processing
```

The backend creates a new job and preserves the previous attempt. The dashboard refreshes the case after the retry completes.

## Step 15 — Open Reports

Click:

```text
Reports
```

The Reports view shows:

- Messages processed.
- Processing failures.
- Human review actions.
- Routing distribution by category.
- Outcome distribution by status.
- Review reasons such as missing attachment, unreadable, wrong document type, or missing value.

This view uses the Phase 4 summary endpoint. It does not fabricate counts in the browser.

## Step 16 — Download evaluation JSON

In Reports, click:

```text
Download evaluation JSON
```

The browser downloads:

```text
cargoclarity-evaluation.json
```

The file is keyed by source email ID. Each item includes:

```json
{
  "category": "BL_COMPARISON",
  "status": "OK",
  "review_reason": null,
  "defect_fields": [],
  "has_defect": false
}
```

The export is generated by the backend. Unprocessed emails are not treated as clean results.

## Step 17 — Check responsive behavior

Resize the browser to a narrow laptop or tablet width.

Confirm that:

- The sidebar becomes a compact horizontal navigation.
- The inbox table can scroll horizontally without breaking the page.
- Comparison values wrap instead of overflowing.
- The evidence drawer remains usable.
- Buttons remain keyboard reachable.
- Status meaning remains available in text without relying on color.

## Step 18 — Reset the local demo state

The API stores local processing and review state in:

```text
.runtime/api_state.json
```

To reset the dashboard demonstration:

1. Stop `cargoclarity-api` with `Control + C`.
2. Run:

```bash
rm -rf .runtime
```

3. Start the server again:

```bash
cargoclarity-api
```

The inbox will return to the unprocessed participant state.

The `.runtime` directory is ignored by Git and is not included in the project archive.

## Step 19 — Review Phase 5 boundaries

Phase 5 includes the dashboard experience and API integration. It does not yet include:

- Login or workspace authorization.
- A production relational database.
- A complete immutable audit-log screen.
- A production queue worker.
- Cloud deployment.
- The local scorer or organizer answer key.

Those are later concerns. Do not expose the local server publicly before authentication, authorization, CORS restrictions, rate limits, and production secret handling are implemented.

## Step 20 — Approve Phase 5

Approve Phase 5 only when:

- `pytest` reports 30 passing tests.
- `cargoclarity fixtures` reports 7/7 passing fixtures.
- The full deterministic smoke test ends with `failures=[]`.
- `cargoclarity-api` starts successfully.
- `/api/v1/health` returns `status: ok`.
- `/dashboard/` loads the operations console.
- The Inbox lists participant records and supports filters.
- The five demo cases can be prepared without developer tools.
- A comparison shows seven fields and evidence actions.
- The evidence drawer shows source excerpts.
- A review reason appears before the review controls.
- Confirm, override, unresolved, and retry actions work.
- Reports show backend summary data.
- Evaluation JSON downloads from the Reports view.
- No organizer answer key or secret is present in the repository.

Then reply:

```text
Phase 5 approved. Move to Phase 6.
```

## References

[1]: ./CargoClarity — UI_UX Specification.md "CargoClarity UI/UX Specification"
[2]: ./CargoClarity — API Specification.md "CargoClarity API Specification"
[3]: ./PHASE4_GUIDE.md "CargoClarity Phase 4 backend workflow guide"
[4]: ./PHASE3_GUIDE.md "CargoClarity Phase 3 AI assistance guide"
