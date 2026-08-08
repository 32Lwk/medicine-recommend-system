#!/usr/bin/env python3
"""PR 用 E2E コーパス YAML の構造・品質検証（HTTP / app.py 不要）。"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import yaml

from src.analysis.e2e_corpus_builder import (
    DEFAULT_BUCKET_QUOTAS,
    is_valid_user_turn,
)

DEFAULT_CORPUS = PROJECT_ROOT / "tests" / "fixtures" / "v2_e2e_corpus_pr500.yaml"


def validate_corpus(path: Path, *, expected_total: int = 500) -> dict:
    blob = yaml.safe_load(path.read_text(encoding="utf-8"))
    scenarios = list(blob.get("scenarios") or [])
    errors: list[str] = []

    if int(blob.get("count") or 0) != len(scenarios):
        errors.append(f"count mismatch: header={blob.get('count')} actual={len(scenarios)}")

    if len(scenarios) != expected_total:
        errors.append(f"expected {expected_total} scenarios, got {len(scenarios)}")

    ids: set[str] = set()
    buckets: Counter[str] = Counter()
    for sc in scenarios:
        sid = str(sc.get("id") or "")
        if not sid:
            errors.append("scenario missing id")
            continue
        if sid in ids:
            errors.append(f"duplicate id: {sid}")
        ids.add(sid)

        bucket = str(sc.get("category") or "unknown")
        buckets[bucket] += 1

        for field in ("input",):
            text = str(sc.get(field) or "")
            if not is_valid_user_turn(text):
                errors.append(f"{sid}: invalid user input")
        for turn in sc.get("setup") or []:
            if not is_valid_user_turn(str(turn)):
                errors.append(f"{sid}: invalid setup turn")

        if not (sc.get("expect") or {}).get("must_have_response", True):
            errors.append(f"{sid}: must_have_response expected")

    for bucket, target in DEFAULT_BUCKET_QUOTAS.items():
        if buckets.get(bucket, 0) != target:
            errors.append(
                f"bucket quota mismatch {bucket}: got {buckets.get(bucket, 0)} want {target}"
            )

    return {
        "path": str(path),
        "scenario_count": len(scenarios),
        "bucket_counts": dict(buckets),
        "errors": errors,
        "ok": not errors,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate PR E2E corpus YAML")
    parser.add_argument(
        "--corpus",
        type=Path,
        default=DEFAULT_CORPUS,
    )
    parser.add_argument("--total", type=int, default=500)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    path = args.corpus.expanduser()
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    if not path.is_file():
        print(f"ERROR: missing {path}", file=sys.stderr)
        return 2

    result = validate_corpus(path, expected_total=args.total)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"Validated {result['scenario_count']} scenarios in {path}")
        print(f"  buckets={result['bucket_counts']}")
        if result["errors"]:
            for err in result["errors"][:20]:
                print(f"  ERROR: {err}")
            if len(result["errors"]) > 20:
                print(f"  ... and {len(result['errors']) - 20} more")

    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
