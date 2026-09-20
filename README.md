# CargoClarity

> Verify the shipment. Understand the decision.

CargoClarity is an explainable shipping-document verification MVP. It classifies a mixed email inbox, routes Bill of Lading comparison requests, extracts seven canonical fields from Shipping Instructions and draft Bills of Lading, compares them with deterministic rules, and escalates uncertain cases instead of guessing.

## Current status

**Phase 0** established the repository and scope. **Phase 1** inspected the participant dataset and created seven local regression fixtures. **Phase 2** implements the deterministic core. **Phase 3** adds an optional schema-validated cloud AI adapter with deterministic fallback. The API, dashboard, persistence layer, human-review workflow, and deployment are later phases.

## Phase 2 capabilities

The core reads TXT, PDF, DOCX, and XLSX attachments through one typed interface. It classifies email records into the five required categories, identifies SI and BL documents from their content, maps variant labels to seven canonical fields, normalizes parties, ports, counts, and weights, and returns field-level `MATCH`, `MISMATCH`, or `UNCERTAIN` results. It produces overall `OK`, `MISMATCH`, or `NEEDS_REVIEW` outcomes with evidence and confidence.

## Quick start

From the repository root on macOS or Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e '.[test]'
pytest
cargoclarity fixtures
```

Expected verification results are **22 passing tests** and **7/7 passing fixtures**.

Process one participant email with:

```bash
cargoclarity email email_001
```

Run the core across all 520 participant emails without reading or using answer labels:

```bash
python tools/run_phase2_smoke.py
```

See [Phase 2 review and operation guide](docs/PHASE2_GUIDE.md) for exact commands, expected results, interpretation, and approval steps.

See [Phase 3 review and operation guide](docs/PHASE3_GUIDE.md) for optional AI configuration, mocked validation, live-call instructions, fallback behavior, and approval steps.

Check the optional AI configuration without sending a request when no key is configured:

```bash
cargoclarity ai-check
```

## Repository layout

```text
src/cargoclarity/              Deterministic core and optional Phase 3 AI adapter
tests/test_phase2_core.py      Automated deterministic-core tests
tests/test_phase3_ai.py        Mocked schema and fallback tests
tests/fixtures/                Seven self-authored regression cases
tools/                         Dataset and smoke-test utilities
docs/                          Product specifications and phase guides
data/participant/              Participant-only dataset bundle
```

## Data safety

The current working tree does not contain `ground_truth.json`, `score_cli.py`, organizer-only material, credentials, or real customer documents. The local Docker bundle contained organizer answer-key material and was removed without reading it. However, an older commit on `origin/main` still contains those paths; see the Phase 2 guide before publishing or pushing further changes. Keep organizer bundles outside the public project and never import them into application or test code.
