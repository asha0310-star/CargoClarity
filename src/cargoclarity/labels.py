"""Canonical field-label mapping derived from the participant documents."""
from __future__ import annotations

import re

LABEL_ALIASES = {
    "shipper": ("shipper", "shipper/exporter", "exporter", "shipper principal or seller"),
    "consignee": ("consignee", "consignee non-negotiable", "to the order of", "importer"),
    "notify_party": ("notify", "notify party"),
    "port_of_loading": ("pol", "port of loading", "load port"),
    "port_of_discharge": ("pod", "port of discharge", "discharge port"),
    "container_count": (
        "container count",
        "total containers",
        "total containers or packages",
        "no of containers",
        "no of containers or packages",
        "number of containers",
    ),
    "gross_weight_kg": (
        "gross weight",
        "gross weight kg",
        "gross wt",
        "gross wt kg",
        "gross wt kgs",
        "total gross weight",
        "total gross weight kg",
        "total gross wt",
        "total gross wt kg",
        "total gross wt kgs",
    ),
}


def normalize_label(label: str) -> str:
    value = label.casefold().strip()
    value = re.sub(r"\([^)]*\)", " ", value)
    value = value.replace(".", " ")
    value = re.sub(r"[^a-z0-9/]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


_ALIAS_LOOKUP = {
    normalize_label(alias): canonical
    for canonical, aliases in LABEL_ALIASES.items()
    for alias in aliases
}


def canonicalize_label(label: str) -> str | None:
    return _ALIAS_LOOKUP.get(normalize_label(label))


def split_labeled_line(line: str) -> tuple[str | None, str | None]:
    """Return a canonical field and raw value when a line starts with a known label."""
    stripped = line.strip()
    for delimiter in ("|", ":"):
        if delimiter in stripped:
            left, right = stripped.split(delimiter, 1)
            canonical = canonicalize_label(left)
            if canonical:
                return canonical, right.strip(" |:\t")

    normalized_line = normalize_label(stripped)
    for alias in sorted(_ALIAS_LOOKUP, key=len, reverse=True):
        if normalized_line == alias:
            return _ALIAS_LOOKUP[alias], ""
    return None, None
