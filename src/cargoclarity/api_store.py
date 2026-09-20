"""Small file-backed Phase 4 store for local and hackathon API use.

This is intentionally not the final PostgreSQL layer. It provides durable
local state, repeatable jobs, reviews, and exports without duplicating the
Phase 2/3 processing logic.
"""
from __future__ import annotations

import hashlib
import json
import mimetypes
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .ai_adapter import AIAdapter
from .pipeline import process_email_record
from .readers import read_attachment


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    return value


class StoreError(RuntimeError):
    """Expected API store error."""


class NotFoundError(StoreError):
    """A requested local object does not exist."""


class UnsafeAttachmentError(StoreError):
    """An attachment path is absolute, traverses directories, or leaves the root."""


class ApiStore:
    def __init__(self, data_root: str | Path, state_path: str | Path | None = None, preload: bool = True):
        self.data_root = Path(data_root).resolve()
        self.state_path = Path(state_path).resolve() if state_path else None
        self.records: dict[str, dict] = {}
        self.jobs: dict[str, dict] = {}
        self.batch_jobs: dict[str, dict] = {}
        self.runs: dict[str, list[dict]] = {}
        self.reviews: dict[str, list[dict]] = {}
        self.audit_events: list[dict] = []
        self.lock = threading.RLock()
        self._load_state()
        if preload:
            self.preload_dataset()

    def _load_state(self) -> None:
        if not self.state_path or not self.state_path.exists():
            return
        try:
            payload = json.loads(self.state_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return
        self.jobs = payload.get("jobs", {})
        self.batch_jobs = payload.get("batch_jobs", {})
        self.runs = payload.get("runs", {})
        self.reviews = payload.get("reviews", {})
        self.audit_events = payload.get("audit_events", [])
        for email_id, record in payload.get("records", {}).items():
            self.records[email_id] = record

    def _persist(self) -> None:
        if not self.state_path:
            return
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "records": self.records,
            "jobs": self.jobs,
            "batch_jobs": self.batch_jobs,
            "runs": self.runs,
            "reviews": self.reviews,
            "audit_events": self.audit_events,
        }
        temporary = self.state_path.with_suffix(".tmp")
        temporary.write_text(json.dumps(_json_safe(payload), indent=2), encoding="utf-8")
        temporary.replace(self.state_path)

    def preload_dataset(self) -> None:
        inbox = self.data_root / "inbox"
        if not inbox.exists():
            return
        for path in sorted(inbox.glob("email_*.json")):
            try:
                record = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            email_id = str(record.get("email_id") or path.stem)
            self.records.setdefault(email_id, record)
        with self.lock:
            self._persist()

    @staticmethod
    def _new_id() -> str:
        return str(uuid.uuid4())

    def _record(self, email_id: str) -> dict:
        try:
            return self.records[email_id]
        except KeyError as exc:
            raise NotFoundError(f"Email {email_id} was not found") from exc

    def _attachment_path(self, record: dict, relative_path: str) -> Path:
        candidate = Path(relative_path)
        if candidate.is_absolute() or ".." in candidate.parts:
            raise UnsafeAttachmentError("Attachment path must remain inside the configured data root")
        resolved = (self.data_root / candidate).resolve()
        try:
            resolved.relative_to(self.data_root)
        except ValueError as exc:
            raise UnsafeAttachmentError("Attachment path leaves the configured data root") from exc
        return resolved

    def _attachment_id(self, email_id: str, relative_path: str) -> str:
        return hashlib.sha256(f"{email_id}:{relative_path}".encode("utf-8")).hexdigest()[:24]

    def _attachment_items(self, email_id: str, record: dict) -> list[dict]:
        items = []
        for relative_path in record.get("attachments") or []:
            path = self._attachment_path(record, str(relative_path))
            stat = path.stat() if path.exists() else None
            items.append({
                "id": self._attachment_id(email_id, str(relative_path)),
                "filename": path.name,
                "mime_type": mimetypes.guess_type(path.name)[0] or "application/octet-stream",
                "size_bytes": stat.st_size if stat else 0,
                "readable": bool(stat),
            })
        return items

    def email_view(self, email_id: str) -> dict:
        record = self._record(email_id)
        latest = self.latest_run(email_id)
        comparison = latest.get("result", {}).get("comparison") if latest else None
        review = self.latest_review(email_id)
        machine_status = comparison.get("status") if comparison else None
        latest_view = None
        if latest:
            latest_view = {
                "id": latest["id"],
                "email_id": latest["email_id"],
                "status": latest["status"],
                "stage": "complete" if latest["status"] == "SUCCEEDED" else "failed",
                "progress": 100,
                "completed_at": latest.get("completed_at"),
                "provider": latest.get("provider"),
                "model": latest.get("model"),
            }
        return {
            "id": email_id,
            "source_email_id": email_id,
            "sender": record.get("from") or record.get("sender"),
            "subject": record.get("subject", ""),
            "body": record.get("body", ""),
            "attachments": self._attachment_items(email_id, record),
            "latest_run": latest_view,
            "category": latest.get("result", {}).get("category") if latest else None,
            "status": self.final_status(email_id),
            "machine_status": machine_status,
            "effective_status": self.final_status(email_id),
            "needs_review": self.final_status(email_id) == "NEEDS_REVIEW",
            "review": review,
            "review_count": len(self.reviews.get(email_id) or []),
            "updated_at": latest.get("completed_at") if latest else None,
        }

    def list_views(self, category: str | None = None, status: str | None = None, needs_review: bool | None = None, search: str | None = None) -> list[dict]:
        query = (search or "").casefold()
        views = []
        for email_id in sorted(self.records):
            view = self.email_view(email_id)
            if category and view["category"] != category:
                continue
            if status and view["status"] != status:
                continue
            if needs_review is not None and view["needs_review"] != needs_review:
                continue
            if query and query not in f"{view['subject']} {view['sender']} {view['source_email_id']}".casefold():
                continue
            views.append({
                "id": view["id"],
                "source_email_id": view["source_email_id"],
                "subject": view["subject"],
                "sender": view["sender"],
                "category": view["category"],
                "status": view["status"],
                "machine_status": view["machine_status"],
                "needs_review": view["needs_review"],
                "review_count": view["review_count"],
                "updated_at": view["updated_at"],
            })
        return views

    def create_job(self, email_id: str, use_ai: bool = False) -> dict:
        self._record(email_id)
        job_id = self._new_id()
        now = utc_now()
        job = {
            "id": job_id,
            "email_id": email_id,
            "status": "QUEUED",
            "stage": "queued",
            "progress": 0,
            "use_ai": use_ai,
            "created_at": now,
            "started_at": None,
            "completed_at": None,
            "error_code": None,
            "error_message": None,
            "result": None,
        }
        with self.lock:
            self.jobs[job_id] = job
            self.audit_events.append({"id": self._new_id(), "event_type": "JOB_QUEUED", "email_id": email_id, "created_at": now})
            self._persist()
        return dict(job)

    def run_job(self, job_id: str) -> dict:
        with self.lock:
            job = self.jobs.get(job_id)
            if not job:
                raise NotFoundError(f"Job {job_id} was not found")
            job.update({"status": "RUNNING", "stage": "processing", "progress": 10, "started_at": utc_now()})
            self._persist()
        try:
            record = self._record(job["email_id"])
            adapter = AIAdapter()
            result = process_email_record(record, self.data_root, use_ai=bool(job["use_ai"]), ai_adapter=adapter)
            completed = utc_now()
            run = {
                "id": self._new_id(),
                "email_id": job["email_id"],
                "status": "SUCCEEDED",
                "category": result.get("category"),
                "completed_at": completed,
                "provider": result.get("ai_processing", {}).get("calls", [{}])[-1].get("provider") if result.get("ai_processing", {}).get("calls") else None,
                "model": result.get("ai_processing", {}).get("calls", [{}])[-1].get("model") if result.get("ai_processing", {}).get("calls") else None,
                "result": result,
            }
            with self.lock:
                self.runs.setdefault(job["email_id"], []).append(run)
                job.update({"status": "SUCCEEDED", "stage": "complete", "progress": 100, "completed_at": completed, "result": result})
                self.audit_events.append({"id": self._new_id(), "event_type": "PROCESSING_SUCCEEDED", "email_id": job["email_id"], "job_id": job_id, "created_at": completed})
                self._persist()
            return dict(job)
        except Exception as exc:
            failed = utc_now()
            with self.lock:
                job.update({"status": "FAILED", "stage": "failed", "progress": 100, "completed_at": failed, "error_code": type(exc).__name__, "error_message": str(exc)[:500]})
                self.audit_events.append({"id": self._new_id(), "event_type": "PROCESSING_FAILED", "email_id": job["email_id"], "job_id": job_id, "created_at": failed})
                self._persist()
            return dict(job)

    def _job_view(self, job: dict | None) -> dict | None:
        if not job:
            return None
        return {
            "id": job["id"],
            "email_id": job["email_id"],
            "status": job["status"],
            "stage": job["stage"],
            "progress": job["progress"],
            "use_ai": job["use_ai"],
            "created_at": job["created_at"],
            "started_at": job["started_at"],
            "completed_at": job["completed_at"],
            "error_code": job["error_code"],
            "error_message": job["error_message"],
            "result": job.get("result"),
        }

    def get_job(self, job_id: str) -> dict:
        job = self.jobs.get(job_id)
        if not job:
            raise NotFoundError(f"Job {job_id} was not found")
        return self._job_view(job)

    def create_batch_job(self, force: bool = False, use_ai: bool = False) -> dict:
        email_ids = [email_id for email_id in sorted(self.records) if force or not self.latest_run(email_id)]
        batch_id = self._new_id()
        created_at = utc_now()
        batch = {
            "id": batch_id,
            "status": "QUEUED",
            "stage": "queued",
            "progress": 0,
            "total": len(email_ids),
            "processed": 0,
            "failed": 0,
            "force": force,
            "use_ai": use_ai,
            "email_ids": email_ids,
            "created_at": created_at,
            "started_at": None,
            "completed_at": None,
        }
        with self.lock:
            self.batch_jobs[batch_id] = batch
            self.audit_events.append({"id": self._new_id(), "event_type": "BATCH_QUEUED", "actor_type": "SYSTEM", "batch_id": batch_id, "created_at": created_at, "new_state": {"total": len(email_ids)}})
            self._persist()
        return dict(batch)

    def run_batch(self, batch_id: str) -> dict:
        batch = self.batch_jobs.get(batch_id)
        if not batch:
            raise NotFoundError(f"Batch {batch_id} was not found")
        started_at = utc_now()
        with self.lock:
            batch.update({"status": "RUNNING", "stage": "processing", "started_at": started_at})
            self._persist()
        total = len(batch["email_ids"])
        adapter = AIAdapter()
        for index, email_id in enumerate(batch["email_ids"], start=1):
            try:
                result = process_email_record(self._record(email_id), self.data_root, use_ai=bool(batch["use_ai"]), ai_adapter=adapter)
                completed_at = utc_now()
                calls = result.get("ai_processing", {}).get("calls") or []
                run = {
                    "id": self._new_id(),
                    "email_id": email_id,
                    "status": "SUCCEEDED",
                    "category": result.get("category"),
                    "completed_at": completed_at,
                    "provider": calls[-1].get("provider") if calls else None,
                    "model": calls[-1].get("model") if calls else None,
                    "result": result,
                }
                with self.lock:
                    self.runs.setdefault(email_id, []).append(run)
                    self.audit_events.append({"id": self._new_id(), "event_type": "PROCESSING_SUCCEEDED", "actor_type": "SYSTEM", "email_id": email_id, "batch_id": batch_id, "created_at": completed_at})
            except Exception as exc:
                with self.lock:
                    batch["failed"] += 1
                    self.audit_events.append({"id": self._new_id(), "event_type": "PROCESSING_FAILED", "actor_type": "SYSTEM", "email_id": email_id, "batch_id": batch_id, "created_at": utc_now(), "reason": f"{type(exc).__name__}: {str(exc)[:300]}"})
            with self.lock:
                batch["processed"] = index
                batch["progress"] = 100 if total == 0 else round(index / total * 100)
                if index == total or index % 25 == 0:
                    self._persist()
        completed_at = utc_now()
        with self.lock:
            batch.update({"status": "SUCCEEDED" if batch["failed"] == 0 else "COMPLETED_WITH_ERRORS", "stage": "complete", "progress": 100, "completed_at": completed_at})
            self.audit_events.append({"id": self._new_id(), "event_type": "BATCH_COMPLETED", "actor_type": "SYSTEM", "batch_id": batch_id, "created_at": completed_at, "new_state": {"processed": batch["processed"], "failed": batch["failed"]}})
            self._persist()
        return dict(batch)

    def get_batch(self, batch_id: str) -> dict:
        batch = self.batch_jobs.get(batch_id)
        if not batch:
            raise NotFoundError(f"Batch {batch_id} was not found")
        return {key: value for key, value in batch.items() if key != "email_ids"}

    def latest_run(self, email_id: str) -> dict | None:
        runs = self.runs.get(email_id) or []
        return runs[-1] if runs else None

    def latest_review(self, email_id: str) -> dict | None:
        reviews = self.reviews.get(email_id) or []
        return reviews[-1] if reviews else None

    def final_status(self, email_id: str) -> str | None:
        review = self.latest_review(email_id)
        if review and review.get("corrected_status"):
            return review["corrected_status"]
        latest = self.latest_run(email_id)
        if not latest:
            return None
        result = latest.get("result") or {}
        comparison = result.get("comparison")
        if comparison is not None:
            return comparison.get("status")
        return "OK" if result.get("category") else None

    def comparison(self, email_id: str) -> dict:
        run = self.latest_run(email_id)
        if not run:
            raise NotFoundError(f"Email {email_id} has not been processed")
        result = run.get("result") or {}
        comparison = result.get("comparison")
        if comparison is None:
            return {"email_id": email_id, "category": result.get("category"), "comparison": None, "review": self.latest_review(email_id)}
        return {
            "email_id": email_id,
            "category": result.get("category"),
            "status": self.final_status(email_id),
            "machine_status": comparison.get("status"),
            "review_reason": comparison.get("review_reason"),
            "has_defect": comparison.get("has_defect", False),
            "defect_fields": comparison.get("defect_fields", []),
            "confidence": comparison.get("confidence"),
            "fields": comparison.get("fields", []),
            "processing": {
                "run_id": run["id"],
                "provider": run.get("provider"),
                "model": run.get("model"),
                "completed_at": run.get("completed_at"),
            },
            "review": self.latest_review(email_id),
        }

    def preview(self, email_id: str, attachment_id: str) -> dict:
        record = self._record(email_id)
        for relative_path in record.get("attachments") or []:
            relative_path = str(relative_path)
            if self._attachment_id(email_id, relative_path) != attachment_id:
                continue
            path = self._attachment_path(record, relative_path)
            if not path.exists():
                raise NotFoundError("Attachment file was not found")
            read_result = read_attachment(path)
            return {
                "attachment_id": attachment_id,
                "filename": path.name,
                "parser_name": read_result.parser_name,
                "readability_status": read_result.readability_status,
                "error_code": read_result.error_code,
                "text_excerpt": read_result.text[:4000],
                "tables": read_result.tables[:5],
            }
        raise NotFoundError(f"Attachment {attachment_id} was not found")

    def add_review(self, email_id: str, decision: str, corrected_status: str, corrected_fields: list[dict], reason: str, reviewer_name: str = "Demo Reviewer") -> dict:
        self._record(email_id)
        latest_run = self.latest_run(email_id)
        if not latest_run:
            raise StoreError("Process the email before submitting a review")
        machine_status = (latest_run.get("result", {}).get("comparison") or {}).get("status")
        old_effective_status = self.final_status(email_id)
        clean_reason = reason.strip()
        if decision == "OVERRIDDEN" and len(clean_reason) < 12:
            raise StoreError("An override requires a specific reason of at least 12 characters")
        if decision == "CONFIRMED" and machine_status and corrected_status != machine_status:
            raise StoreError("A confirmed decision must keep the machine status; use OVERRIDDEN to change it")
        if decision == "UNRESOLVED" and corrected_status != "NEEDS_REVIEW":
            raise StoreError("An unresolved decision must keep the case in NEEDS_REVIEW")
        created_at = utc_now()
        review = {
            "id": self._new_id(),
            "email_id": email_id,
            "processing_run_id": latest_run["id"],
            "reviewer_name": reviewer_name.strip(),
            "decision": decision,
            "corrected_status": corrected_status,
            "corrected_fields": corrected_fields,
            "reason": clean_reason,
            "machine_status": machine_status,
            "old_effective_status": old_effective_status,
            "new_effective_status": corrected_status,
            "created_at": created_at,
        }
        audit_event = {
            "id": self._new_id(),
            "event_type": "REVIEW_RECORDED",
            "actor_type": "USER",
            "actor_name": review["reviewer_name"],
            "email_id": email_id,
            "review_id": review["id"],
            "created_at": created_at,
            "prior_state": {"status": old_effective_status, "machine_status": machine_status},
            "new_state": {"status": corrected_status, "decision": decision, "corrected_fields": corrected_fields},
            "reason": clean_reason,
        }
        with self.lock:
            self.reviews.setdefault(email_id, []).append(review)
            self.audit_events.append(audit_event)
            self._persist()
        return {**review, "audit_event_id": audit_event["id"]}

    def audit_log(self, email_id: str | None = None, limit: int = 100) -> list[dict]:
        if email_id is not None:
            self._record(email_id)
        events = [event for event in self.audit_events if email_id is None or event.get("email_id") == email_id]
        events.sort(key=lambda event: event.get("created_at") or "", reverse=True)
        return events[:limit]

    def review_history(self, email_id: str) -> list[dict]:
        self._record(email_id)
        return list(reversed(self.reviews.get(email_id) or []))

    def summary(self) -> dict:
        by_category: dict[str, int] = {}
        by_status: dict[str, int] = {}
        by_review_reason: dict[str, int] = {}
        succeeded = failed = 0
        for email_id in self.records:
            run = self.latest_run(email_id)
            if not run:
                continue
            if run["status"] == "SUCCEEDED":
                succeeded += 1
            else:
                failed += 1
            result = run.get("result") or {}
            category = result.get("category")
            status = self.final_status(email_id)
            reason = result.get("comparison", {}).get("review_reason") if result.get("comparison") else None
            if category:
                by_category[category] = by_category.get(category, 0) + 1
            if status:
                by_status[status] = by_status.get(status, 0) + 1
            if reason:
                by_review_reason[reason] = by_review_reason.get(reason, 0) + 1
        return {
            "total_emails": len(self.records),
            "processed_emails": succeeded + failed,
            "processing": {"succeeded": succeeded, "failed": failed},
            "by_category": by_category,
            "by_status": by_status,
            "by_review_reason": by_review_reason,
            "reviews_recorded": sum(len(items) for items in self.reviews.values()),
            "audit_events": len(self.audit_events),
        }

    def export(self) -> dict:
        output = {}
        for email_id in sorted(self.records):
            latest = self.latest_run(email_id)
            if not latest:
                continue
            result = latest.get("result") or {}
            comparison = result.get("comparison") or {}
            output[email_id] = {
                "category": result.get("category"),
                "status": self.final_status(email_id),
                "review_reason": comparison.get("review_reason"),
                "defect_fields": comparison.get("defect_fields", []),
                "has_defect": comparison.get("has_defect", False),
            }
        return output

    def health(self) -> dict:
        ai = AIAdapter()
        return {
            "status": "ok",
            "version": "1.0.0",
            "dependencies": {
                "data_source": "ok" if self.data_root.exists() else "degraded",
                "runtime_store": "ok",
                "ai": "configured" if ai.enabled else "degraded",
            },
        }
