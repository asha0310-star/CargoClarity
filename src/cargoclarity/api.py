"""Phase 4 FastAPI backend for the CargoClarity workflow."""
from __future__ import annotations

import os
import time
import uuid
from collections import defaultdict, deque
from pathlib import Path
from typing import Any

from fastapi import BackgroundTasks, FastAPI, Query, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from .api_schemas import BatchProcessRequest, IngestRequest, ProcessRequest, ReviewRequest
from .api_store import ApiStore, NotFoundError, StoreError, UnsafeAttachmentError

API_PREFIX = "/api/v1"


def _request_id() -> str:
    return f"req_{uuid.uuid4().hex[:16]}"


def _error(code: str, message: str, request_id: str, http_status: int) -> JSONResponse:
    return JSONResponse(
        status_code=http_status,
        content={"error": {"code": code, "message": message, "request_id": request_id}},
    )


class _RateLimiter:
    """Small in-process limiter for the public synthetic-data prototype."""

    def __init__(self) -> None:
        self.hits: dict[str, deque[float]] = defaultdict(deque)

    def allow(self, key: str, limit: int, window_seconds: int = 60) -> bool:
        now = time.monotonic()
        bucket = self.hits[key]
        while bucket and now - bucket[0] >= window_seconds:
            bucket.popleft()
        if len(bucket) >= limit:
            return False
        bucket.append(now)
        return True


def _default_data_root() -> Path:
    return Path(os.getenv("DATA_SOURCE", "data/participant/sdoc-hackathon-bundle"))


def _default_state_path() -> Path:
    return Path(os.getenv("API_STATE_PATH", ".runtime/api_state.json"))


def _default_dashboard_dir() -> Path:
    configured = os.getenv("DASHBOARD_DIR")
    return Path(configured) if configured else Path(__file__).resolve().parents[2] / "dashboard"


def create_app(
    *,
    data_root: str | Path | None = None,
    state_path: str | Path | None = None,
    preload: bool = True,
) -> FastAPI:
    app = FastAPI(
        title="CargoClarity API",
        version="1.0.0",
        description="Explainable shipping-document verification workflow API",
    )
    limiter = _RateLimiter()
    app.state.store = ApiStore(
        data_root=data_root or _default_data_root(),
        state_path=state_path if state_path is not None else _default_state_path(),
        preload=preload,
    )
    dashboard_dir = _default_dashboard_dir()
    if dashboard_dir.exists():
        app.mount("/dashboard", StaticFiles(directory=dashboard_dir, html=True), name="dashboard")

    @app.middleware("http")
    async def security_and_reliability_headers(request: Request, call_next):
        request_id = _request_id()
        request.state.request_id = request_id
        content_length = request.headers.get("content-length")
        max_body_bytes = int(os.getenv("API_MAX_BODY_BYTES", "1048576"))
        if content_length and int(content_length) > max_body_bytes:
            return _error("PAYLOAD_TOO_LARGE", "Request body exceeds the configured limit.", request_id, 413)
        if request.method == "POST" and any(segment in request.url.path for segment in ("/process", "/retry", "/review", "/ingest")):
            client = request.client.host if request.client else "unknown"
            limit = int(os.getenv("API_MUTATION_RATE_LIMIT", "60"))
            if not limiter.allow(client, limit):
                return _error("RATE_LIMITED", "Too many workflow requests. Try again shortly.", request_id, 429)
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'"
        if request.url.path.startswith(API_PREFIX):
            response.headers["Cache-Control"] = "no-store"
        return response

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, exc: RequestValidationError):
        return _error("VALIDATION_ERROR", "The request is invalid.", request.state.request_id, 422)

    @app.exception_handler(NotFoundError)
    async def not_found_handler(request: Request, exc: NotFoundError):
        return _error("NOT_FOUND", str(exc), request.state.request_id, 404)

    @app.exception_handler(UnsafeAttachmentError)
    async def unsafe_attachment_handler(request: Request, exc: UnsafeAttachmentError):
        return _error("UNSAFE_ATTACHMENT_PATH", str(exc), request.state.request_id, 400)

    @app.exception_handler(StoreError)
    async def store_error_handler(request: Request, exc: StoreError):
        return _error("WORKFLOW_ERROR", str(exc), request.state.request_id, 409)

    @app.get("/", include_in_schema=False)
    async def dashboard_redirect():
        return RedirectResponse(url="/dashboard/", status_code=307)

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

    @app.post(f"{API_PREFIX}/batches/process", status_code=status.HTTP_202_ACCEPTED)
    async def process_batch(payload: BatchProcessRequest, request: Request, background_tasks: BackgroundTasks):
        store: ApiStore = request.app.state.store
        batch = store.create_batch_job(force=payload.force, use_ai=payload.use_ai)
        background_tasks.add_task(store.run_batch, batch["id"])
        return {"batch_id": batch["id"], "status": batch["status"], "total": batch["total"]}

    @app.get(f"{API_PREFIX}/batches/{{batch_id}}")
    async def get_batch(batch_id: str, request: Request):
        return request.app.state.store.get_batch(batch_id)

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
            reviewer_name=payload.reviewer_name,
        )

    @app.get(f"{API_PREFIX}/emails/{{email_id}}/reviews")
    async def review_history(email_id: str, request: Request):
        return {"email_id": email_id, "items": request.app.state.store.review_history(email_id)}

    @app.get(f"{API_PREFIX}/emails/{{email_id}}/audit")
    async def email_audit(email_id: str, request: Request, limit: int = Query(default=100, ge=1, le=500)):
        return {"email_id": email_id, "items": request.app.state.store.audit_log(email_id=email_id, limit=limit)}

    @app.get(f"{API_PREFIX}/audit")
    async def audit_log(request: Request, limit: int = Query(default=100, ge=1, le=500)):
        return {"items": request.app.state.store.audit_log(limit=limit)}

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
            return _error("UNSUPPORTED_FORMAT", "Only JSON export is supported.", request.state.request_id, 400)
        return {"format": "json", "items": request.app.state.store.export()}

    return app


app = create_app()


def main() -> None:
    import uvicorn

    port = os.getenv("PORT") or os.getenv("API_PORT", "8000")
    uvicorn.run(app, host=os.getenv("API_HOST", "127.0.0.1"), port=int(port))


if __name__ == "__main__":
    main()
