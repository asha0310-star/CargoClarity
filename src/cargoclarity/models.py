"""Typed data contracts shared by the deterministic core."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

CANONICAL_FIELDS = (
    "shipper",
    "consignee",
    "notify_party",
    "port_of_loading",
    "port_of_discharge",
    "container_count",
    "gross_weight_kg",
)

CATEGORIES = ("BL_COMPARISON", "SI_REQUEST", "INVOICE_QUERY", "GENERAL", "SPAM")
FIELD_RESULTS = ("MATCH", "MISMATCH", "UNCERTAIN")
OVERALL_STATUSES = ("OK", "MISMATCH", "NEEDS_REVIEW")
REVIEW_REASONS = ("wrong_doc_type", "missing_attachment", "unreadable", "missing_value")


@dataclass
class TextBlock:
    text: str
    location: dict[str, Any] = field(default_factory=dict)


@dataclass
class DocumentReadResult:
    path: str
    filename: str
    text_blocks: list[TextBlock] = field(default_factory=list)
    tables: list[list[list[str]]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    readability_status: str = "UNREADABLE"
    parser_name: str = "unknown"
    parser_confidence: float = 0.0
    error_code: str | None = None

    @property
    def text(self) -> str:
        return "\n".join(block.text for block in self.text_blocks if block.text).strip()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ClassificationResult:
    category: str
    confidence: float
    signals: list[str]
    decided_by: str = "RULE"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ExtractedField:
    field_name: str
    raw_value: str | None
    normalized_value: str | int | float | None
    confidence: float
    evidence_excerpt: str | None
    evidence_location: dict[str, Any]
    extraction_method: str = "RULE"


@dataclass
class DocumentExtraction:
    filename: str
    document_role: str
    role_confidence: float
    readability_status: str
    parser_name: str
    parser_confidence: float
    fields: dict[str, ExtractedField] = field(default_factory=dict)
    error_code: str | None = None


@dataclass
class FieldComparison:
    field_name: str
    result: str
    confidence: float
    comparison_method: str
    explanation: str
    si: ExtractedField | None
    bl: ExtractedField | None


@dataclass
class ComparisonReport:
    status: str
    review_reason: str | None
    has_defect: bool
    defect_fields: list[str]
    confidence: float
    fields: list[FieldComparison]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
