"""Strict JSON Schemas used by the optional Phase 3 AI adapter."""
from __future__ import annotations

from .models import CANONICAL_FIELDS, CATEGORIES


def _nullable_string():
    return {"anyOf": [{"type": "string"}, {"type": "null"}]}


FIELD_SCHEMA = {
    "type": "object",
    "properties": {
        "raw_value": _nullable_string(),
        "evidence_excerpt": _nullable_string(),
        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
    },
    "required": ["raw_value", "evidence_excerpt", "confidence"],
    "additionalProperties": False,
    "allOf": [
        {
            "if": {
                "properties": {"raw_value": {"type": "string"}},
                "required": ["raw_value"],
            },
            "then": {
                "properties": {
                    "evidence_excerpt": {"type": "string", "minLength": 1},
                },
            },
        }
    ],
}

EXTRACTION_SCHEMA = {
    "type": "object",
    "properties": {
        "document_role": {"type": "string", "enum": ["SI", "BL", "OTHER", "UNKNOWN"]},
        "role_confidence": {"type": "number", "minimum": 0, "maximum": 1},
        "fields": {
            "type": "object",
            "properties": {field_name: FIELD_SCHEMA for field_name in CANONICAL_FIELDS},
            "required": list(CANONICAL_FIELDS),
            "additionalProperties": False,
        },
    },
    "required": ["document_role", "role_confidence", "fields"],
    "additionalProperties": False,
}

CLASSIFICATION_SCHEMA = {
    "type": "object",
    "properties": {
        "category": {"type": "string", "enum": list(CATEGORIES)},
        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
        "signals": {"type": "array", "items": {"type": "string"}, "maxItems": 12},
        "explanation": {"type": "string", "maxLength": 500},
    },
    "required": ["category", "confidence", "signals", "explanation"],
    "additionalProperties": False,
}


def response_format(name: str, schema: dict) -> dict:
    """Return the strict OpenAI-compatible response_format object."""
    return {
        "type": "json_schema",
        "json_schema": {
            "name": name,
            "strict": True,
            "schema": schema,
        },
    }
