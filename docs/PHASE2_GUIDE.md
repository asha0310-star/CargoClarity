# Phase 2 — Deterministic Core: Setup and Review Guide

## What this phase does

Phase 2 builds the application’s decision-making core without a web interface, API, database, or AI provider. The core can classify an email, read its attachments, identify SI and BL documents, extract the seven required fields, normalize their values, compare them, calculate confidence, and return a safe overall result.

This phase is complete only when the automated tests pass, all seven regression fixtures produce their expected outcomes, real examples from all four file formats are readable, and the complete participant bundle can be processed without a crash.

## Important repository correction

The project previously included `data/participant/sdoc-hackathon-docker`. That folder contained `ground_truth.json` and `score_cli.py`, which must not be committed to a public participant repository or used by the application. The entire Docker folder was removed without reading those files. The safe participant bundle remains at `data/participant/sdoc-hackathon-bundle`.

The environment template was also renamed from `env.example` to `.env.example`, and the Phase 1 notes were renamed from `PHASE1_DATASET_NOTES.md.md` to `PHASE1_DATASET_NOTES.md`.

### Existing GitHub history warning

The forbidden Docker files were already committed in historical commit `d5f720a` and pushed to `origin/main`. The current working tree no longer contains them, but ordinary deletion does not remove them from older Git commits. Do not treat the GitHub repository as submission-safe until its history has been rewritten and force-pushed. That operation changes shared repository history, so it was deliberately not performed without explicit approval. Ask for the history cleanup before publishing a release, sharing the repository with judges, or continuing normal pushes.

## Step 1 — Open the project in Terminal

On your Mac, open Terminal and run:

```bash
cd "/Users/abdulhakimshaon/Desktop/Averis/CargoClarity/CargoClarity"
```

Confirm that you are in the correct folder:

```bash
pwd
```

The output should end with:

```text
/Averis/CargoClarity/CargoClarity
```

## Step 2 — Check Python

Run:

```bash
python3 --version
```

Use Python 3.11 or newer. If the command is unavailable, install a current Python 3 release before continuing.

## Step 3 — Create and activate the local environment

Run:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

After activation, the Terminal prompt normally begins with `(.venv)`. The `.venv` directory is ignored by Git and should not be committed.

Each time you open a new Terminal window, return to the repository and reactivate the environment:

```bash
cd "/Users/abdulhakimshaon/Desktop/Averis/CargoClarity/CargoClarity"
source .venv/bin/activate
```

## Step 4 — Install the Phase 2 package

With the environment active, run:

```bash
python -m pip install --upgrade pip
python -m pip install -e '.[test]'
```

This installs CargoClarity in editable mode together with the PDF, DOCX, XLSX, and test dependencies. Editable mode means later source edits are immediately used without reinstalling the package.

## Step 5 — Run all automated tests

Run:

```bash
pytest
```

The expected result is:

```text
16 passed
```

The tests cover the seven Phase 1 fixtures, five representative email categories, all four attachment readers, typed file failures, label mapping, value normalization, a clean TXT pair, a PDF pair, a mixed XLSX/DOCX pair, and a wrong-document case.

If any test fails, do not move to Phase 3. Copy the complete failure output and provide it for correction.

## Step 6 — Run the seven required regression fixtures

Run:

```bash
cargoclarity fixtures
```

The expected result is:

```text
PASS clean_match: OK []
PASS one_field_mismatch: MISMATCH ['consignee']
PASS multi_field_mismatch: MISMATCH ['port_of_loading', 'gross_weight_kg']
PASS missing_attachment: NEEDS_REVIEW []
PASS wrong_document_type: NEEDS_REVIEW []
PASS unreadable_file: NEEDS_REVIEW []
PASS missing_value: NEEDS_REVIEW []

7/7 fixtures passed
```

This is the main Phase 2 completion test. It confirms that missing or unreadable evidence becomes `NEEDS_REVIEW` rather than a false `MISMATCH`.

## Step 7 — Inspect a clean TXT comparison

Run:

```bash
cargoclarity email email_001
```

In the JSON output, confirm:

```text
category = BL_COMPARISON
comparison.status = OK
comparison.defect_fields = []
```

Open the individual objects in `comparison.fields`. Each field should show its SI and BL values, normalized values, comparison method, explanation, evidence location, and confidence.

## Step 8 — Inspect the mixed XLSX/DOCX case

