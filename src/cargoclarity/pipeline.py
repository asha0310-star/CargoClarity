"""Deterministic orchestration with optional, schema-validated AI assistance."""
from __future__ import annotations

from pathlib import Path

from .ai_adapter import AIAdapter, AIAdapterError
from .classifier import classify_email
from .comparison import compare_extractions
from .extractor import extract_document, identify_document_role
from .models import (
    CANONICAL_FIELDS,
    ClassificationResult,
    DocumentReadResult,
    ExtractedField,
    TextBlock,
)
from .normalizers import normalize_field
from .readers import read_attachment

AI_CLASSIFICATION_THRESHOLD = 0.78
AI_MIN_ACCEPTED_CLASSIFICATION_CONFIDENCE = 0.75


def _inline_document(document: dict | None) -> DocumentReadResult | None:
    if document is None:
        return None
    text = document.get("text") or ""
    status = document.get("readability_status", "READABLE")
    return DocumentReadResult(
        path=document.get("filename", "inline"),
        filename=document.get("filename", "inline"),
        text_blocks=[TextBlock(text, {"source": "fixture"})] if text else [],
        metadata={"format": document.get("format")},
        readability_status=status,
        parser_name="fixture",
        parser_confidence=1.0 if status == "READABLE" else 0.0,
        error_code=None if status == "READABLE" else "FIXTURE_UNREADABLE",
    )


def process_inline_case(case: dict) -> dict:
    documents = case.get("documents") or {}
    si_read = _inline_document(documents.get("si"))
    bl_read = _inline_document(documents.get("bl"))
    si = extract_document(si_read) if si_read else None
    bl = extract_document(bl_read) if bl_read else None
    report = compare_extractions(si, bl)
    return report.to_dict()


def _filename_hint(filename: str) -> str | None:
    upper = filename.upper()
    if "_SI." in upper:
        return "SI"
    if "_BL." in upper:
        return "BL"
    return None


def _ai_classification(record: dict, deterministic: ClassificationResult, adapter: AIAdapter, use_ai: bool):
    if not use_ai or not adapter.enabled or deterministic.confidence >= AI_CLASSIFICATION_THRESHOLD:
        return deterministic
    try:
        payload = adapter.classify(
            str(record.get("subject") or ""),
            str(record.get("body") or ""),
            [str(item) for item in record.get("attachments") or []],
        )
        ai_confidence = float(payload["confidence"])
        if ai_confidence < AI_MIN_ACCEPTED_CLASSIFICATION_CONFIDENCE:
            return deterministic
        return ClassificationResult(
            category=payload["category"],
            confidence=ai_confidence,
            signals=[f"AI: {signal}" for signal in payload["signals"]],
            decided_by="AI",
            explanation=payload["explanation"],
        )
    except AIAdapterError:
        return deterministic


def _merge_ai_extraction(document, adapter: AIAdapter, use_ai: bool):
    """Use AI only to fill uncertain deterministic fields, never overwrite evidence."""
    if not use_ai or not adapter.enabled or document.readability_status != "READABLE":
        return document
    if document.document_role == "OTHER":
        return document
    missing_fields = [
        field_name
        for field_name in CANONICAL_FIELDS
        if document.fields.get(field_name) is None
        or document.fields[field_name].normalized_value is None
    ]
    if document.document_role != "UNKNOWN" and not missing_fields:
        return document
    try:
        payload = adapter.extract(document_text=document_text(document), filename=document.filename, deterministic_role=document.document_role)
    except AIAdapterError:
        return document

    ai_role = payload["document_role"]
    if document.document_role == "UNKNOWN" and ai_role in {"SI", "BL", "OTHER"}:
        document.document_role = ai_role
        document.role_confidence = float(payload["role_confidence"])

    for field_name in CANONICAL_FIELDS:
        current = document.fields[field_name]
        candidate = payload["fields"][field_name]
        raw_value = candidate["raw_value"]
        evidence = candidate["evidence_excerpt"]
        if current.normalized_value is not None or raw_value is None or not evidence:
            continue
        normalized = normalize_field(field_name, raw_value)
        if normalized is None:
            continue
        document.fields[field_name] = ExtractedField(
            field_name=field_name,
            raw_value=raw_value,
            normalized_value=normalized,
            confidence=min(float(candidate["confidence"]), 0.89),
            evidence_excerpt=evidence[:600],
            evidence_location={"source": "ai", "prompt_version": adapter.settings.prompt_version},
            extraction_method="AI",
        )
    return document


def document_text(document) -> str:
    return "\n".join(block.text for block in document.text_blocks if block.text)[:12000]


def process_email_record(
    record: dict,
    data_root: str | Path,
    *,
    use_ai: bool = False,
    ai_adapter: AIAdapter | None = None,
) -> dict:
    """Classify an email and compare attachments only for BL_COMPARISON records."""
    adapter = ai_adapter or AIAdapter()
    deterministic = classify_email(record)
    calls_before_classification = len(adapter.calls)
    classification = _ai_classification(record, deterministic, adapter, use_ai)
    classification_ai_called = len(adapter.calls) > calls_before_classification
    output = {
        "email_id": record.get("email_id"),
        "category": classification.category,
        "classification": classification.to_dict(),
        "comparison": None,
        "ai_processing": {
            "enabled": bool(use_ai and adapter.enabled),
            "used": classification_ai_called,
            "fallback_active": bool(use_ai and (not adapter.enabled or classification_ai_called and classification.decided_by == "RULE")),
            "calls": [],
        },
    }
    if classification.decided_by == "AI":
        output["ai_processing"]["used"] = True
    if classification.category != "BL_COMPARISON":
        output["ai_processing"]["calls"] = [call.to_dict() for call in adapter.calls]
        output["ai_processing"]["fallback_active"] = bool(
            use_ai
            and (
                not adapter.enabled
                or any(call.validation_status == "FAILED" for call in adapter.calls)
                or (classification_ai_called and classification.decided_by == "RULE")
            )
        )
        return output

    data_root = Path(data_root)
    selected: dict[str, object] = {"SI": None, "BL": None}
    attachment_summaries = []
    for relative_path in record.get("attachments") or []:
        read_result = read_attachment(data_root / relative_path)
        role, role_confidence = identify_document_role(read_result)
        extraction = extract_document(read_result)
        before_calls = len(adapter.calls)
        extraction = _merge_ai_extraction(extraction, adapter, use_ai)
        if len(adapter.calls) > before_calls:
            output["ai_processing"]["used"] = True
        hint = _filename_hint(read_result.filename)
        slot = hint or (role if role in selected else None)
        if slot and selected[slot] is None:
            selected[slot] = extraction
        attachment_summaries.append({
            "filename": read_result.filename,
            "readability_status": read_result.readability_status,
            "parser_name": read_result.parser_name,
            "document_role": extraction.document_role,
            "role_confidence": extraction.role_confidence,
            "error_code": read_result.error_code,
        })

    report = compare_extractions(selected["SI"], selected["BL"])
    output["attachments"] = attachment_summaries
    output["comparison"] = report.to_dict()
    output["ai_processing"]["calls"] = [call.to_dict() for call in adapter.calls]
    output["ai_processing"]["fallback_active"] = bool(
        use_ai
        and (
            not adapter.enabled
            or any(call.validation_status == "FAILED" for call in adapter.calls)
            or (classification_ai_called and classification.decided_by == "RULE")
        )
    )
    return output
