# CargoClarity — UI/UX Specification

## 1. Experience principles

CargoClarity should feel like a calm operations console, not a generic AI chat screen. The interface must answer three questions immediately: what needs attention, why the system reached its result, and what the reviewer can do next.

The design should use plain operational language. “Needs review” is preferable to a vague “AI failed.” Color must support, not replace, text labels. Every confidence indicator must include a numeric value or explanation on hover and must never imply certainty beyond the evidence.

## 2. Navigation

The application uses a compact left navigation with the following destinations:

- **Inbox:** all ingested messages and processing states.
- **Review queue:** cases with `NEEDS_REVIEW` or low confidence.
- **Reports:** aggregate quality and export tools.
- **Audit log:** immutable decision history.
- **Settings:** workspace and processing preferences.

## 3. Screen specifications

### 3.1 Inbox dashboard

The dashboard opens with a headline summary: total messages, document checks, mismatches, cases needing review, and processing failures. The main table shows email ID, subject, sender, category, status, confidence, attachment state, and last updated time.

Filters include category, status, review reason, file type, date, and free-text search. Rows should be scannable and should expose a clear next action. A mismatch row opens the comparison. A review row opens the evidence-first review screen. Non-document categories open a classification detail panel rather than an empty comparison screen.

### 3.2 Classification detail

The classification panel shows the predicted category, confidence, signals, and the decision source. It may show a short email excerpt and attachment summary. A reviewer can reprocess an ambiguous classification or route it manually when the product supports that action.

### 3.3 Comparison workspace

The comparison workspace is the main product surface. The header shows the source email, overall status, summary explanation, processing time, and actions for export, retry, or review.

The central area is a seven-row comparison table:

| Field | SI reference | BL value | Result | Confidence |
|---|---|---|---|---|
| Shipper | Raw and normalized value | Raw and normalized value | Match/mismatch/uncertain | Band and score |
| Consignee | Raw and normalized value | Raw and normalized value | Match/mismatch/uncertain | Band and score |
| Notify party | Raw and normalized value | Raw and normalized value | Match/mismatch/uncertain | Band and score |
| Port of loading | Raw and normalized value | Raw and normalized value | Match/mismatch/uncertain | Band and score |
| Port of discharge | Raw and normalized value | Raw and normalized value | Match/mismatch/uncertain | Band and score |
| Container count | Parsed quantity | Parsed quantity | Match/mismatch/uncertain | Band and score |
| Gross weight | Kilograms | Kilograms | Match/mismatch/uncertain | Band and score |

Each row has a “View evidence” action. Evidence opens a side drawer containing the source document name, page or line location, raw excerpt, normalized value, parser method, and comparison explanation.

### 3.4 Human review screen

The review screen leads with the reason for escalation: missing attachment, wrong document type, unreadable file, or missing value. It shows the relevant evidence before presenting the decision controls.

The reviewer can confirm the proposed result, correct a value, mark a field as unresolved, or retry processing. Any override requires a short reason. After saving, the screen shows the new final status and a link to the audit event.

### 3.5 Reports screen

The reports screen presents category distribution, match/mismatch/review counts, field-level discrepancy frequency, parser failures, and AI-call health. It includes an export button for evaluation JSON and a human-readable discrepancy report.

## 4. Visual language

Use a neutral light background, dark text, restrained blue as the primary action color, amber for review, and red only for confirmed mismatches or failures. Each status must include a text label such as `MATCH`, `MISMATCH`, or `NEEDS_REVIEW`. Avoid decorative dashboards that compete with evidence.

Use a readable sans-serif typeface with generous line height. Keep the comparison table dense enough for operations work but allow long party names and addresses to wrap. Preserve raw values in a monospace or quote-like evidence treatment so that reviewers can distinguish extracted content from system interpretation.

## 5. Responsive and accessibility requirements

The dashboard must remain usable at laptop width and should support a narrower tablet layout. Keyboard users must be able to move through filters, table rows, evidence, and review actions. Status must not rely on color alone. Focus states must be visible. Tables need appropriate headers, labels, and accessible descriptions. Error messages should state the problem and recovery action.

## 6. Empty, loading, and error states

An empty inbox should explain how to ingest data. A queued job should show a progress stage such as “Reading attachments” or “Comparing fields.” A failed job should show a stable error code, plain-language explanation, retry action, and link to the audit record. An unreadable document should never render as a blank clean result.

## 7. Demo-critical interactions

The five-minute demo should use a prepared sequence that demonstrates the product's differentiation: open the inbox, filter to document checks, open a normalized match, open an exact mismatch, inspect evidence, open an uncertain case, and record a human override. The path should require no hidden configuration or manual database changes.

## References

[1]: ./cargoclarity_prd.md "CargoClarity Product Requirements Document"
[2]: ./Functional%20Requirements.md "CargoClarity Functional Requirements"
[3]: ./API%20Specification.md "CargoClarity API Specification"
[4]: ./Security%20%26%20Privacy.md "CargoClarity Security and Privacy"
