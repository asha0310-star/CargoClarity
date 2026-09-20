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
    assert health.json()["version"] == "1.0.0"
    assert health.headers["x-content-type-options"] == "nosniff"
    assert health.headers["x-frame-options"] == "DENY"
    assert health.headers["x-request-id"].startswith("req_")

    listing = client.get("/api/v1/emails")
    assert listing.status_code == 200
    assert listing.json() == {"items": [], "page": 1, "page_size": 25, "total": 0}


def test_root_redirects_to_product_dashboard(client):
    response = client.get("/", follow_redirects=False)
    assert response.status_code == 307
    assert response.headers["location"] == "/dashboard/"


def test_oversized_request_is_rejected_before_parsing(client, monkeypatch):
    monkeypatch.setenv("API_MAX_BODY_BYTES", "10")
    response = client.post("/api/v1/emails/ingest", content=b'{"emails": []}')
    assert response.status_code == 413
    assert response.json()["error"]["code"] == "PAYLOAD_TOO_LARGE"


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
    assert review.json()["reviewer_name"] == "Demo Reviewer"
    assert review.json()["old_effective_status"] == "OK"
    assert review.json()["new_effective_status"] == "OK"
    assert review.json()["audit_event_id"]

    history = client.get("/api/v1/emails/email_001/reviews")
    assert history.status_code == 200
    assert history.json()["items"][0]["reason"].startswith("Reviewed the evidence")

    audit = client.get("/api/v1/emails/email_001/audit")
    assert audit.status_code == 200
    review_event = next(item for item in audit.json()["items"] if item["event_type"] == "REVIEW_RECORDED")
    assert review_event["actor_name"] == "Demo Reviewer"
    assert review_event["prior_state"]["status"] == "OK"
    assert review_event["new_state"]["status"] == "OK"

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


def test_override_requires_specific_reason_and_preserves_machine_output(client):
    client.post("/api/v1/emails/ingest", json=_email_payload())
    rejected = client.post(
        "/api/v1/emails/email_001/review",
        json={"decision": "OVERRIDDEN", "corrected_status": "MISMATCH", "reason": "wrong"},
    )
    assert rejected.status_code == 409

    accepted = client.post(
        "/api/v1/emails/email_001/review",
        json={
            "decision": "OVERRIDDEN",
            "corrected_status": "MISMATCH",
            "reason": "The visible BL source value differs from the SI reference.",
            "reviewer_name": "Operations Reviewer",
        },
    )
    assert accepted.status_code == 200
    comparison = client.get("/api/v1/emails/email_001/comparison").json()
    assert comparison["machine_status"] == "OK"
    assert comparison["status"] == "MISMATCH"


def test_batch_processes_all_unprocessed_records(client):
    client.post("/api/v1/emails/ingest", json={**_email_payload("email_001"), "process": False})
    client.post("/api/v1/emails/ingest", json={**_email_payload("email_016"), "process": False})
    accepted = client.post("/api/v1/batches/process", json={"force": False, "use_ai": False})
    assert accepted.status_code == 202
    assert accepted.json()["total"] == 2
    batch = client.get(f"/api/v1/batches/{accepted.json()['batch_id']}")
    assert batch.status_code == 200
    assert batch.json()["status"] == "SUCCEEDED"
    assert batch.json()["processed"] == 2
    assert batch.json()["failed"] == 0
    assert client.get("/api/v1/reports/summary").json()["processed_emails"] == 2


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
    assert "verifyInbox" in script.text
    assert "openFieldEvidence" in script.text
    assert "loadAudit" in script.text
    assert ".review-workbench" in styles.text