Run:

```bash
cargoclarity email email_055
```

Confirm that the attachment summaries show:

```text
openpyxl
python-docx
```

The comparison status should be `OK`. This proves that the comparison engine is independent of the original file format.

## Step 9 — Inspect the PDF case

Run:

```bash
cargoclarity email email_059
```

Confirm that both attachments use the `pypdf` parser and that all seven field results are `MATCH`. The overall status should be `OK`.

## Step 10 — Inspect safe escalation cases

Run the missing-attachment example:

```bash
cargoclarity email email_003
```

Confirm:

```text
comparison.status = NEEDS_REVIEW
comparison.review_reason = missing_attachment
```

Then run the wrong-document example:

```bash
cargoclarity email email_501
```

Confirm:

```text
comparison.status = NEEDS_REVIEW
comparison.review_reason = wrong_doc_type
```

The second case contains a Commercial Invoice where the draft BL should be. CargoClarity must not compare invoice values and call them shipment defects.

## Step 11 — Smoke-test all 520 emails

Run:

```bash
python tools/run_phase2_smoke.py
```

The command does not read or use any answer key. It checks that every participant email can be loaded and processed without crashing. The final line must be:

```text
failures=[]
```

Classification and status counts are diagnostics, not accuracy scores. Accuracy tuning against the official scorer belongs to Phase 7.

## Step 12 — Review the implementation files

| File | What to review |
|---|---|
| `src/cargoclarity/readers.py` | Typed readers and safe parser failures |
| `src/cargoclarity/classifier.py` | Visible email-category rules and signals |
| `src/cargoclarity/labels.py` | Canonical aliases for the seven fields |
| `src/cargoclarity/normalizers.py` | Party, port, count, and weight normalization |
| `src/cargoclarity/extractor.py` | Document-role detection, evidence, and extraction |
| `src/cargoclarity/comparison.py` | Field-specific decisions and confidence |
| `src/cargoclarity/pipeline.py` | Classification-first orchestration |
| `src/cargoclarity/cli.py` | Commands used for manual verification |
| `tests/test_phase2_core.py` | Automated acceptance tests |

The core must not contain email-ID-specific answers, organizer labels, hidden-answer imports, AI calls, UI code, API routes, or database logic.

## Step 13 — Check repository safety

Run:

```bash
find . -type f \
  \( -iname '*ground*truth*' -o -iname '*answer*key*' -o -iname '*score_cli*' \) \
  -not -path './.git/*'
```

The command should print nothing.

Then run:

```bash
git status --short
```

Review the listed Phase 2 changes. Do not add `.venv`, `.env`, secrets, or organizer files.

Check whether the forbidden files remain in history:

```bash
git log --all --oneline -- \
  data/participant/sdoc-hackathon-docker/data_v2/ground_truth.json \
  data/participant/sdoc-hackathon-docker/server/score_cli.py
```

At present this reports commit `d5f720a`. Cleaning it requires a coordinated history rewrite and force-push. Do not run an improvised deletion command; request that cleanup explicitly so a backup, history rewrite, verification, and remote update are handled together.

## Step 14 — Approve the phase

Approve Phase 2 only if all of the following are true:

- `pytest` reports 16 passing tests.
- `cargoclarity fixtures` reports 7/7 fixtures passed.
- `email_001`, `email_055`, and `email_059` produce `OK`.
- `email_003` produces `NEEDS_REVIEW` with `missing_attachment`.
- `email_501` produces `NEEDS_REVIEW` with `wrong_doc_type`.
- The full smoke test ends with `failures=[]`.
- The repository safety search returns no forbidden files.
- The Phase 2 implementation is functionally ready, but public-repository approval remains blocked until the known Git-history cleanup is authorized and completed.

After checking these items, reply:

```text
Phase 2 approved. Move to Phase 3.
```

## What is deliberately not included

Phase 2 does not add cloud AI extraction, FastAPI routes, Streamlit screens, persistence, human-review actions, audit history, export endpoints, or deployment. Phase 3 adds the schema-validated AI adapter while preserving this deterministic core as the decision authority.

## References

[1]: ../data/participant/sdoc-hackathon-bundle/README.md "SDOC Hackathon participant bundle README"
[2]: ./CargoClarity — Functional Requirements.md "CargoClarity Functional Requirements"
[3]: ./CargoClarity — System Architecture.md "CargoClarity System Architecture"
