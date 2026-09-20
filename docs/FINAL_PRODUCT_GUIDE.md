# CargoClarity 1.0 — Final Product Guide

## 1. Install and verify

```bash
cd "/Users/abdulhakimshaon/Desktop/Averis/CargoClarity/CargoClarity"
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e '.[test,ai,api]'
pytest
cargoclarity fixtures
python tools/run_phase2_smoke.py
python tools/generate_submission.py
```

The release gate is 39 passing tests, 7/7 fixtures, no full-dataset failures, and 520 valid submission records.

## 2. Start the product

```bash
cargoclarity-api
```

Open `http://127.0.0.1:8000/`. Keep Terminal open while using the product.

## 3. Verify the inbox

Select **Verify inbox**. CargoClarity processes every unprocessed message with deterministic classification, extraction, normalization, and comparison. The progress banner reports the live batch status. AI is not used by this bulk action, which makes the default run reproducible and cost-free.

## 4. Inspect routing and decisions

Use Inbox search and filters to isolate document comparisons, SI requests, invoice queries, general messages, spam, mismatches, or reviewable cases. Select **Inspect** to open the decision record.

The record leads with the effective outcome, then separates the machine result from any human result. For a BL comparison, it shows all seven SI-versus-BL field decisions and their source evidence. Other categories stop after routing.

## 5. Use AI assistance selectively

Select **Use AI assist** only for an ambiguous case. Local Ollama is the no-API-charge option. Gemini is the cloud option when an eligible project and key are available. Schema validation, evidence requirements, confidence thresholds, and deterministic fallback apply to either provider.

## 6. Resolve uncertain cases

Open **Review queue**. Select a case, read why processing stopped, and inspect source evidence. Record one of three outcomes: confirm the machine result, override it with a specific rationale, or leave the case unresolved. Machine output remains immutable.

## 7. Inspect accountability

Open **Audit trail**. Processing, batch, retry, failure, and human review events are shown separately. A human review event identifies the reviewer, prior state, new state, timestamp, and rationale.

## 8. Review quality and export

Open **Reports** to inspect processing coverage, category distribution, effective outcomes, escalation reasons, review count, and audit count. Select **Download submission JSON** to obtain the participant-compatible output.

You can generate the same validated output from Terminal:

```bash
python tools/generate_submission.py
```

## 9. Reset the demo

Stop the API with `Control + C`, then run:

```bash
rm -rf .runtime
cargoclarity-api
```

The synthetic participant inbox is reloaded with no processed state.

## 10. Deploy

Use the included `Dockerfile` for any container platform or `render.yaml` for a Render blueprint. Configure provider keys only in the platform secret manager. The product remains functional in deterministic mode when AI is unavailable and reports that state visibly.

## 11. Product boundaries

CargoClarity 1.0 is a single-instance hackathon product using synthetic participant data. Its local JSON store and in-memory limiter are transparent prototype choices. Production expansion should add organizational login, workspace authorization, PostgreSQL, private object storage, Redis-backed jobs and limits, and managed observability without changing the core decision contract.
