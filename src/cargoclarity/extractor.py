"""Document-role detection and deterministic seven-field extraction."""
from __future__ import annotations

import re

from .labels import split_labeled_line
from .models import CANONICAL_FIELDS, DocumentExtraction, DocumentReadResult, ExtractedField
from .normalizers import normalize_field

_PARTY_FIELDS = {"shipper", "consignee", "notify_party"}
_STOP_HEADINGS = re.compile(
    r"^(?:VESSEL|VOY(?:AGE)?|COMMODITY|DESCRIPTION OF GOODS|HS CODE|BOOKING|OC NO|FREIGHT|B/L|BILL OF LADING NO)",
    re.IGNORECASE,
)


def identify_document_role(document: DocumentReadResult) -> tuple[str, float]:
    text = document.text.upper()[:4000]
    filename = document.filename.upper()

    if document.readability_status != "READABLE":
        return "UNKNOWN", 0.0
    if any(heading in text for heading in ("COMMERCIAL INVOICE", "PACKING LIST", "CERTIFICATE OF ORIGIN")):
        return "OTHER", 0.99
    if "BILL OF LADING (DRAFT)" in text or "DRAFT BILL OF LADING" in text:
        return "BL", 0.99
    if any(heading in text for heading in ("SHIPPING INSTRUCTION", "BILL OF LADING INSTRUCTION", "BL INSTRUCTION")):
        return "SI", 0.97
    if re.search(r"_SI\.[A-Z0-9]+$", filename):
        return "SI", 0.65
    if re.search(r"_BL\.[A-Z0-9]+$", filename):
        return "BL", 0.65
    return "UNKNOWN", 0.20


def _flatten_lines(document: DocumentReadResult):
    for block_index, block in enumerate(document.text_blocks, start=1):
        for line_index, line in enumerate(block.text.splitlines() or [block.text], start=1):
            text = line.strip()
            if text:
                yield text, {**block.location, "block": block_index, "line": line_index}


def extract_document(document: DocumentReadResult) -> DocumentExtraction:
    role, role_confidence = identify_document_role(document)
    extraction = DocumentExtraction(
        filename=document.filename,
        document_role=role,
        role_confidence=role_confidence,
        readability_status=document.readability_status,
        parser_name=document.parser_name,
        parser_confidence=document.parser_confidence,
        error_code=document.error_code,
    )
    if document.readability_status != "READABLE":
        return extraction

    lines = list(_flatten_lines(document))
    for index, (line, location) in enumerate(lines):
        field_name, inline_value = split_labeled_line(line)
        if not field_name or field_name in extraction.fields:
            continue

        parts = [inline_value] if inline_value else []
        if field_name in _PARTY_FIELDS:
            for next_line, _next_location in lines[index + 1:index + 4]:
                next_field, _ = split_labeled_line(next_line)
                if next_field or _STOP_HEADINGS.match(next_line):
                    break
                parts.append(next_line)
        elif not inline_value and index + 1 < len(lines):
            next_line, _next_location = lines[index + 1]
            next_field, _ = split_labeled_line(next_line)
            if not next_field and not _STOP_HEADINGS.match(next_line):
                parts.append(next_line)

        raw_value = " ".join(part.strip() for part in parts if part and part.strip()).strip() or None
        normalized_value = normalize_field(field_name, raw_value)
        if raw_value is not None and normalized_value is None and raw_value.casefold() not in {"tba", "tbd", "n/a", "na", "unknown"}:
            continue
        confidence = min(0.99, 0.78 + 0.20 * document.parser_confidence) if normalized_value is not None else 0.20
        extraction.fields[field_name] = ExtractedField(
            field_name=field_name,
            raw_value=raw_value,
            normalized_value=normalized_value,
            confidence=round(confidence, 4),
            evidence_excerpt=line if not raw_value else f"{line.split(':', 1)[0]}: {raw_value}"[:600],
            evidence_location=location,
        )

    for field_name in CANONICAL_FIELDS:
        extraction.fields.setdefault(
            field_name,
            ExtractedField(
                field_name=field_name,
                raw_value=None,
                normalized_value=None,
                confidence=0.0,
                evidence_excerpt=None,
                evidence_location={},
            ),
        )
    return extraction
