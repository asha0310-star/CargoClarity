"""Transparent deterministic email classifier with explainable signals."""
from __future__ import annotations

import re
from collections import defaultdict

from .models import ClassificationResult

_RULES = {
    "SPAM": (
        (r"\bweird trick\b", 8.0, "promotional 'weird trick' phrase"),
        (r"\bcongratulations\b", 4.0, "prize-style language"),
        (r"\bclaim (?:your|a)\b", 3.0, "claim-action language"),
        (r"\bgift card\b", 4.0, "gift-card offer"),
        (r"bit\.ly|unsubscribe", 2.0, "bulk-link signal"),
    ),
    "BL_COMPARISON": (
        (r"\bto confirm docs?\b", 8.0, "document-confirmation subject"),
        (r"\bconfirm (?:the )?(?:si|draft bl|documents?|docs?)\b", 5.0, "document confirmation request"),
        (r"\bdraft bl\b", 5.0, "draft BL phrase"),
        (r"\brequest bl draft\b", 6.0, "BL draft request"),
        (r"\bcompare (?:the )?(?:si|bl|documents?)\b", 5.0, "comparison request"),
    ),
    "SI_REQUEST": (
        (r"\brequest si\b", 8.0, "SI request phrase"),
        (r"\bsi needed\b", 8.0, "SI-needed phrase"),
        (r"\bcust si\b", 7.0, "customer SI phrase"),
        (r"\bsubmit si\b", 7.0, "submit-SI phrase"),
        (r"^\s*(?:re[_:\- ]*)?si\s*[-_]", 5.0, "SI subject pattern"),
        (r"\bshipping instruction\b", 2.0, "shipping-instruction text"),
    ),
    "INVOICE_QUERY": (
        (r"\binvoice\b", 7.0, "invoice phrase"),
        (r"\bbilling\b", 6.0, "billing phrase"),
        (r"\blocal charges?\b", 6.0, "local-charges phrase"),
        (r"\bdetention charges?\b|\bd\s*&\s*d\b", 5.0, "detention-charge phrase"),
        (r"\btotal freight\b", 6.0, "freight-total phrase"),
    ),
    "GENERAL": (
        (r"\bdelivery planning\b", 7.0, "delivery-planning phrase"),
        (r"\bupdate summary\b", 6.0, "update-summary phrase"),
        (r"\btime off\b", 6.0, "administrative message"),
        (r"\bberthing report\b", 4.0, "operations-report phrase"),
    ),
}


def classify_email(record: dict) -> ClassificationResult:
    subject = str(record.get("subject") or "")
    body = str(record.get("body") or "")
    attachments = record.get("attachments") or []
    scores = defaultdict(float)
    signals: dict[str, list[str]] = defaultdict(list)

    for source, text, multiplier in (("subject", subject, 1.0), ("body", body, 0.45)):
        search_text = text.replace("_", " ")
        for category, rules in _RULES.items():
            for pattern, weight, description in rules:
                if re.search(pattern, search_text, flags=re.IGNORECASE):
                    scores[category] += weight * multiplier
                    signals[category].append(f"{source}: {description}")

    names = " ".join(str(path) for path in attachments)
    if re.search(r"_SI\.[A-Za-z0-9]+", names, re.IGNORECASE) and re.search(r"_BL\.[A-Za-z0-9]+", names, re.IGNORECASE):
        scores["BL_COMPARISON"] += 6.0
        signals["BL_COMPARISON"].append("attachments: SI and BL pair")

    if not scores:
        return ClassificationResult("GENERAL", 0.60, ["fallback: no stronger category signal"])

    ranked = sorted(scores.items(), key=lambda item: (-item[1], item[0]))
    category, top_score = ranked[0]
    second_score = ranked[1][1] if len(ranked) > 1 else 0.0
    margin = max(0.0, top_score - second_score)
    confidence = min(0.99, 0.58 + min(top_score, 12.0) / 40.0 + min(margin, 8.0) / 40.0)
    return ClassificationResult(category, round(confidence, 4), signals[category])
