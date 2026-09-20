"""CargoClarity document-verification core and optional AI assistance."""

from .ai_adapter import AIAdapter, AIAdapterError, AISettings
from .classifier import classify_email
from .comparison import compare_extractions
from .extractor import extract_document, identify_document_role
from .pipeline import process_email_record, process_inline_case
from .readers import read_attachment

__all__ = [
    "AIAdapter",
    "AIAdapterError",
    "AISettings",
    "classify_email",
    "compare_extractions",
    "extract_document",
    "identify_document_role",
    "process_email_record",
    "process_inline_case",
    "read_attachment",
]
