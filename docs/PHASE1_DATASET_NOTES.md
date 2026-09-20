# Phase 1 — Dataset Inspection Notes

## Conclusion

The participant bundle contains **520 email records** and **250 attachments**. It is a mixed inbox rather than a document-only corpus: **394 emails have no attachments**, while the remaining records contain SI/BL document pairs. The attachment set includes **192 TXT files, 28 PDF files, 22 XLSX files, and 8 DOCX files**. The first implementation should therefore classify the inbox before attempting document processing, and it must treat attachment absence as a normal routing condition rather than as a parser failure.

The dataset is suitable for a deterministic-first MVP. Subjects and bodies contain strong operational phrases, document headings are regular enough for role detection, and the seven fields appear under multiple labels. The main extraction risks are mixed file formats, multiline values, table layouts, numeric units, and semantic differences in party names.

## Source schema and loading

Each inbox record has the keys `email_id`, `from`, `subject`, `body`, and `attachments`. The participant loader exposes local and HTTP-backed sources through the same `Inbox` interface. Local attachment paths are relative strings such as `attachments/email_004_SI.txt`. The source README confirms that every email must appear in the final submission and that only five categories are valid.

The source uses `from`, not `sender`. This distinction is recorded here so that the future API mapping does not silently lose sender information.

## Format inventory

| Format | File count | Emails containing the format | Observed structure | MVP implication |
|---|---:|---:|---|---|
| TXT | 192 | 98 | Plain text with heading separators and label/value lines | Implement first and use as the baseline parser. |
| PDF | 28 | 15 | Text-bearing PDFs with SI/BL headings and table-like container rows | Use text extraction and detect empty/image-only output. |
| XLSX | 22 | 15 | One or more worksheets with label/value rows | Read cell values and preserve sheet/row evidence. |
| DOCX | 8 | 8 | Word paragraphs and tables; bilingual labels appear | Parse paragraphs and tables; do not depend on filenames alone. |

Representative samples inspected were the TXT pair for `email_004`, the PDF pair for `email_059`, the XLSX Shipping Instruction for `email_055`, and the DOCX draft BL for `email_055`. The `email_055` pair is especially useful because it crosses formats: the SI is XLSX and the BL is DOCX.

The TXT sample uses labels such as `Shipper`, `Consignee (Non-Negotiable)`, `Notify`, `Port of Loading (POL)`, `POD`, `Total Containers`, and `Gross Wt (kgs)`. The PDF sample uses `POL`, `Port of Discharge (POD)`, and `No. of Containers`. The XLSX sample uses `Shipper/Exporter`, `Load Port`, `POD`, `Container Count`, and `GROSS WEIGHT`. The DOCX sample includes bilingual labels such as `Shipper (Principal or Seller)`, `Consignee`, `Notify`, `PORT OF LOADING`, `POD`, `Total Containers`, and `Gross Wt (kgs)`.

## Classification signals

The inspected subjects support transparent rules before AI fallback. Document-check candidates commonly contain `TO CONFIRM DOCS`, `Draft BL`, `REQUEST BL DRAFT`, or similar language. SI-request candidates commonly contain `REQUEST SI`, `SI NEEDED`, `CUST SI`, or `Submit SI`. Invoice-related candidates use phrases such as `INVOICE`, `BILLING`, `FREIGHT`, `LOCAL CHARGES`, or `DETENTION CHARGES`. General messages include operational phrases such as `Delivery planning` and `UPDATE SUMMARY`. Spam examples use promotional or prize language, including `weird trick`, `CONGRATULATIONS`, and unsolicited link language.

These phrase groups overlap in some records. For example, a document-check subject can contain `BL` while its body requests a missing draft. The classifier should combine subject, body, attachment presence, and document cues, and it should preserve the signal list for explanation. A rule must not classify an email from one keyword alone.

Initial presentation candidates selected for later validation are `email_038` for a document-check request without attachments, `email_033` for an SI request, `email_048` for an invoice-related request, `email_070` for a general operational message, and `email_072` for a spam-like message. These are candidates only; Phase 2 or the evaluation harness must not hard-code their labels.

## Document and field patterns

Document roles are recognizable from content headings such as `SHIPPING INSTRUCTION`, `BILL OF LADING INSTRUCTION`, and `BILL OF LADING (DRAFT)`. The implementation should use these headings together with field density and attachment pairing. A filename suffix of `_SI` or `_BL` is useful evidence but must not be the only role signal.

The seven canonical fields occur with meaningful label variation. The label mapper should include the following observed families:

| Canonical field | Observed labels |
|---|---|
| `shipper` | `Shipper`, `Shipper/Exporter`, `Shipper (Principal or Seller)` |
| `consignee` | `Consignee`, `Consignee (Non-Negotiable)`, `To the Order of` |
| `notify_party` | `Notify`, `Notify Party` |
| `port_of_loading` | `POL`, `Port of Loading (POL)`, `Load Port`, `PORT OF LOADING` |
| `port_of_discharge` | `POD`, `Port of Discharge (POD)`, `Discharge Port` |
| `container_count` | `Total Containers`, `Container Count`, `No. of Containers` |
| `gross_weight_kg` | `Gross Wt (kgs)`, `Gross Weight (KG)`, `GROSS WEIGHT`, `Gross Wt (kgs)` |

Values frequently span multiple lines because company names include addresses. The parser should capture a bounded value region rather than only the text on the same line as a label. Ports may include country names and codes, while party values may contain punctuation, corporate suffixes, and `ON BEHALF OF` clauses. Container counts include forms such as `6 x 40'HC` and `12 x 20'FCL`; comparison should extract the integer count and retain the full raw value. Weight values include comma separators and explicit or implicit kilogram units.

## Edge-case inspection set

Twenty records were inspected as edge-case candidates without using answer labels: `email_003`, `email_005`, `email_015`, `email_038`, `email_055`, `email_059`, `email_072`, `email_097`, `email_107`, `email_160`, `email_208`, `email_243`, `email_273`, `email_291`, `email_302`, `email_313`, `email_351`, `email_354`, `email_398`, and `email_511`.

The set covers attachment-free messages, spam-like messages, TXT/PDF/DOCX/XLSX combinations, and mixed-format pairs. `email_511` is a useful cross-format case because its SI is TXT and its BL is PDF. The attachment-free document-request cases demonstrate why classification must precede comparison: an email can clearly request a BL check while still requiring `missing_attachment` review handling.

The inspection also found no attachment paths that were missing from the participant bundle. Empty or unreadable content must still be handled explicitly by the future reader interface because the product requirements require safe escalation even when the supplied sample does not expose every failure through a missing path.

## Phase 1 regression fixtures

The local fixture file defines seven synthetic, self-contained cases: a normalized match, a one-field mismatch, a multi-field mismatch, a missing BL attachment, a wrong document type, an unreadable document, and a missing value. The fixtures are authored test data, not organizer labels, and are intended to test the deterministic core in Phase 2.

## Recommended implementation order after approval

First implement the TXT reader and canonical label mapper because TXT is the largest format family and gives the clearest evidence. Then add PDF text extraction, XLSX cell/table extraction, and DOCX paragraph/table extraction. Keep raw excerpts and locations in every extracted field. Make the comparison engine independent of file format so that it receives the same structured field-value contract from every reader.

## References

[1]: ../data/participant/sdoc-hackathon-bundle/README.md "SDOC Hackathon participant bundle README"
[2]: ../data/participant/sdoc-hackathon-bundle/loader.py "SDOC Hackathon participant loader"
