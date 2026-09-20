"""Phase 4 FastAPI backend for the CargoClarity workflow."""
from __future__ import annotations

import os
import uuid
from pathlib import Path
from typing import Any

from fastapi import BackgroundTasks, FastAPI, Query, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from .api_schemas import IngestRequest, ProcessRequest, ReviewRequest
from .api_store import ApiStore, NotFoundError, StoreError, UnsafeAttachmentError

API_PREFIX = "/api/v1"


def _request_id() -> str:
    return f"req_{uuid.uuid4().hex[:16]}"


def _error(code: str, message: str, request_id: str, http_status: int) -> JSONResponse:
    return JSONResponse(
        status_code=http_status,
        content={"error": {"code": code, "message": message, "request_id": request_id}},
    )


def _default_data_root() -> Path:
    return Path(os.getenv("DATA_SOURCE", "data/participant/sdoc-hackathon-bundle"))


def _default_state_path() -> Path:
    return Path(os.getenv("API_STATE_PATH", ".runtime/api_state.json"))


def create_app(
    *,
    data_root: str | Path | None = None,
    state_path: str | Path | None = None,
    preload: bool = True,
) -> FastAPI:
    app = FastAPI(
        title="CargoClarity API",
        version="0.4.0",
        description="Explainable shipping-document verification workflow API",
    )
    app.state.store = ApiStore(
        data_root=data_root or _default_data_root(),
        state_path=state_path if state_path is not None else _default_state_path(),
        preload=preload,
    )
    dashboard_dir = Path(__file__).resolve().parents[2] / "dashboard"
    if dashboard_dir.exists():
        app.mount("/dashboard", StaticFiles(directory=dashboard_dir, html=True), name="dashboard")

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, exc: RequestValidationError):
        return _error("VALIDATION_ERROR", "The request is invalid.", _request_id(), 422)

    @app.exception_handler(NotFoundError)
    async def not_found_handler(request: Request, exc: NotFoundError):
        return _error("NOT_FOUND", str(exc), _request_id(), 404)

    @app.exception_handler(UnsafeAttachmentError)
    async def unsafe_attachment_handler(request: Request, exc: UnsafeAttachmentError):
        return _error("UNSAFE_ATTACHMENT_PATH", str(exc), _request_id(), 400)

    @app.exception_handler(StoreError)
    async def store_error_handler(request: Request, exc: StoreError):
        return _error("WORKFLOW_ERROR", str(exc), _request_id(), 409)

    @app.get(f"{API_PREFIX}/health")
    async def health(request: Request):
        return request.app.state.store.health()

    @app.get(f"{API_PREFIX}/emails")
    async def list_emails(
        request: Request,
        category: str | None = None,
        result_status: str | None = Query(default=None, alias="status"),
        needs_review: bool | None = None,
        search: str | None = None,
        page: int = Query(default=1, ge=1),
        page_size: int = Query(default=25, ge=1, le=100),
    ):
        items = request.app.state.store.list_views(category, result_status, needs_review, search)
        start = (page - 1) * page_size
        return {"items": items[start : start + page_size], "page": page, "page_size": page_size, "total": len(items)}

    @app.get(f"{API_PREFIX}/emails/{{email_id}}")
    async def get_email(email_id: str, request: Request):
        return request.app.state.store.email_view(email_id)

    @app.post(f"{API_PREFIX}/emails/ingest", status_code=status.HTTP_202_ACCEPTED)
    async def ingest(payload: IngestRequest, request: Request, background_tasks: BackgroundTasks):
        store: ApiStore = request.app.state.store
        accepted = []
        for item in payload.emails:
            record = {
                "email_id": item.source_email_id,
                "from": item.sender,
                "subject": item.subject,
                "body": item.body,
                "attachments": item.attachments,
            }
            for attachment in item.attachments:
                store._attachment_path(record, attachment)
            store.records[item.source_email_id] = record
            entry: dict[str, Any] = {"email_id": item.source_email_id, "job_id": None, "status": "INGESTED"}
            if payload.process:
                job = store.create_job(item.source_email_id, use_ai=payload.use_ai)
                background_tasks.add_task(store.run_job, job["id"])
                entry.update({"job_id": job["id"], "status": "QUEUED"})
            accepted.append(entry)
        with store.lock:
            store._persist()
        return {"source": payload.source, "items": accepted}

    @app.post(f"{API_PREFIX}/emails/{{email_id}}/process", status_code=status.HTTP_202_ACCEPTED)
    async def process_email(email_id: str, payload: ProcessRequest, request: Request, background_tasks: BackgroundTasks):
        store: ApiStore = request.app.state.store
        job = store.create_job(email_id, use_ai=payload.use_ai)
        background_tasks.add_task(store.run_job, job["id"])
        return {"job_id": job["id"], "email_id": email_id, "status": "QUEUED"}

    @app.get(f"{API_PREFIX}/jobs/{{job_id}}")
    async def get_job(job_id: str, request: Request):
        return request.app.state.store.get_job(job_id)

    @app.get(f"{API_PREFIX}/emails/{{email_id}}/comparison")
    async def get_comparison(email_id: str, request: Request):
        return request.app.state.store.comparison(email_id)

    @app.get(f"{API_PREFIX}/emails/{{email_id}}/attachments/{{attachment_id}}/preview")
    async def preview_attachment(email_id: str, attachment_id: str, request: Request):
        return request.app.state.store.preview(email_id, attachment_id)

    @app.post(f"{API_PREFIX}/emails/{{email_id}}/review")
    async def review_email(email_id: str, payload: ReviewRequest, request: Request):
        return request.app.state.store.add_review(
            email_id=email_id,
            decision=payload.decision,
            corrected_status=payload.corrected_status,
            corrected_fields=payload.corrected_fields,
            reason=payload.reason,
        )

    @app.post(f"{API_PREFIX}/emails/{{email_id}}/retry", status_code=status.HTTP_202_ACCEPTED)
    async def retry_email(email_id: str, request: Request, background_tasks: BackgroundTasks):
        store: ApiStore = request.app.state.store
        job = store.create_job(email_id, use_ai=False)
        background_tasks.add_task(store.run_job, job["id"])
        return {"job_id": job["id"], "email_id": email_id, "status": "QUEUED", "retry": True}

    @app.get(f"{API_PREFIX}/reports/summary")
    async def report_summary(request: Request):
        return request.app.state.store.summary()

    @app.get(f"{API_PREFIX}/reports/export")
    async def report_export(request: Request, format: str = "json"):
        if format.casefold() != "json":
            return _error("UNSUPPORTED_FORMAT", "Only JSON export is supported in Phase 4.", _request_id(), 400)
        return {"format": "json", "items": request.app.state.store.export()}

    return app


app = create_app()


def main() -> None:
    import uvicorn

    uvicorn.run(app, host=os.getenv("API_HOST", "127.0.0.1"), port=int(os.getenv("API_PORT", "8000")))


if __name__ == "__main__":
    main()
