"""Field-specific value normalization for deterministic comparison."""
from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation

MISSING_MARKERS = {"", "-", "--", "n/a", "na", "none", "null", "tba", "tbd", "unknown", "not available"}
LEGAL_SUFFIXES = {
    "CO", "COMPANY", "CORP", "CORPORATION", "FZE", "GMBH", "INC", "INCORPORATED",
    "LLC", "LTD", "LIMITED", "PTE", "PTY", "SDN", "BHD", "PLC",
}
COUNTRY_SUFFIXES = {
    "AUSTRALIA", "CHINA", "INDONESIA", "MALAYSIA", "MYANMAR", "NIGERIA", "PAKISTAN",
    "PERU", "SINGAPORE", "SOUTH KOREA", "TURKEY", "UAE", "UNITED ARAB EMIRATES", "US", "USA",
}


def clean_text(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = re.sub(r"\s+", " ", str(value)).strip()
    return None if cleaned.casefold() in MISSING_MARKERS else cleaned


def normalize_party(value: str | None) -> str | None:
    cleaned = clean_text(value)
    if not cleaned:
        return None
    tokens = re.findall(r"[A-Z0-9]+", cleaned.upper())
    tokens = [token for token in tokens if token not in LEGAL_SUFFIXES]
    return " ".join(tokens) or None


def normalize_port(value: str | None) -> str | None:
    cleaned = clean_text(value)
    if not cleaned:
        return None
    normalized = cleaned.upper()
    normalized = re.sub(r"\(([A-Z]{5})\)\s*$", " ", normalized)
    normalized = re.sub(r"\bPORT\s+OF\b", " ", normalized)
    parts = [part.strip() for part in normalized.split(",") if part.strip()]
    if len(parts) > 1 and parts[-1] in COUNTRY_SUFFIXES:
        parts.pop()
    normalized = " ".join(parts)
    normalized = re.sub(r"[^A-Z0-9/]+", " ", normalized)
    return re.sub(r"\s+", " ", normalized).strip() or None


def normalize_container_count(value: str | None) -> int | None:
    cleaned = clean_text(value)
    if not cleaned:
        return None
    match = re.search(r"\b(\d+)\b", cleaned.replace(",", ""))
    return int(match.group(1)) if match else None


def normalize_weight_kg(value: str | None) -> int | float | None:
    cleaned = clean_text(value)
    if not cleaned:
        return None
    match = re.search(r"(?<![A-Z0-9])(-?\d[\d,]*(?:\.\d+)?)", cleaned.upper())
    if not match:
        return None
    try:
        amount = Decimal(match.group(1).replace(",", ""))
    except InvalidOperation:
        return None
    upper = cleaned.upper()
    if re.search(r"\b(LB|LBS|POUND|POUNDS)\b", upper):
        amount *= Decimal("0.45359237")
    elif re.search(r"\b(MT|TONNE|TONNES|METRIC TON|METRIC TONS)\b", upper):
        amount *= Decimal("1000")
    amount = amount.quantize(Decimal("0.001")).normalize()
    return int(amount) if amount == amount.to_integral() else float(amount)


def normalize_field(field_name: str, value: str | None):
    if field_name in {"shipper", "consignee", "notify_party"}:
        return normalize_party(value)
    if field_name in {"port_of_loading", "port_of_discharge"}:
        return normalize_port(value)
    if field_name == "container_count":
        return normalize_container_count(value)
    if field_name == "gross_weight_kg":
        return normalize_weight_kg(value)
    return clean_text(value)
