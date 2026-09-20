#!/usr/bin/env python3
"""Run the deterministic core over every participant email without answer labels."""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from cargoclarity.pipeline import process_email_record


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--data-root",
        type=Path,
        default=Path("data/participant/sdoc-hackathon-bundle"),
    )
    args = parser.parse_args()

    categories = Counter()
    statuses = Counter()
    review_reasons = Counter()
    failures = []
    paths = sorted((args.data_root / "inbox").glob("email_*.json"))

    for path in paths:
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
            result = process_email_record(record, args.data_root)
            categories[result["category"]] += 1
            comparison = result.get("comparison")
            if comparison:
                statuses[comparison["status"]] += 1
                if comparison.get("review_reason"):
                    review_reasons[comparison["review_reason"]] += 1
        except Exception as exc:  # smoke runner reports failures and continues
            failures.append({"email_id": path.stem, "error": f"{type(exc).__name__}: {exc}"})

    print(f"processed={len(paths)}")
    print("categories=" + json.dumps(dict(sorted(categories.items()))))
    print("comparison_statuses=" + json.dumps(dict(sorted(statuses.items()))))
    print("review_reasons=" + json.dumps(dict(sorted(review_reasons.items()))))
    print("failures=" + json.dumps(failures))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
