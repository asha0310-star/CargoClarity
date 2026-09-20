"""Generate and validate scorer-compatible CargoClarity submissions."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .models import CANONICAL_FIELDS, CATEGORIES, OVERALL_STATUSES, REVIEW_REASONS
from .pipeline import process_email_record

SUBMISSION_KEYS = {"category", "status", "review_reason", "defect_fields", "has_defect"}


class SubmissionValidationError(ValueError):
    """Raised when a result cannot be accepted by the participant scorer contract."""


def result_to_submission(result: dict[str, Any]) -> dict[str, Any]:
    comparison = result.get("comparison")
    if comparison is None:
        return {
            "category": result.get("category"),
            "status": "OK",
            "review_reason": None,
            "defect_fields": [],
            "has_defect": False,
        }
    return {
        "category": result.get("category"),
        "status": comparison.get("status"),
        "review_reason": comparison.get("review_reason"),
        "defect_fields": list(comparison.get("defect_fields") or []),
        "has_defect": bool(comparison.get("has_defect", False)),
    }


def build_submission(data_root: str | Path, *, use_ai: bool = False) -> dict[str, dict[str, Any]]:
    root = Path(data_root)
    output: dict[str, dict[str, Any]] = {}
    for path in sorted((root / "inbox").glob("email_*.json")):
        record = json.loads(path.read_text(encoding="utf-8"))
        email_id = str(record.get("email_id") or path.stem)
        result = process_email_record(record, root, use_ai=use_ai)
        output[email_id] = result_to_submission(result)
    return output


def validate_submission(submission: dict[str, Any], sample_submission: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    expected_ids = set(sample_submission)
    actual_ids = set(submission)
    missing_ids = sorted(expected_ids - actual_ids)
    extra_ids = sorted(actual_ids - expected_ids)
    if missing_ids:
        errors.append(f"missing {len(missing_ids)} email IDs")
    if extra_ids:
        errors.append(f"contains {len(extra_ids)} unknown email IDs")

    category_counts: dict[str, int] = {}
    status_counts: dict[str, int] = {}
    review_counts: dict[str, int] = {}
    for email_id, item in submission.items():
        if not isinstance(item, dict):
            errors.append(f"{email_id}: result must be an object")
            continue
        if set(item) != SUBMISSION_KEYS:
            errors.append(f"{email_id}: fields must be exactly {sorted(SUBMISSION_KEYS)}")
            continue
        category = item.get("category")
        status = item.get("status")
        reason = item.get("review_reason")
        fields = item.get("defect_fields")
        has_defect = item.get("has_defect")
        if category not in CATEGORIES:
            errors.append(f"{email_id}: invalid category {category!r}")
        if status not in OVERALL_STATUSES:
            errors.append(f"{email_id}: invalid status {status!r}")
        if reason is not None and reason not in REVIEW_REASONS:
            errors.append(f"{email_id}: invalid review_reason {reason!r}")
        if not isinstance(fields, list) or any(field not in CANONICAL_FIELDS for field in fields):
            errors.append(f"{email_id}: defect_fields must contain only canonical fields")
        if not isinstance(has_defect, bool):
            errors.append(f"{email_id}: has_defect must be boolean")
        if isinstance(fields, list) and has_defect != bool(fields):
            errors.append(f"{email_id}: has_defect must equal bool(defect_fields)")
        if status == "MISMATCH" and not has_defect:
            errors.append(f"{email_id}: MISMATCH requires at least one defect field")
        if status != "MISMATCH" and has_defect:
            errors.append(f"{email_id}: only MISMATCH may report defects")
        if status == "NEEDS_REVIEW" and reason is None:
            errors.append(f"{email_id}: NEEDS_REVIEW requires a review_reason")
        if category != "BL_COMPARISON" and (status != "OK" or reason is not None or fields or has_defect):
            errors.append(f"{email_id}: non-comparison routes must use the neutral OK result")
        category_counts[str(category)] = category_counts.get(str(category), 0) + 1
        status_counts[str(status)] = status_counts.get(str(status), 0) + 1
        if reason:
            review_counts[str(reason)] = review_counts.get(str(reason), 0) + 1

    report = {
        "valid": not errors,
        "record_count": len(submission),
        "expected_count": len(sample_submission),
        "errors": errors,
        "category_counts": dict(sorted(category_counts.items())),
        "status_counts": dict(sorted(status_counts.items())),
        "review_reason_counts": dict(sorted(review_counts.items())),
    }
    if errors:
        raise SubmissionValidationError("; ".join(errors[:10]))
    return report


def build_and_validate(data_root: str | Path, *, use_ai: bool = False) -> tuple[dict[str, Any], dict[str, Any]]:
    root = Path(data_root)
    submission = build_submission(root, use_ai=use_ai)
    sample = json.loads((root / "sample_submission.json").read_text(encoding="utf-8"))
    return submission, validate_submission(submission, sample)
