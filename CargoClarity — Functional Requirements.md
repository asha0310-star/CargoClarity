# CargoClarity — Functional Requirements

## 1. Purpose

This document defines what CargoClarity must do. Requirements are written so they can be implemented, demonstrated, and tested against the supplied inbox and self-evaluation format.

## 2. Actors

| Actor | Responsibility |
|---|---|
| Operations reviewer | Inspects inbox cases, reviews comparisons, and resolves escalations |
| Supervisor | Reviews audit history and monitors system quality |
| AI extraction service | Assists with classification, field extraction, and explanations |
| CargoClarity backend | Orchestrates ingestion, parsing, comparison, persistence, and reporting |
| Dataset/API source | Provides email records and attachments |

## 3. Requirements

### FR-001 Inbox ingestion

The system shall ingest email records containing `email_id`, sender, subject, body, and attachment paths. It shall preserve the original record and support repeatable reprocessing.

### FR-002 Email classification

The system shall classify every email into exactly one of `BL_COMPARISON`, `SI_REQUEST`, `INVOICE_QUERY`, `GENERAL`, or `SPAM`. The result shall include a confidence score and an explanation or signal summary.

The classifier should use deterministic signals first, such as subject and body phrases, attachment presence, and document cues. AI assistance may resolve ambiguous messages. The result shall record whether the decision came from a rule, AI, or a combination.

### FR-003 Routing

Only `BL_COMPARISON` emails shall enter the SI/BL comparison workflow. Other categories shall receive a classification result without generating a false discrepancy report.

### FR-004 Attachment inspection

The system shall inspect attachment names, file extensions, content type, file size, and readable text. It shall detect missing attachments, unreadable files, and likely wrong document types.

### FR-005 Format support

The system shall support TXT, PDF, DOCX, and XLSX attachments in the first complete implementation. Scanned or image-only PDFs shall be detected as requiring OCR or human review. Processing failures shall be visible and retryable.

### FR-006 Document-role detection

The system shall identify which attachment is the SI and which is the BL. It shall not trust a filename alone. It should use document headings, labels, and content signals. If the supposed BL is a Commercial Invoice, Packing List, or Certificate of Origin, the case shall be marked `NEEDS_REVIEW` with `wrong_doc_type`.

### FR-007 Field extraction

For both SI and BL, the system shall attempt to extract:

`shipper`, `consignee`, `notify_party`, `port_of_loading`, `port_of_discharge`, `container_count`, and `gross_weight_kg`.

Each extracted value shall include the raw value, normalized value, confidence, source attachment, and source excerpt or location when available.

### FR-008 Label normalization

The system shall map synonymous labels to canonical fields. Examples include `POL` to `port_of_loading`, `POD` to `port_of_discharge`, `Load Port` to `port_of_loading`, `To the Order of` to `consignee`, and `Gross Wt (kgs)` to `gross_weight_kg`.

### FR-009 Value normalization

The system shall normalize case, punctuation, whitespace, address line breaks, common corporate suffixes, port prefixes such as “Port of,” and equivalent unit expressions. It shall retain the original value for evidence.

### FR-010 Intelligent comparison

The system shall compare each field using a field-specific strategy. Parties and ports shall use exact normalized comparison followed by conservative fuzzy matching. Container count shall compare parsed integer counts. Gross weight shall compare numeric kilograms after unit conversion. A fuzzy similarity score shall not independently declare a mismatch when the extraction is uncertain.

### FR-011 Field result

Each field shall receive one of `MATCH`, `MISMATCH`, or `UNCERTAIN`. The result shall show SI value, BL value, normalized values, confidence, comparison method, and explanation.

### FR-012 Overall status

A comparable case with no differing fields shall receive `OK`. A comparable case with one or more confirmed differing fields shall receive `MISMATCH`. A case that cannot be compared dependably shall receive `NEEDS_REVIEW`.

`NEEDS_REVIEW` shall be used for `wrong_doc_type`, `missing_attachment`, `unreadable`, or `missing_value`, with the applicable reason recorded.

### FR-013 Human review

The reviewer shall be able to inspect source evidence, confirm a proposed result, correct an extracted value, override a field result, or mark the case unresolved. The system shall record the reviewer, timestamp, prior result, new result, and reason.

### FR-014 Retry and failure handling

A reviewer shall be able to retry a failed extraction or comparison. The system shall preserve prior attempts and make the latest successful attempt explicit.

### FR-015 Reporting

The system shall provide an inbox-level summary, a case-level comparison report, and an export that follows the required per-email structure: category, status, review reason, defect fields, and defect flag.

### FR-016 Auditability

The system shall retain processing attempts, model or parser versions, confidence values, extracted evidence, human actions, and report export events.

## 4. Non-functional requirements

The dashboard should show an ordinary result within an operationally reasonable response time and should display progress for longer document processing. The API should be stateless at the request layer and should support idempotent reprocessing. All outputs must be schema-valid JSON. The system should fail safely: inability to read a document must never be silently reported as a clean match.

## 5. Acceptance scenarios

| Scenario | Expected outcome |
|---|---|
| SI and BL use different labels but equal values | All relevant fields are `MATCH`; status `OK` |
| SI has 3 containers and BL has 4 | Only `container_count` is `MISMATCH`; status `MISMATCH` |
| BL attachment is absent | Status `NEEDS_REVIEW`; reason `missing_attachment` |
| BL slot contains a Packing List | Status `NEEDS_REVIEW`; reason `wrong_doc_type` |
| PDF has no readable text | Status `NEEDS_REVIEW`; reason `unreadable` |
| SI field is blank or `TBA` | Status `NEEDS_REVIEW`; reason `missing_value` |
| Email is an invoice query | Category `INVOICE_QUERY`; no comparison result |

## References

[1]: ./cargoclarity_prd.md "CargoClarity Product Requirements Document"
[2]: ./System%20Architecture.md "CargoClarity System Architecture"
[3]: ./API%20Specification.md "CargoClarity API Specification"
[4]: ./review_notes.md "Project review notes and official hackathon requirements" 
