#!/usr/bin/env python3
"""Generate a scorer-compatible CargoClarity submission from participant data."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from cargoclarity.submission import build_and_validate


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, default=Path("data/participant/sdoc-hackathon-bundle"))
    parser.add_argument("--output", type=Path, default=Path("deliverables/cargoclarity-submission.json"))
    parser.add_argument("--use-ai", action="store_true", help="Use configured AI only for ambiguous cases; deterministic fallback remains active.")
    args = parser.parse_args()

    submission, report = build_and_validate(args.data_root, use_ai=args.use_ai)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(submission, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(args.output), **report}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
