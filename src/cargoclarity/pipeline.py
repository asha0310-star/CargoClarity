"""Deterministic orchestration for inline fixtures and participant emails."""
from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

from .classifier import classify_email
from .comparison import compare_extractions
from .extractor import extract_document, identify_document_role
from .models import DocumentReadResult, TextBlock
from .readers import read_attachment


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


def process_email_record(record: dict, data_root: str | Path) -> dict:
    """Classify an email and compare attachments only for BL_COMPARISON records."""
    classification = classify_email(record)
    output = {
        "email_id": record.get("email_id"),
        "category": classification.category,
        "classification": classification.to_dict(),
        "comparison": None,
    }
    if classification.category != "BL_COMPARISON":
        return output

    data_root = Path(data_root)
    selected: dict[str, object] = {"SI": None, "BL": None}
    attachment_summaries = []
    for relative_path in record.get("attachments") or []:
        read_result = read_attachment(data_root / relative_path)
        role, role_confidence = identify_document_role(read_result)
        extraction = extract_document(read_result)
        hint = _filename_hint(read_result.filename)
        slot = hint or (role if role in selected else None)
        if slot and selected[slot] is None:
            selected[slot] = extraction
        attachment_summaries.append({
            "filename": read_result.filename,
            "readability_status": read_result.readability_status,
            "parser_name": read_result.parser_name,
            "document_role": role,
            "role_confidence": role_confidence,
            "error_code": read_result.error_code,
        })

    report = compare_extractions(selected["SI"], selected["BL"])
    output["attachments"] = attachment_summaries
    output["comparison"] = report.to_dict()
    return output
