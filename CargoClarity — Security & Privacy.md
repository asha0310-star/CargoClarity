# CargoClarity — Security & Privacy

## 1. Security objectives

CargoClarity handles business correspondence, customer and company names, addresses, shipment quantities, and document files. The system must preserve confidentiality, prevent unauthorized modification, and make processing activity auditable. The prototype should follow least privilege and fail safely even when full enterprise controls are not yet implemented.

## 2. Data classification

| Data | Classification | Handling |
|---|---|---|
| Email subjects and bodies | Confidential business data | Encrypted in transit and at rest; access limited to workspace members |
| SI and BL attachments | Confidential business documents | Private object storage; signed short-lived access only |
| Extracted party, port, quantity, and weight fields | Confidential operational data | Store with tenant boundary and audit history |
| AI prompts and responses | Confidential processing data | Minimize content, redact secrets, apply provider retention controls |
| Confidence and audit events | Internal operational data | Append-only records; supervisor access for review |
| Access tokens and API keys | Secret | Secret manager or protected environment variables; never log |

## 3. Identity and access

The deployed application must require authenticated access. Every request must be associated with a workspace. Workspace membership is checked before reading emails, attachments, comparisons, reports, or audit records.

Roles should be limited to `reviewer` and `supervisor`. Reviewers may process cases and create review decisions. Supervisors may view quality reports and audit history. Administrative functions should be kept outside the hackathon demo unless required.

Use short-lived access tokens, secure cookies where applicable, token rotation, and logout or revocation support. Do not embed provider keys in frontend code.

## 4. File and input security

Uploaded or fetched attachments must be treated as untrusted input. The system shall validate file size, extension, MIME type, and file signature. It shall reject path traversal, unsafe filenames, oversized archives, executable content, and unexpected compression formats. Parsers should run in an isolated worker with resource limits and timeouts.

The API must never construct a file path directly from unvalidated user input. Source objects should be addressed by internal IDs or sanitized storage keys. PDF, DOCX, and XLSX parsing failures must be isolated from the API process.

## 5. AI and third-party processing

The AI provider is a data processor in the product architecture. CargoClarity should send only the text or document fragments needed for the current task. It should avoid sending unrelated email history, credentials, or internal system data. Provider retention, training use, regional processing, and deletion settings must be reviewed before production deployment.

AI output must be treated as untrusted data. Validate it against a strict schema, reject unsupported fields, cap explanation length, and escape text before rendering. The AI must not directly authorize access, perform external actions, or silently change a human-confirmed result.

## 6. Encryption and secrets

Use TLS for all browser, API, storage, and provider communication. Use managed encryption at rest for the database and object storage. Store secrets in the deployment platform's secret manager. Rotate secrets when team membership or deployment credentials change. Logs must contain request IDs and error codes rather than raw tokens or full documents.

## 7. Auditability and integrity

Record ingestion, classification, extraction, comparison, AI calls, retries, exports, review decisions, and authentication events. Audit events should include actor type, actor ID where available, timestamp, affected email, prior state, new state, and reason.

Machine results must remain immutable after completion. A human correction creates a new review decision and a new effective result. This preserves the distinction between what the system originally extracted and what a reviewer decided.

## 8. Privacy and retention

Collect only fields required for verification, reporting, and audit. Provide configurable retention for source documents, derived text, AI prompts, and logs. Delete or anonymize data when the retention period expires. Do not use real customer documents in demos unless the team has permission; the supplied synthetic dataset is the preferred demonstration source.

The product should state that confidence is an operational signal, not a guarantee. Human review remains required for low-confidence, incomplete, unreadable, or semantically ambiguous cases.

## 9. Threat model and mitigations

| Threat | Mitigation |
|---|---|
| Unauthorized document access | Authentication, workspace authorization, private storage, short-lived signed URLs |
| Malicious attachment | MIME and signature validation, sandboxed parsers, size/time limits |
| Prompt injection in document text | Treat extracted text as data; fixed system instructions; schema validation; no tool privileges for document content |
| Data leakage through logs | Structured redacted logs and restricted log access |
| False mismatch | Field-specific rules, confidence thresholds, evidence display, human escalation |
| Tampered review decision | Append-only audit events and immutable machine runs |
| Provider outage | Retry with backoff, deterministic fallback, visible degraded state |
| Cross-tenant data exposure | Workspace-scoped queries and authorization tests |

## 10. Hackathon deployment checklist

Before sharing the prototype, confirm that the repository contains no API keys, private answer key, customer documents, or production credentials. Confirm that the participant-facing bundle does not expose `ground_truth.json`. Test unauthorized attachment access, malformed files, oversized files, invalid JSON, and review permissions. Confirm that the public demo uses synthetic or authorized data and that the prototype can be reset.

## References

[1]: ./cargoclarity_prd.md "CargoClarity Product Requirements Document"
[2]: ./System%20Architecture.md "CargoClarity System Architecture"
[3]: ./Database%20Design.md "CargoClarity Database Design"
[4]: ./API%20Specification.md "CargoClarity API Specification"
[5]: ./UI%20UX%20Specification.md "CargoClarity UI/UX Specification"
[6]: ./review_notes.md "Project review notes and official hackathon requirements"
