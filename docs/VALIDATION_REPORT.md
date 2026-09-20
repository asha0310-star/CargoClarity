# CargoClarity Validation Report

**Release:** 1.0.0  
**Dataset:** Participant bundle only  
**Evaluation date:** 20 September 2026

## Executive result

CargoClarity processes all 520 participant email records without an unhandled failure and produces a submission object that exactly matches the participant `sample_submission.json` structure. The automated suite contains 39 passing tests. The seven self-authored deterministic fixtures all pass.

No organizer answer key was opened, imported, copied, or used. Therefore this report makes no unsupported claim about private-label accuracy. It reports structural validity, processing coverage, deterministic regression behavior, and observed output distribution.

## Release gate

| Check | Result |
|---|---:|
| Automated tests | 39 passed |
| Deterministic fixtures | 7/7 passed |
| Participant emails processed | 520/520 |
| Unhandled full-dataset failures | 0 |
| Submission records | 520 |
| Submission schema errors | 0 |
| Forbidden files in working tree | 0 |

## Output distribution

| Category | Count |
|---|---:|
| BL comparison | 220 |
| SI request | 137 |
| Invoice query | 92 |
| General | 51 |
| Spam | 20 |

| Effective status | Count |
|---|---:|
| OK | 335 |
| Mismatch | 31 |
| Needs review | 154 |

| Review reason | Count |
|---|---:|
| Missing attachment | 96 |
| Missing value | 48 |
| Unreadable | 5 |
| Wrong document type | 5 |

The high review count is consistent with a conservative safety policy. Missing or unreliable evidence is not converted into a guessed result.

## What is tested

The deterministic layer covers supported document formats, parser failures, label aliases, field-specific normalization, weight and container parsing, exact one- and multi-field mismatches, missing evidence, wrong document types, unreadable content, and mixed-format documents.

The AI layer is tested through mock transports for strict schema validation, semantic evidence checks, provider failures, malformed output, low-confidence rejection, and deterministic fallback. Local Ollama and Gemini use the same OpenAI-compatible adapter.

The API layer covers ingestion, processing, jobs, comparison, safe attachment preview, path traversal rejection, review validation, retry, review history, immutable machine status, audit history, complete-inbox batches, reports, export, root routing, request IDs, security headers, payload limits, and dashboard asset serving.

The submission layer independently processes the participant data and validates all 520 email IDs, exact result fields, canonical categories, statuses, review reasons, defect fields, and consistency between defects and overall status.

## Remaining uncertainty

Private-label classification precision, recall, and exact defect-field accuracy can be measured only through an organizer-provided scorer endpoint. If that endpoint is available, the generated `deliverables/cargoclarity-submission.json` should be submitted as a black box. Any correction should be evidence-based and generalized; no per-email condition or private label may enter the product.

## Reproduction

```bash
source .venv/bin/activate
pytest
cargoclarity fixtures
python tools/run_phase2_smoke.py
python tools/generate_submission.py
```

The expected terminal indicators are `39 passed`, `7/7 fixtures passed`, `failures=[]`, and a validation report containing `"valid": true` and `"record_count": 520`.
