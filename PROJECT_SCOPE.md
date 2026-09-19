# CargoClarity MVP Scope

## Objective

Build the smallest reliable, explainable shipping-document verification product that supports the complete workflow:

> Inbox → classify → inspect SI/BL → extract seven fields → normalize → compare → explain with evidence → escalate uncertainty → record a human decision → export JSON.

## In scope

- Load the supplied participant JSON inbox and attachments.
- Classify every message as `BL_COMPARISON`, `SI_REQUEST`, `INVOICE_QUERY`, `GENERAL`, or `SPAM`.
- Route only `BL_COMPARISON` messages into SI/BL verification.
- Read TXT, PDF, DOCX, and XLSX attachments where available.
- Identify SI and BL document roles.
- Extract the canonical fields:
  - `shipper`
  - `consignee`
  - `notify_party`
  - `port_of_loading`
  - `port_of_discharge`
  - `container_count`
  - `gross_weight_kg`
- Normalize labels, names, ports, counts, and weights while preserving raw evidence.
- Compare each field as `MATCH`, `MISMATCH`, or `UNCERTAIN`.
- Produce overall status `OK`, `MISMATCH`, or `NEEDS_REVIEW`.
- Escalate missing attachments, wrong document types, unreadable files, and missing values.
- Display field-level confidence, source excerpts, and explanations.
- Support confirmation, correction, override, retry, and audit history.
- Export the required evaluation JSON for every email.
- Deploy as one cloud-hosted service suitable for the hackathon demo.

## Explicit non-goals

The MVP will not include full account registration, password reset, enterprise multi-tenancy administration, real Outlook/Gmail synchronization, customs or sanctions checks, carrier integrations, automated document correction, vector databases, RAG, model fine-tuning, custom OCR model training, mobile apps, real-time collaboration, a general-purpose chatbot, or a large analytics platform.

Authentication, production-grade object storage, and PostgreSQL may be added only if required by the selected deployment environment; they are not prerequisites for the local MVP.

## Reliability principles

Deterministic rules control final comparison decisions. AI may assist with ambiguous classification, document-role identification, structured extraction, and concise explanations, but AI output must be schema-validated and must never independently create a false mismatch. Missing or unreadable evidence results in human review rather than a guessed result.

## Phase boundary

Phase 0 establishes the repository and scope. Phase 1 will inspect the dataset and create fixtures. No extraction, comparison engine, API, or dashboard implementation belongs in Phase 0.

## Initial demo ID candidates

These are presentation candidates selected from subject signals and must be validated against the dataset during Phase 1:

- `email_038` — document confirmation request
- `email_033` — SI request
- `email_048` — invoice request
- `email_070` — general operational message
- `email_072` — likely spam message

The application must not use hidden answer labels to route or classify records.
