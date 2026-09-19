# CargoClarity — Product Requirements Document

**Product name:** CargoClarity  
**Tagline:** *Verify the shipment. Understand the decision.*  
**Document status:** Hackathon-ready product definition  
**Owner:** CargoClarity team  

## 1. Executive summary

CargoClarity is an AI-assisted shipping document verification workspace for operations teams. It starts with a mixed email inbox, identifies the messages that require a draft Bill of Lading (BL) check, extracts shipment information from the Shipping Instruction (SI) and BL, compares the seven required fields, and produces an explainable result with confidence and evidence. When the system cannot make a dependable decision, it sends the case to a human reviewer rather than inventing a mismatch.

The product is designed around the supplied SDOC dataset and the hackathon's reliability challenge. It supports plain-text attachments as the baseline and PDF, DOCX, XLSX, scanned, missing, and incorrect attachments as advanced cases.

## 2. Problem statement

Shipping operations staff must find relevant requests in a noisy inbox and repeatedly compare shipment details across documents. The same fact may appear under different labels or formats, while missing, unreadable, or incorrect attachments can make an automated result unsafe. A missed discrepancy can create corrections, delays, and additional operational work. A false alarm creates unnecessary review effort.

CargoClarity addresses both problems by combining AI assistance with deterministic validation, field-level confidence scoring, transparent evidence, and human review.

## 3. Goals and success measures

The primary goal is to deliver a working end-to-end prototype that classifies inbox records, detects exact document defects, and handles uncertainty visibly.

| Goal | Success measure |
|---|---|
| Route inbox messages correctly | High five-way classification accuracy and macro-F1 across BL comparison, SI request, invoice query, general, and spam |
| Catch real defects | Exact defect-field identification for comparable SI/BL pairs |
| Avoid false alarms | Missing or unreadable values produce `NEEDS_REVIEW`, not `MISMATCH` |
| Explain decisions | Every field result includes source values, normalized values, rule/method, and confidence |
| Support operations | Reviewer can confirm, override, retry, and export a result |
| Demonstrate cloud AI use | AI extraction/classification or explanation is called through a cloud-hosted service and is visible in the architecture |

The implementation should optimize the supplied scorer's headline outcomes while retaining the broader human-in-the-loop product value.

## 4. Users and primary journeys

The primary user is a shipping operations coordinator who reviews incoming messages and needs a dependable discrepancy report. A secondary user is a supervisor who reviews escalated cases and audits prior decisions.

The main journey is: open the inbox dashboard, filter or inspect a message, view the predicted category and rationale, open a BL comparison, review the seven field results, inspect source evidence, and export or resolve the case. For a `NEEDS_REVIEW` result, the reviewer selects the correct value or confirms that the case cannot be decided. CargoClarity records the action and updates the final status.

## 5. Product scope

### In scope for the first working version

CargoClarity will ingest the supplied JSON email records or an equivalent API source. It will classify the five required categories, read TXT/PDF/DOCX/XLSX attachments, identify SI and BL documents, extract the seven fields, normalize values, compare fields with field-specific rules, assign confidence, explain outcomes, escalate uncertainty, retain audit history, and export the required JSON report.

### Deliberately deferred

Full enterprise email synchronization, production-grade OCR for every language, user provisioning across multiple organizations, customs or sanctions validation, carrier-system integrations, and automated document correction are outside the hackathon scope.

## 6. Functional principles

CargoClarity will use the SI as the reference document. A semantic variation such as “Shanghai” and “Shanghai Port” should be normalized before comparison. Numeric fields require units and tolerance-aware parsing. A blank, unreadable, or wrong document is evidence of uncertainty, not evidence of a shipment mismatch. An AI explanation must never override a validated structured result without a human decision.

## 7. Risks and mitigations

The main risks are extraction errors, false-positive mismatches, slow or unavailable AI calls, and over-scoping. CargoClarity mitigates them with deterministic parsers for common formats, schema validation, explicit confidence thresholds, retries, cached processing results, a local fallback for classification rules, and a narrow seven-field workflow.

## 8. Release acceptance criteria

The prototype is acceptable when a reviewer can process a representative inbox from start to finish, see the five categories, inspect at least one match and one mismatch, identify the exact differing fields, see evidence and confidence, escalate an edge case, record an override, and download a report. The submission must also include setup instructions, a public prototype, a short demo video, and technical documentation.

## References

[1]: ./Functional%20Requirements.md "CargoClarity Functional Requirements"
[2]: ./System%20Architecture.md "CargoClarity System Architecture"
[3]: ./Database%20Design.md "CargoClarity Database Design"
[4]: ./API%20Specification.md "CargoClarity API Specification"
[5]: ./UI%20UX%20Specification.md "CargoClarity UI/UX Specification"
[6]: ./Security%20%26%20Privacy.md "CargoClarity Security and Privacy"
[7]: ./review_notes.md "Project review notes and official hackathon requirements"

---

**Recommended name:** **CargoClarity** is short, memorable, relevant to shipping, and communicates the product's differentiator: making document-verification decisions understandable rather than merely producing a pass/fail result.
