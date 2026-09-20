"""Field-specific deterministic SI/BL comparison."""
from __future__ import annotations

from difflib import SequenceMatcher
from statistics import mean

from .models import CANONICAL_FIELDS, ComparisonReport, DocumentExtraction, FieldComparison


def _empty_report(reason: str) -> ComparisonReport:
    return ComparisonReport("NEEDS_REVIEW", reason, False, [], 0.0, [])


def _compare_text(field_name: str, left: str, right: str):
    if left == right:
        return "MATCH", 1.0, "normalized_exact", "The normalized values are identical."
    ratio = SequenceMatcher(None, left, right).ratio()
    threshold = 0.985 if field_name in {"port_of_loading", "port_of_discharge"} else 0.965
    if ratio >= threshold:
        return "MATCH", ratio, f"conservative_fuzzy_{field_name}", "The values differ only by a minor formatting variation."
    return "MISMATCH", max(0.80, 1.0 - ratio / 2), "normalized_difference", "The readable normalized values are materially different."


def _compare_numeric(field_name: str, left: int | float, right: int | float):
    if field_name == "gross_weight_kg":
        difference = abs(float(left) - float(right))
        tolerance = max(1.0, max(abs(float(left)), abs(float(right))) * 0.0005)
        if difference <= tolerance:
            return "MATCH", 0.99, "kilogram_tolerance", f"The kilogram values differ by {difference:g}, within the {tolerance:g} kg tolerance."
        return "MISMATCH", 0.98, "kilogram_difference", f"The kilogram values differ by {difference:g}, above the {tolerance:g} kg tolerance."
    if int(left) == int(right):
        return "MATCH", 1.0, "integer_exact", "The parsed container counts are identical."
    return "MISMATCH", 0.99, "integer_difference", "The parsed container counts are different."


def compare_extractions(si: DocumentExtraction | None, bl: DocumentExtraction | None) -> ComparisonReport:
    if si is None or bl is None:
        return _empty_report("missing_attachment")
    if si.readability_status != "READABLE" or bl.readability_status != "READABLE":
        return _empty_report("unreadable")
    if si.document_role != "SI" or bl.document_role != "BL":
        return _empty_report("wrong_doc_type")

    results = []
    for field_name in CANONICAL_FIELDS:
        si_value = si.fields.get(field_name)
        bl_value = bl.fields.get(field_name)
        left = si_value.normalized_value if si_value else None
        right = bl_value.normalized_value if bl_value else None
        if left is None or right is None:
            result, strength, method, explanation = (
                "UNCERTAIN",
                0.0,
                "missing_value",
                "At least one required value is missing or cannot be parsed.",
            )
        elif field_name in {"container_count", "gross_weight_kg"}:
            result, strength, method, explanation = _compare_numeric(field_name, left, right)
        else:
            result, strength, method, explanation = _compare_text(field_name, str(left), str(right))

        source_confidence = min(si_value.confidence if si_value else 0.0, bl_value.confidence if bl_value else 0.0)
        confidence = round(source_confidence * strength, 4)
        results.append(FieldComparison(field_name, result, confidence, method, explanation, si_value, bl_value))

    if any(item.result == "UNCERTAIN" for item in results):
        status, review_reason = "NEEDS_REVIEW", "missing_value"
    elif any(item.result == "MISMATCH" for item in results):
        status, review_reason = "MISMATCH", None
    else:
        status, review_reason = "OK", None

    defect_fields = [item.field_name for item in results if item.result == "MISMATCH"] if status == "MISMATCH" else []
    comparable = [item.confidence for item in results if item.result != "UNCERTAIN"]
    confidence = round(mean(comparable), 4) if comparable else 0.0
    return ComparisonReport(status, review_reason, status == "MISMATCH", defect_fields, confidence, results)
