from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from cargoclarity.api import create_app

ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = ROOT / "data" / "participant" / "sdoc-hackathon-bundle"


@pytest.fixture
def client(tmp_path):
    app = create_app(data_root=DATA_ROOT, state_path=tmp_path / "api_state.json", preload=False)
    return TestClient(app)


def _email_payload(email_id: str = "email_001"):
    record = json.loads((DATA_ROOT / "inbox" / f"{email_id}.json").read_text(encoding="utf-8"))
    return {
        "source": "participant-test",
        "emails": [
            {
                "source_email_id": record["email_id"],
                "sender": record.get("from", ""),
                "subject": record.get("subject", ""),
                "body": record.get("body", ""),
                "attachments": record.get("attachments", []),
            }
        ],
        "process": True,
        "use_ai": False,
    }


def test_health_and_empty_list(client):
    health = client.get("/api/v1/health")
    assert health.status_code == 200
    assert health.json()["status"] == "ok"

    listing = client.get("/api/v1/emails")
    assert listing.status_code == 200
    assert listing.json() == {"items": [], "page": 1, "page_size": 25, "total": 0}


def test_end_to_end_ingest_process_comparison_preview_review_retry_export(client):
    ingested = client.post("/api/v1/emails/ingest", json=_email_payload())
    assert ingested.status_code == 202
    item = ingested.json()["items"][0]
    assert item["status"] == "QUEUED"
    job_id = item["job_id"]

    job = client.get(f"/api/v1/jobs/{job_id}")
    assert job.status_code == 200
    assert job.json()["status"] == "SUCCEEDED"
    assert job.json()["result"]["category"] == "BL_COMPARISON"

    email = client.get("/api/v1/emails/email_001")
    assert email.status_code == 200
    email_body = email.json()
    assert email_body["source_email_id"] == "email_001"
    assert email_body["status"] == "OK"
    assert len(email_body["attachments"]) == 2

    listing = client.get("/api/v1/emails?category=BL_COMPARISON&status=OK&page_size=10")
    assert listing.status_code == 200
    assert listing.json()["total"] == 1

    comparison = client.get("/api/v1/emails/email_001/comparison")
    assert comparison.status_code == 200
    assert comparison.json()["status"] == "OK"
    assert len(comparison.json()["fields"]) == 7

    attachment_id = email_body["attachments"][0]["id"]
    preview = client.get(f"/api/v1/emails/email_001/attachments/{attachment_id}/preview")
    assert preview.status_code == 200
    assert preview.json()["filename"]
    assert preview.json()["readability_status"] == "READABLE"

    review = client.post(
        "/api/v1/emails/email_001/review",
        json={
            "decision": "CONFIRMED",
            "corrected_status": "OK",
            "corrected_fields": [],
            "reason": "Reviewed the evidence and confirmed the machine result.",
        },
    )
    assert review.status_code == 200
    assert review.json()["decision"] == "CONFIRMED"

    retry = client.post("/api/v1/emails/email_001/retry")
    assert retry.status_code == 202
    retry_job = client.get(f"/api/v1/jobs/{retry.json()['job_id']}")
    assert retry_job.json()["status"] == "SUCCEEDED"

    summary = client.get("/api/v1/reports/summary")
    assert summary.status_code == 200
    assert summary.json()["total_emails"] == 1
    assert summary.json()["reviews_recorded"] == 1

    export = client.get("/api/v1/reports/export?format=json")
    assert export.status_code == 200
    assert export.json()["items"]["email_001"]["status"] == "OK"


def test_process_endpoint_and_review_requires_processing(client):
    ingest = client.post("/api/v1/emails/ingest", json={**_email_payload(), "process": False})
    assert ingest.status_code == 202

    review = client.post(
        "/api/v1/emails/email_001/review",
        json={"decision": "UNRESOLVED", "corrected_status": "NEEDS_REVIEW", "reason": "Needs operator review."},
    )
    assert review.status_code == 409
    assert review.json()["error"]["code"] == "WORKFLOW_ERROR"

    process = client.post("/api/v1/emails/email_001/process", json={"force": True, "use_ai": False})
    assert process.status_code == 202
    job = client.get(f"/api/v1/jobs/{process.json()['job_id']}")
    assert job.json()["status"] == "SUCCEEDED"


def test_validation_missing_email_and_unsafe_attachment(client):
    invalid = client.post("/api/v1/emails/ingest", json={"emails": []})
    assert invalid.status_code == 422
    assert invalid.json()["error"]["code"] == "VALIDATION_ERROR"

    unsafe = client.post(
        "/api/v1/emails/ingest",
        json={
            "emails": [
                {
                    "source_email_id": "unsafe",
                    "sender": "test@example.com",
                    "subject": "test",
                    "body": "test",
                    "attachments": ["../ground_truth.json"],
                }
            ],
            "process": False,
        },
    )
    assert unsafe.status_code == 400
    assert unsafe.json()["error"]["code"] == "UNSAFE_ATTACHMENT_PATH"

    missing = client.get("/api/v1/emails/not-present")
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "NOT_FOUND"


def test_export_rejects_unsupported_format(client):
    response = client.get("/api/v1/reports/export?format=csv")
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "UNSUPPORTED_FORMAT"


def test_phase5_dashboard_is_served_same_origin(client):
    page = client.get("/dashboard/")
    assert page.status_code == 200
    assert "CargoClarity" in page.text
    assert "/dashboard/app.js" in page.text
    assert "/dashboard/styles.css" in page.text

    script = client.get("/dashboard/app.js")
    styles = client.get("/dashboard/styles.css")
    assert script.status_code == 200
    assert styles.status_code == 200
    assert "Prepare demo cases" in script.text
    assert "View evidence" in script.text
    assert ".status-pill.review" in styles.text
