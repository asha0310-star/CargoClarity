"""Explicit request contracts for the Phase 4 API."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class IngestEmail(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_email_id: str = Field(min_length=1, max_length=120)
    sender: str = Field(default="", max_length=500)
    subject: str = Field(default="", max_length=5000)
    body: str = Field(default="", max_length=50000)
    attachments: list[str] = Field(default_factory=list, max_length=20)


class IngestRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source: str = Field(default="dataset", min_length=1, max_length=100)
    emails: list[IngestEmail] = Field(min_length=1, max_length=100)
    process: bool = True
    use_ai: bool = False


class ProcessRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    force: bool = False
    parser_version: str = Field(default="phase4-local-v1", max_length=100)
    use_ai: bool = False


class ReviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision: Literal["CONFIRMED", "OVERRIDDEN", "UNRESOLVED"]
    corrected_status: Literal["OK", "MISMATCH", "NEEDS_REVIEW"]
    corrected_fields: list[dict[str, Any]] = Field(default_factory=list, max_length=20)
    reason: str = Field(min_length=1, max_length=2000)


class ErrorBody(BaseModel):
    code: str
    message: str
    request_id: str
