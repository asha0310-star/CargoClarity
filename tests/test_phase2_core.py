from __future__ import annotations

import json
from pathlib import Path

import pytest

from cargoclarity.classifier import classify_email
from cargoclarity.labels import canonicalize_label
from cargoclarity.normalizers import normalize_container_count, normalize_party, normalize_port, normalize_weight_kg
from cargoclarity.pipeline import process_email_record, process_inline_case
from cargoclarity.readers import read_attachment

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "participant" / "sdoc-hackathon-bundle"


def test_all_phase1_fixtures_match_expected_outcomes():
    fixture_path = ROOT / "tests" / "fixtures" / "phase1_cases.json"
    payload = json.loads(fixture_path.read_text(encoding="utf-8"))
    assert len(payload["cases"]) == 7
    for case in payload["cases"]:
        actual = process_inline_case(case)
        expected = case["expected"]
        for key in ("status", "review_reason", "defect_fields", "has_defect"):
            assert actual[key] == expected[key], f"{case['id']} failed for {key}"


@pytest.mark.parametrize(
    ("email_id", "category"),
    [
        ("email_038", "BL_COMPARISON"),
        ("email_033", "SI_REQUEST"),
        ("email_048", "INVOICE_QUERY"),
        ("email_070", "GENERAL"),
        ("email_072", "SPAM"),
    ],
)
def test_representative_email_categories(email_id, category):
    record = json.loads((DATA / "inbox" / f"{email_id}.json").read_text(encoding="utf-8"))
    result = classify_email(record)
    assert result.category == category
    assert result.signals
    assert result.decided_by == "RULE"


@pytest.mark.parametrize(
    ("filename", "parser_name"),
    [
        ("email_004_SI.txt", "txt"),
        ("email_059_SI.pdf", "pypdf"),
        ("email_055_BL.docx", "python-docx"),
        ("email_055_SI.xlsx", "openpyxl"),
    ],
)
def test_supported_readers_return_text(filename, parser_name):
    result = read_attachment(DATA / "attachments" / filename)
    assert result.readability_status == "READABLE"
    assert result.parser_name == parser_name
    assert result.text
    assert result.parser_confidence > 0.8


def test_missing_and_unsupported_files_are_typed_failures(tmp_path):
    missing = read_attachment(tmp_path / "missing.txt")
    assert missing.readability_status == "UNREADABLE"
    assert missing.error_code == "MISSING_FILE"

    unsupported_path = tmp_path / "sample.exe"
    unsupported_path.write_bytes(b"not an executable")
    unsupported = read_attachment(unsupported_path)
    assert unsupported.readability_status == "UNSUPPORTED"
    assert unsupported.error_code == "UNSUPPORTED_FORMAT"


def test_label_mapping_and_normalization():
    assert canonicalize_label("Gross Wt (kgs)") == "gross_weight_kg"
    assert canonicalize_label("To the Order of") == "consignee"
    assert normalize_party("Alpha Paper Trading Ltd.") == "ALPHA PAPER TRADING"
    assert normalize_port("Port of Shanghai, China") == "SHANGHAI"
    assert normalize_container_count("6 x 40'HC") == 6
    assert normalize_weight_kg("131,058 KG") == 131058
    assert normalize_weight_kg("220.462 lb") == pytest.approx(100, abs=0.01)


def test_real_clean_txt_pair_processes_end_to_end():
    record = json.loads((DATA / "inbox" / "email_001.json").read_text(encoding="utf-8"))
    output = process_email_record(record, DATA)
    assert output["category"] == "BL_COMPARISON"
    assert output["comparison"]["status"] == "OK"
    assert output["comparison"]["defect_fields"] == []


def test_real_mixed_xlsx_docx_pair_processes_end_to_end():
    record = json.loads((DATA / "inbox" / "email_055.json").read_text(encoding="utf-8"))
    output = process_email_record(record, DATA)
    assert output["category"] == "BL_COMPARISON"
    assert {item["parser_name"] for item in output["attachments"]} == {"openpyxl", "python-docx"}
    assert output["comparison"]["status"] == "OK"


def test_real_pdf_pair_processes_end_to_end():
    record = json.loads((DATA / "inbox" / "email_059.json").read_text(encoding="utf-8"))
    output = process_email_record(record, DATA)
    assert output["category"] == "BL_COMPARISON"
    assert output["comparison"]["status"] == "OK"


def test_real_wrong_document_is_sent_to_review():
    record = json.loads((DATA / "inbox" / "email_501.json").read_text(encoding="utf-8"))
    output = process_email_record(record, DATA)
    assert output["category"] == "BL_COMPARISON"
    assert output["comparison"]["status"] == "NEEDS_REVIEW"
    assert output["comparison"]["review_reason"] == "wrong_doc_type"
