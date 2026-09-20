# CargoClarity

> Verify the shipment. Understand the decision.

CargoClarity is an explainable shipping-document verification MVP. It classifies a mixed email inbox, routes Bill of Lading comparison requests, extracts seven canonical fields from Shipping Instructions and draft Bills of Lading, compares them with deterministic rules, and escalates uncertain cases instead of guessing.

## Current status

**Phase 0** established the repository and scope. **Phase 1** inspected the participant dataset and created seven local regression fixtures. **Phase 2** implements the deterministic core. **Phase 3** adds an optional schema-validated AI adapter with deterministic fallback. **Phase 4** adds the local FastAPI backend workflow. The dashboard, production persistence, authentication, and deployment are later phases.

## Phase 2 capabilities

The core reads TXT, PDF, DOCX, and XLSX attachments through one typed interface. It classifies email records into the five required categories, identifies SI and BL documents from their content, maps variant labels to seven canonical fields, normalizes parties, ports, counts, and weights, and returns field-level `MATCH`, `MISMATCH`, or `UNCERTAIN` results. It produces overall `OK`, `MISMATCH`, or `NEEDS_REVIEW` outcomes with evidence and confidence.

## Quick start

From the repository root on macOS or Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e '.[test,ai,api]'
pytest
cargoclarity fixtures
```

Expected verification results are **24 passing tests** and **7/7 passing fixtures**.

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

See [Phase 4 backend workflow guide](docs/PHASE4_GUIDE.md) for API setup, endpoint walkthroughs, review actions, retry, export, error handling, and approval steps.

Phase 3 supports Google Gemini and local Ollama through the same OpenAI-compatible adapter. Google currently documents a Free Tier for eligible Gemini models and projects; use the [official AI Studio API-key page](https://aistudio.google.com/apikey) and do not enable billing if you want to stay within free-tier usage. Ollama runs locally without an API charge.

The local `.env` file is created for development, ignored by Git, and loaded automatically. Its provider settings are local-only and are not committed. Keep any real key only in that ignored file.

Check the optional AI configuration without sending a request when no key is configured:

```bash
cargoclarity ai-check
```

Start the local backend with:

```bash
cargoclarity-api
```

Then check `http://127.0.0.1:8000/api/v1/health`.

## Repository layout

```text
src/cargoclarity/              Core, AI adapter, and Phase 4 API
tests/test_phase2_core.py      Automated deterministic-core tests
tests/test_phase3_ai.py        Mocked schema and fallback tests
tests/test_phase4_api.py       Backend workflow and security tests
tests/fixtures/                Seven self-authored regression cases
tools/                         Dataset and smoke-test utilities
docs/                          Product specifications and phase guides
data/participant/              Participant-only dataset bundle
.runtime/                      Ignored local API state
```

## Data safety

The current working tree does not contain `ground_truth.json`, `score_cli.py`, organizer-only material, credentials, or real customer documents. The local Docker bundle contained organizer answer-key material and was removed without reading it. However, an older commit on `origin/main` still contains those paths; see the Phase 2 guide before publishing or pushing further changes. Keep organizer bundles outside the public project and never import them into application or test code.
