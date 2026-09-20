# Phase 5 — Operations Workbench: Step-by-Step Guide

## Outcome

Phase 5 delivers a same-origin reviewer workbench at `/dashboard/`. The final design uses a restrained logistics-operations visual language: one global header, a quiet navigation rail, a single summary strip, dense work tables, explicit status dots, and a decision-first comparison record. It intentionally avoids decorative gradients, oversized cards, generic illustrations, and unnecessary animation.

The application uses four status meanings consistently. Teal means complete or confirmed, amber means human attention, red means a confirmed defect, and grey means not processed. Every color signal also has a text label.

## Step 1 — Start CargoClarity

```bash
cd "/Users/abdulhakimshaon/Desktop/Averis/CargoClarity/CargoClarity"
source .venv/bin/activate
cargoclarity-api
```

Open:

```text
http://127.0.0.1:8000/dashboard/
```

## Step 2 — Read the system state

The global header reports whether the API is ready. The lower-left assurance panel shows whether AI assistance is available or degraded. A degraded AI provider does not disable deterministic verification.

## Step 3 — Use the verification Inbox

The summary strip reports the total inbox, processed coverage, review queue, and confirmed defects. The queue supports email ID, subject, and sender search plus category, outcome, and review-state filters.

Select **Inspect** to open a decision record. Select **Process selected** after choosing a row to verify only that message.

## Step 4 — Verify the complete inbox

Select **Verify inbox**. CargoClarity creates one bounded background batch for all currently unprocessed messages. A progress banner displays processed, total, failure count, and percentage. Selecting the button again after completion does not reprocess every message; it reports that the inbox is already verified.

## Step 5 — Inspect a decision record

A decision record leads with the effective outcome and its explanation. Machine and effective statuses are shown separately. The field table then displays the SI reference value, BL value, result, confidence, explanation, and evidence action.

For non-comparison categories, the record explains that classification completed successfully and no SI/BL comparison was required.

## Step 6 — Inspect evidence

Select **Open evidence** for a field or **Preview** for an attachment. The side drawer displays bounded source text, raw and normalized values, parser status, extraction method, comparison method, and confidence.

Close it with **Close**, the outside scrim, or the `Escape` key.

## Step 7 — Use AI assistance only when needed

Select **Use AI assist** on an ambiguous case. The request uses the configured Phase 3 provider. Strict schema validation and the confidence gate remain active, while field comparison stays deterministic.

## Step 8 — Use keyboard and narrow-screen behavior

All controls have visible focus treatment. On narrow screens, primary navigation moves to a fixed bottom bar, tables scroll horizontally, and the decision and review layouts stack without hiding evidence.

## Step 9 — Run visual and route checks

```bash
node --check dashboard/app.js
curl -I http://127.0.0.1:8000/dashboard/
curl -I http://127.0.0.1:8000/dashboard/styles.css
curl -I http://127.0.0.1:8000/dashboard/app.js
pytest tests/test_phase4_api.py
```

The dashboard, stylesheet, and script must return `200 OK`. The JavaScript syntax check and API tests must pass.

## Step 10 — Approve Phase 5

Phase 5 passes when the workbench loads without a second frontend server, the Inbox and filters work, complete-inbox progress is visible, processed cases show an explainable decision record, evidence opens from fields and attachments, non-comparison routes are clear, and the UI remains usable on narrow screens.
