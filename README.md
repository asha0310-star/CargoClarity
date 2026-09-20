# CargoClarity

> Verify the shipment. Understand the decision.

CargoClarity is an explainable shipping-document assurance product for operations teams. It classifies a mixed inbox, routes Bill of Lading checks, reads TXT, PDF, DOCX, and XLSX documents, extracts seven canonical shipment fields, compares Shipping Instructions against a draft Bill of Lading, and sends unreliable cases to a human instead of guessing.

## Product status

The hackathon product is complete through **Phase 8**. It includes the deterministic verification core, optional schema-validated AI assistance, FastAPI workflow backend, redesigned operations workbench, human review, immutable audit history, 520-record submission generation, hard-case regression tests, reliability controls, and container/cloud deployment configuration. The Phase 9 video is intentionally excluded.

## Why the design is safer

CargoClarity separates three responsibilities. AI may assist ambiguous classification or extraction when explicitly requested. Deterministic field-specific rules make the final SI-versus-BL comparison. Humans resolve missing, unreadable, contradictory, or low-confidence evidence. Every source value, normalized value, machine result, and review decision remains traceable.

The seven verified fields are `shipper`, `consignee`, `notify_party`, `port_of_loading`, `port_of_discharge`, `container_count`, and `gross_weight_kg`.

## Quick start

From the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e '.[test,ai,api]'
pytest
cargoclarity fixtures
cargoclarity-api
```

Open the complete product:

```text
http://127.0.0.1:8000/
```

The root redirects to the dashboard at `/dashboard/`. The API documentation is available at `/docs`, and health is available at `/api/v1/health`.

The current release gate is:

```text
39 passing tests
7/7 regression fixtures
520/520 valid submission records
0 full-dataset processing failures
```

## Workbench

The interface is an operations workbench rather than a presentation dashboard. It contains:

| Area | Purpose |
|---|---|
| Inbox | Search, filter, route, process, and inspect all participant messages |
| Decision record | Compare SI and BL values side by side with normalization and evidence |
| Review queue | Resolve only cases that cannot be decided safely |
| Audit trail | Preserve machine processing and human decisions as separate events |
| Reports | Monitor coverage, categories, outcomes, review causes, and export readiness |

Select **Verify inbox** to process every unprocessed participant email. Progress is visible while the batch runs. Individual cases can be reprocessed with rules only or with optional AI assistance.

## AI configuration

The local `.env` file is ignored by Git and loaded automatically. The application supports a local Ollama endpoint or a Google Gemini OpenAI-compatible endpoint. No key is required for deterministic processing.

Check the configured provider with:

```bash
cargoclarity ai-check
```

AI output is accepted only when it satisfies the strict JSON schema and confidence gate. Provider errors, invalid output, and low-confidence decisions fall back safely to deterministic behavior.

## Complete-dataset submission

Generate and validate the scorer-compatible 520-record output with:

```bash
python tools/generate_submission.py
```

The generated file is:

```text
deliverables/cargoclarity-submission.json
```

The validator checks the exact participant email IDs, exact result keys, canonical vocabularies, defect fields, review reasons, and logical consistency. It never reads or imports an answer key.

## Deployment

The product ships as one same-origin web service. Build and run the container with:

```bash
docker build -t cargoclarity:1.0.0 .
docker run --rm -p 8000:8000 -e PORT=8000 cargoclarity:1.0.0
```

`render.yaml` provides a Render blueprint. `GEMINI_API_KEY` is declared as a platform secret and is never stored in the repository. Without a cloud AI key, the deployed product remains fully usable in deterministic mode and visibly reports that AI assistance is degraded.

## Guides

| Phase | Guide |
|---|---|
| Dataset inspection | [Phase 1](docs/PHASE1_DATASET_NOTES.md) |
| Deterministic verification | [Phase 2](docs/PHASE2_GUIDE.md) |
| Optional AI assistance | [Phase 3](docs/PHASE3_GUIDE.md) |
| Workflow API | [Phase 4](docs/PHASE4_GUIDE.md) |
| Operations workbench | [Phase 5](docs/PHASE5_GUIDE.md) |
| Human review and audit | [Phase 6](docs/PHASE6_GUIDE.md) |
| Submission validation | [Phase 7](docs/PHASE7_GUIDE.md) |
| Deployment and reliability | [Phase 8](docs/PHASE8_GUIDE.md) |
| Final operating walkthrough | [CargoClarity 1.0 guide](docs/FINAL_PRODUCT_GUIDE.md) |
| Public release evidence | [Browser QA report](docs/PUBLIC_QA_REPORT.md) |

## Repository layout

```text
dashboard/                       Same-origin reviewer workbench
src/cargoclarity/                Core, AI adapter, API, store, and submission builder
tests/                           Deterministic, AI, API, audit, batch, and submission tests
tests/fixtures/                  Seven self-authored regression cases
tools/                           Dataset inspection, smoke, and submission commands
docs/                            Product specifications and phase-by-phase guides
data/participant/                Participant-only hackathon dataset
Dockerfile                       Non-root production container
render.yaml                      Cloud deployment blueprint
.runtime/                        Ignored disposable local state
deliverables/                    Ignored generated artifacts
```

## Data and repository safety

The current working tree contains no `ground_truth.json`, `score_cli.py`, answer key, organizer-only material, credential, or real customer document. The organizer Docker bundle was removed without reading its answer material. An older `origin/main` history was previously found to contain forbidden paths; do not push this branch into that history. Publish from the clean release archive or create a new history before sharing the repository.

CargoClarity is a synthetic-data hackathon prototype. The included JSON runtime store and in-memory limiter are suitable for a single-instance demonstration. A production multi-user system should use authentication, workspace authorization, PostgreSQL, object storage, Redis-backed rate limiting, and managed secrets as described in the architecture and security specifications.
