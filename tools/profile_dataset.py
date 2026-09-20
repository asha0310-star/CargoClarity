#!/usr/bin/env python3
"""Profile the participant bundle without reading hidden answer labels."""
from __future__ import annotations

import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path


def load_records(root: Path):
    records = []
    for path in sorted((root / "inbox").glob("email_*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        records.append(data)
    return records


def attachment_extension(path: str) -> str:
    return Path(path).suffix.lower().lstrip(".") or "(none)"


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "data/participant")
    records = load_records(root)
    print(f"records={len(records)}")

    attachment_counts = Counter()
    attachment_email_counts = Counter()
    subjects = []
    for record in records:
        subjects.append((record.get("email_id"), record.get("subject", "")))
        attachments = record.get("attachments") or []
        for attachment in attachments:
            attachment_counts[attachment_extension(attachment)] += 1
        for ext in {attachment_extension(a) for a in attachments}:
            attachment_email_counts[ext] += 1
    print("attachment_files=" + json.dumps(dict(sorted(attachment_counts.items()))))
    print("emails_by_attachment_extension=" + json.dumps(dict(sorted(attachment_email_counts.items()))))
    print("emails_without_attachments=" + str(sum(not (r.get("attachments") or []) for r in records)))

    phrase_groups = {
        "BL_COMPARISON_signals": ["confirm docs", "draft bl", "draft bill", "compare", "bl draft"],
        "SI_REQUEST_signals": ["request si", "si needed", "cust si", "submit si"],
        "INVOICE_QUERY_signals": ["invoice", "billing", "freight", "charges"],
        "GENERAL_signals": ["delivery planning", "update summary", "time off"],
        "SPAM_signals": ["weird trick", "shipping revenue", "unsubscribe"],
    }
    text_by_group = {}
    for group, phrases in phrase_groups.items():
        matches = []
        for email_id, subject in subjects:
            lower = subject.lower()
            if any(p in lower for p in phrases):
                matches.append(email_id)
        text_by_group[group] = matches
    print("subject_signal_candidates=" + json.dumps(text_by_group))

    print("sample_records=")
    for email_id in ["email_038", "email_033", "email_048", "email_070", "email_072"]:
        record = next((r for r in records if r.get("email_id") == email_id), None)
        if record:
            print(json.dumps({
                "email_id": record.get("email_id"),
                "from": record.get("from"),
                "subject": record.get("subject"),
                "attachments": record.get("attachments"),
                "body_preview": re.sub(r"\s+", " ", record.get("body", ""))[:240],
            }, ensure_ascii=False))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
