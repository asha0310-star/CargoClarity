# Phase 7 — Submission Validation and Hard Cases: Step-by-Step Guide

## Outcome

Phase 7 adds a reproducible submission builder that processes all 520 participant emails and validates the result against the exact participant `sample_submission.json` contract. It does not access an answer key, infer private labels, or hardcode individual email outcomes.

The validator checks record coverage, exact object keys, category vocabulary, status vocabulary, review reasons, canonical defect fields, and logical consistency between `status`, `defect_fields`, and `has_defect`.

## Step 1 — Activate the environment

```bash
cd "/Users/abdulhakimshaon/Desktop/Averis/CargoClarity/CargoClarity"
source .venv/bin/activate
```

## Step 2 — Generate the complete submission

Run:

```bash
python tools/generate_submission.py
```

The generated file is:

```text
deliverables/cargoclarity-submission.json
```

The `deliverables` directory is ignored by Git, so generated evaluation output does not pollute source control.

## Step 3 — Read the validation report

The command prints a JSON report. The required indicators are:

```json
{
  "valid": true,
  "record_count": 520,
  "expected_count": 520,
  "errors": []
}
```

The report also provides category, status, and review-reason distributions. These are operational diagnostics, not accuracy scores.

The current deterministic run produces:

| Measure | Result |
|---|---:|
| Records | 520 |
| BL comparison | 220 |
| SI request | 137 |
| Invoice query | 92 |
| General | 51 |
| Spam | 20 |
| OK | 335 |
| Mismatch | 31 |
| Needs review | 154 |

A high review count is not automatically an error. Many participant records intentionally contain missing, wrong-type, malformed, or unreadable evidence. CargoClarity escalates those inputs rather than inventing a result.

## Step 4 — Inspect the output shape

Run:

```bash
python -m json.tool deliverables/cargoclarity-submission.json | head -40
```

Every top-level key is an email ID. Every result contains exactly:

```text
category
status
review_reason
defect_fields
has_defect
```

Non-comparison routes use the neutral result `status: OK`, `review_reason: null`, an empty defect list, and `has_defect: false`.

## Step 5 — Run hard-case regression tests

Run:

```bash
pytest tests/test_phase2_core.py tests/test_phase7_submission.py
```

The regression set covers clean matches, one-field mismatches, multi-field mismatches, missing attachments, wrong document types, unreadable files, missing values, non-comparison neutral output, exact 520-record coverage, and invalid output rejection.

## Step 6 — Run the independent full-dataset smoke test

Run:

```bash
python tools/run_phase2_smoke.py
```

The final line must be:

```text
failures=[]
```

This is separate from submission generation, which helps detect accidental coupling between the validator and the smoke runner.

## Step 7 — Use an organizer scorer only as a black box

If organizers provide an official local or remote self-evaluation endpoint, submit the generated JSON through the documented endpoint or participant loader. Do not open, import, copy, or commit any organizer reference answers.

For a provided HTTP dataset/scorer URL, the participant loader supports:

```python
from loader import Inbox
import json

inbox = Inbox("http://localhost:8080")
submission = json.load(open("deliverables/cargoclarity-submission.json"))
print(inbox.submit(submission))
```

Only use an endpoint explicitly provided by the organizers. The repository intentionally excludes `ground_truth.json`, `score_cli.py`, answer keys, and the organizer Docker bundle.

## Step 8 — Diagnose without overfitting

If a scorer reports weaknesses, inspect errors in this order:

| Priority | Error class |
|---:|---|
| 1 | A BL comparison email routed to the wrong category |
| 2 | A true mismatch field omitted from `defect_fields` |
| 3 | A formatting difference incorrectly reported as a mismatch |
| 4 | Missing, unreadable, or wrong documents not escalated |
| 5 | Explanation wording |

Every correction must be a general rule supported by source evidence. Never introduce an email-ID condition or private answer label.

## Step 9 — Re-run the complete gate after a change

```bash
pytest
cargoclarity fixtures
python tools/run_phase2_smoke.py
python tools/generate_submission.py
```

Do not keep a change unless every command passes.

## Step 10 — Approve Phase 7

Phase 7 passes when the generator produces all 520 records, the validator reports `valid: true`, every output has the exact participant schema, the hard-case tests pass, the full smoke test reports no failures, and the repository contains no answer key or per-email label logic.
