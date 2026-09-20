from __future__ import annotations

import json

import pytest

from cargoclarity.ai_adapter import AIAdapter, AISettings, AISchemaError
from cargoclarity.ai_schemas import CLASSIFICATION_SCHEMA
from cargoclarity.pipeline import process_email_record


def _settings():
    return AISettings(enabled=True, api_key="test-key", model="gpt-5-mini")


def test_classification_uses_strict_schema_and_records_metadata():
    captured = {}

    def transport(**kwargs):
        captured.update(kwargs)
        return json.dumps(
            {
                "category": "BL_COMPARISON",
                "confidence": 0.91,
                "signals": ["ambiguous document request"],
                "explanation": "The message requests a draft BL check.",
            }
        )

    adapter = AIAdapter(settings=_settings(), transport=transport)
    result = adapter.classify("Please check the documents", "The draft BL is attached.", ["x_SI.txt", "x_BL.txt"])

    assert result["category"] == "BL_COMPARISON"
    assert captured["response_format"]["json_schema"]["strict"] is True
    assert captured["response_format"]["json_schema"]["schema"] == CLASSIFICATION_SCHEMA
    assert adapter.calls[0].validation_status == "VALIDATED"
    assert adapter.calls[0].operation == "classification"


def test_extraction_rejects_missing_evidence_for_non_null_values():
    def transport(**kwargs):
        return json.dumps(
            {
                "document_role": "BL",
                "role_confidence": 0.9,
                "fields": {
                    field: {
                        "raw_value": "Alpha Paper" if field == "shipper" else None,
                        "evidence_excerpt": None,
                        "confidence": 0.9,
                    }
                    for field in (
                        "shipper",
                        "consignee",
                        "notify_party",
                        "port_of_loading",
                        "port_of_discharge",
                        "container_count",
                        "gross_weight_kg",
                    )
                },
            }
        )

    adapter = AIAdapter(settings=_settings(), transport=transport)
    with pytest.raises(AISchemaError):
        adapter.extract("BILL OF LADING (DRAFT)", "draft.txt", "BL")
    assert adapter.calls[0].validation_status == "FAILED"


def test_valid_extraction_is_schema_validated_and_records_evidence():
    def transport(**kwargs):
        return json.dumps(
            {
                "document_role": "BL",
                "role_confidence": 0.94,
                "fields": {
                    field: {
                        "raw_value": "Alpha Paper" if field == "shipper" else None,
                        "evidence_excerpt": "Shipper: Alpha Paper" if field == "shipper" else None,
                        "confidence": 0.91,
                    }
                    for field in (
                        "shipper",
                        "consignee",
                        "notify_party",
                        "port_of_loading",
                        "port_of_discharge",
                        "container_count",
                        "gross_weight_kg",
                    )
                },
            }
        )

    adapter = AIAdapter(settings=_settings(), transport=transport)
    result = adapter.extract("BILL OF LADING (DRAFT)\nShipper: Alpha Paper", "draft.txt", "BL")

    assert result["document_role"] == "BL"
    assert result["fields"]["shipper"]["evidence_excerpt"] == "Shipper: Alpha Paper"
    assert adapter.calls[0].validation_status == "VALIDATED"


def test_malformed_provider_response_is_safe_and_does_not_become_a_decision():
    def transport(**kwargs):
        return '{"category":"NOT_A_CATEGORY"}'

    adapter = AIAdapter(settings=_settings(), transport=transport)
    with pytest.raises(AISchemaError):
        adapter.classify("subject", "body", [])
    assert adapter.calls[0].error_code == "AISchemaError"


def test_disabled_adapter_is_explicitly_degraded():
    adapter = AIAdapter(settings=AISettings(enabled=False))
    assert adapter.enabled is False
    assert adapter.calls == []


def test_gemini_environment_defaults_are_free_tier_configuration(monkeypatch):
    monkeypatch.setenv("CARGOCLARITY_DISABLE_DOTENV", "1")
    monkeypatch.delenv("AI_PROVIDER", raising=False)
    monkeypatch.delenv("AI_MODEL", raising=False)
    monkeypatch.delenv("AI_API_BASE", raising=False)
    monkeypatch.delenv("AI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini-key")

    settings = AISettings.from_env()

    assert settings.provider == "gemini"
    assert settings.model == "gemini-2.5-flash"
    assert settings.api_base == "https://generativelanguage.googleapis.com/v1beta/openai/"
    assert settings.enabled is True


def test_gemini_does_not_reuse_an_unrelated_openai_key(monkeypatch):
    monkeypatch.setenv("CARGOCLARITY_DISABLE_DOTENV", "1")
    monkeypatch.setenv("AI_PROVIDER", "gemini")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("AI_API_KEY", raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", "unrelated-openai-key")

    settings = AISettings.from_env()

    assert settings.provider == "gemini"
    assert settings.api_key is None
    assert settings.enabled is False


def test_pipeline_keeps_deterministic_result_when_ai_response_is_malformed(tmp_path):
    record = {
        "email_id": "fixture_email",
        "from": "ops@example.com",
        "subject": "Please review shipment details",
        "body": "The attached correspondence needs attention.",
        "attachments": [],
    }

    def transport(**kwargs):
        return '{"category":"NOT_A_CATEGORY"}'

    adapter = AIAdapter(settings=_settings(), transport=transport)
    result = process_email_record(record, tmp_path, use_ai=True, ai_adapter=adapter)

    assert result["category"] == "GENERAL"
    assert result["classification"]["decided_by"] == "RULE"
    assert result["ai_processing"]["fallback_active"] is True
    assert result["ai_processing"]["calls"][0]["validation_status"] == "FAILED"


def test_pipeline_keeps_deterministic_result_when_ai_confidence_is_low(tmp_path):
    record = {
        "email_id": "fixture_email",
        "from": "ops@example.com",
        "subject": "Please review shipment details",
        "body": "The attached correspondence needs attention.",
        "attachments": [],
    }

    def transport(**kwargs):
        return json.dumps(
            {
                "category": "INVOICE_QUERY",
                "confidence": 0.50,
                "signals": ["weak local-model signal"],
                "explanation": "Low-confidence classification.",
            }
        )

    adapter = AIAdapter(settings=_settings(), transport=transport)
    result = process_email_record(record, tmp_path, use_ai=True, ai_adapter=adapter)

    assert result["category"] == "GENERAL"
    assert result["classification"]["decided_by"] == "RULE"
    assert result["ai_processing"]["used"] is True
    assert result["ai_processing"]["fallback_active"] is True
    assert result["ai_processing"]["calls"][0]["validation_status"] == "VALIDATED"
