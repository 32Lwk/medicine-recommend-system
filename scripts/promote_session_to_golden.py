#!/usr/bin/env python3
"""本番 aligned セッション → golden PR YAML 草案生成。"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import yaml

from src.analysis.e2e_corpus_builder import _infer_rule_turn_expects, infer_e2e_bucket, sanitize_user_text


def _load_report(path: Path) -> list[dict]:
    blob = json.loads(path.read_text(encoding="utf-8"))
    return list(blob.get("results") or [])


def promote_from_report(
    report_path: Path,
    *,
    min_judge_grade: str = "aligned",
    limit: int = 10,
) -> list[dict]:
    rows = _load_report(report_path)
    promoted: list[dict] = []
    for row in rows:
        if not row.get("auto_pass"):
            continue
        turn_evals = row.get("turn_evals") or []
        grades = [str((te.get("judge") or {}).get("grade") or "") for te in turn_evals if te.get("judge")]
        if grades and min_judge_grade == "aligned" and not all(g == "aligned" for g in grades):
            continue
        turns = row.get("turns") or []
        if len(turns) < 1:
            continue
        setup = [sanitize_user_text(str(t.get("user_message") or "")) for t in turns[:-1]]
        user_input = sanitize_user_text(str(turns[-1].get("user_message") or ""))
        bucket = infer_e2e_bucket(user_input, setup=setup)
        spec = {
            "id": f"promoted-{row.get('scenario_id', 'session')}"[:48],
            "category": bucket,
            "wave": "golden-promoted",
            "description": f"Promoted from {row.get('scenario_id')} session {row.get('session_id')}",
            "setup": setup or None,
            "input": user_input,
            "expect": {"must_have_response": True},
            "turn_expects": _infer_rule_turn_expects(bucket, setup, user_input),
            "meta": {"source_session_id": row.get("session_id"), "source_scenario": row.get("scenario_id")},
        }
        if not spec.get("setup"):
            spec.pop("setup", None)
        promoted.append(spec)
        if len(promoted) >= limit:
            break
    return promoted


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Promote aligned sessions to golden YAML draft")
    parser.add_argument("--report", type=Path, required=True, help="local_v2_chat_test JSON report")
    parser.add_argument("--output", type=Path, default=PROJECT_ROOT / "log" / "analysis" / "golden_promoted_draft.yaml")
    parser.add_argument("--limit", type=int, default=10)
    args = parser.parse_args(argv)

    report = args.report if args.report.is_absolute() else PROJECT_ROOT / args.report
    promoted = promote_from_report(report, limit=args.limit)
    out = {
        "version": 2,
        "source": f"promoted-from-{report.name}",
        "count": len(promoted),
        "scenarios": promoted,
    }
    out_path = args.output if args.output.is_absolute() else PROJECT_ROOT / args.output
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(yaml.safe_dump(out, allow_unicode=True, sort_keys=False), encoding="utf-8")
    print(f"Wrote {len(promoted)} promoted scenarios to {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
