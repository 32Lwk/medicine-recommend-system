#!/usr/bin/env python3
"""E2E コーパス expect / turn_expects 付与（ルール自動 + 任意 LLM 草案）。"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import yaml

from src.analysis.e2e_corpus_builder import _infer_rule_turn_expects, infer_e2e_bucket


def enrich_scenarios(scenarios: list[dict], *, overwrite: bool = False) -> tuple[list[dict], dict]:
    stats = {"enriched": 0, "skipped": 0}
    out: list[dict] = []
    for sc in scenarios:
        row = dict(sc)
        if row.get("turn_expects") and not overwrite:
            stats["skipped"] += 1
            out.append(row)
            continue
        setup = list(row.get("setup") or [])
        user_input = str(row.get("input") or "")
        bucket = str(row.get("category") or infer_e2e_bucket(user_input, setup=setup))
        turn_expects = _infer_rule_turn_expects(bucket, setup, user_input)
        if turn_expects:
            row["turn_expects"] = turn_expects
            stats["enriched"] += 1
        out.append(row)
    return out, stats


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Enrich E2E corpus with turn_expects")
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    in_path = args.input if args.input.is_absolute() else PROJECT_ROOT / args.input
    blob = yaml.safe_load(in_path.read_text(encoding="utf-8"))
    scenarios = list(blob.get("scenarios") or [])
    enriched, stats = enrich_scenarios(scenarios, overwrite=args.overwrite)
    blob["scenarios"] = enriched
    blob["count"] = len(enriched)

    out_path = args.output or in_path
    if not out_path.is_absolute():
        out_path = PROJECT_ROOT / out_path
    out_path.write_text(yaml.safe_dump(blob, allow_unicode=True, sort_keys=False), encoding="utf-8")

    if args.json:
        print(json.dumps({"path": str(out_path), **stats}, ensure_ascii=False, indent=2))
    else:
        print(f"Wrote {out_path}: enriched={stats['enriched']} skipped={stats['skipped']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
