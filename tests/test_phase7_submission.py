from __future__ import annotations

import json
from pathlib import Path

import pytest

from cargoclarity.submission import (
    SUBMISSION_KEYS,
    SubmissionValidationError,
    build_submission,
    result_to_submission,
    validate_submission,
)

ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = ROOT / "data" / "participant" / "sdoc-hackathon-bundle"


def test_result_to_submission_uses_neutral_output_for_non_comparison_routes():
    item = result_to_submission({"category": "INVOICE_QUERY", "comparison": None})
    assert item == {
        "category": "INVOICE_QUERY",
        "status": "OK",
        "review_reason": None,
        "defect_fields": [],
        "has_defect": False,
    }


def test_complete_participant_submission_matches_exact_schema():
    sample = json.loads((DATA_ROOT / "sample_submission.json").read_text(encoding="utf-8"))
    submission = build_submission(DATA_ROOT)
    report = validate_submission(submission, sample)
    assert report["valid"] is True
    assert report["record_count"] == 520
    assert set(submission) == set(sample)
    assert all(set(item) == SUBMISSION_KEYS for item in submission.values())


def test_submission_validation_rejects_inconsistent_defect_flags():
    sample = {"email_001": {"category": "GENERAL", "status": "OK", "review_reason": None, "defect_fields": [], "has_defect": False}}
    invalid = {"email_001": {"category": "BL_COMPARISON", "status": "MISMATCH", "review_reason": None, "defect_fields": [], "has_defect": False}}
    with pytest.raises(SubmissionValidationError, match="MISMATCH requires"):
        validate_submission(invalid, sample)


def test_submission_validation_rejects_missing_records():
    sample = {
        "email_001": {"category": "GENERAL", "status": "OK", "review_reason": None, "defect_fields": [], "has_defect": False},
        "email_002": {"category": "GENERAL", "status": "OK", "review_reason": None, "defect_fields": [], "has_defect": False},
    }
    candidate = {"email_001": sample["email_001"]}
    with pytest.raises(SubmissionValidationError, match="missing 1 email IDs"):
        validate_submission(candidate, sample)
