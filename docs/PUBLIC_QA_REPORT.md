# CargoClarity 1.0 — Public Browser QA Report

**QA date:** 20 September 2026  
**Release commit tested:** `7026d0c`  
**Environment:** Fresh sandbox browser and isolated Linux installation from the clean release archive

## Result

The complete product passed the public-browser acceptance path. The application root redirected to the dashboard, the real participant inbox loaded all 520 messages, and the navigation, queue controls, filters, process actions, evidence drawer, review workbench, audit trail, reports, and submission export were present and usable.

The redesigned interface uses a compact dark header, quiet navigation rail, single summary strip, dense operational tables, restrained typography, and explicit status semantics. It avoids decorative gradients, generic illustrations, oversized cards, and unnecessary animation. Browser automation's yellow/red numbered outlines in screenshots are inspection overlays and are not part of the product.

## Fresh-state verification

The first fresh-browser load displayed 520 inbox messages, zero processed messages, zero review cases, and zero confirmed defects. AI assistance displayed **Degraded** because no Gemini-specific key was configured. This was correct even though the host had an unrelated OpenAI environment variable, proving provider credentials are isolated.

## Complete-inbox verification

The **Verify inbox** action processed the full participant bundle. The progress banner advanced while the batch ran and disappeared after completion. The final server and UI results were:

| Measure | Result |
|---|---:|
| Participant messages | 520 |
| Successfully processed | 520 |
| Processing failures | 0 |
| OK | 335 |
| Mismatch | 31 |
| Needs review | 154 |

## Decision and evidence verification

The `email_001` decision record displayed an `OK` result, distinct machine and effective statuses, all seven canonical fields, side-by-side SI and BL values, normalized values, comparison methods, confidence, explanations, source documents, and evidence actions.

Opening field evidence displayed the exact SI excerpt and BL excerpt, raw and normalized values, extraction methods, confidence, and deterministic decision basis in a side drawer.

## Review and audit verification

The Review queue initially exposed an API-page limit during browser QA. The product was corrected to retrieve and combine all pages. A fresh browser then displayed **154 cases awaiting review**, matching the navigation and report totals.

A disposable `UNRESOLVED` decision was recorded for `email_003` under reviewer `Release QA`. The effective status remained `NEEDS_REVIEW`, the immutable machine status remained `NEEDS_REVIEW`, the email review count became one, and the audit event preserved the actor, prior state, new state, timestamp, and rationale.

## Reporting verification

The Operations report displayed 520/520 coverage, 520 successful jobs, zero failures, one disposable QA review, 523 audit events, all five routing categories, all three outcomes, all four review reasons, and 520/520 submission readiness. The submission-download action was enabled.

## Security and runtime verification

The public release returned version `1.0.0`, unique `X-Request-ID` headers, `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, a same-origin Content Security Policy, payload limits, and mutation rate limiting. The deployed release contained no `.env`, answer key, scorer file, organizer bundle, or persisted local development state.

## Public URL

The QA deployment is available at:

<https://8765-iyvhsdsyl34bxmbdg85s9-44c7dae6.sg2.manus.computer/>

This URL is a temporary sandbox demonstration, not a durable production deployment. Use `render.yaml` and the Phase 8 guide for a persistent public service.
