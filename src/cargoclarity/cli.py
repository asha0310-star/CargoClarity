"""Command-line verification helpers for the CargoClarity core."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from .ai_adapter import AIAdapter, AIAdapterError
from .pipeline import process_email_record, process_inline_case


def _fixtures(path: Path) -> int:
    payload = json.loads(path.read_text(encoding="utf-8"))
    failures = 0
    for case in payload["cases"]:
        actual = process_inline_case(case)
        expected = case["expected"]
        keys = ("status", "review_reason", "defect_fields", "has_defect")
        passed = all(actual[key] == expected[key] for key in keys)
        failures += int(not passed)
        print(f"{'PASS' if passed else 'FAIL'} {case['id']}: {actual['status']} {actual['defect_fields']}")
        if not passed:
            print("  expected:", {key: expected[key] for key in keys})
            print("  actual:  ", {key: actual[key] for key in keys})
    print(f"\n{len(payload['cases']) - failures}/{len(payload['cases'])} fixtures passed")
    return 1 if failures else 0


def _email(data_root: Path, email_id: str, use_ai: bool = False) -> int:
    record_path = data_root / "inbox" / f"{email_id}.json"
    if not record_path.exists():
        raise SystemExit(f"Email not found: {record_path}")
    record = json.loads(record_path.read_text(encoding="utf-8"))
    print(json.dumps(process_email_record(record, data_root, use_ai=use_ai), indent=2, ensure_ascii=False))
    return 0


def _ai_check() -> int:
    adapter = AIAdapter()
    if not adapter.enabled:
        print(json.dumps({"enabled": False, "message": "AI is not configured; deterministic fallback is active."}, indent=2))
        return 0
    try:
        result = adapter.classify(
            "Please review these shipment details",
            "The correspondence needs a category before an operator processes it.",
            [],
        )
        print(json.dumps({"enabled": True, "result": result, "calls": [call.to_dict() for call in adapter.calls]}, indent=2))
        return 0
    except AIAdapterError as exc:
        print(json.dumps({"enabled": True, "error": str(exc), "calls": [call.to_dict() for call in adapter.calls]}, indent=2))
        return 1


def main() -> int:
    parser = argparse.ArgumentParser(description="CargoClarity deterministic core with optional AI assistance")
    commands = parser.add_subparsers(dest="command", required=True)

    fixtures = commands.add_parser("fixtures", help="Run the seven Phase 1 regression fixtures")
    fixtures.add_argument("path", type=Path, nargs="?", default=Path("tests/fixtures/phase1_cases.json"))

    email = commands.add_parser("email", help="Process one participant email")
    email.add_argument("email_id", help="Source email ID, for example email_001")
    email.add_argument("--data-root", type=Path, default=Path("data/participant/sdoc-hackathon-bundle"))
    email.add_argument("--use-ai", action="store_true", help="Use the configured AI adapter for ambiguous cases")

    commands.add_parser("ai-check", help="Verify optional AI configuration with a bounded classification call")

    args = parser.parse_args()
    if args.command == "fixtures":
        return _fixtures(args.path)
    if args.command == "email":
        return _email(args.data_root, args.email_id, use_ai=args.use_ai)
    if args.command == "ai-check":
        return _ai_check()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
