"""turn_expects / golden PR fixture 静的検証。"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import yaml
from src.services.e2e_turn_eval import build_turn_expect_map

ALLOWED_EXPECT_KEYS = frozenset({
    "primary_route",
    "diagnosis_kind",
    "must_have_response",
    "must_not",
    "must_not_contain",
    "must_answer",
    "must_answer_question",
    "must_reference_prior",
    "must_not_repeat_prior_bot",
    "context_keywords",
    "min_turns",
    "content_kpi",
    "expects_clarify",
    "min_history_turns_in_prompt",
    "user_goal",
    "active_product",
})


def _turn_count(spec: dict[str, Any]) -> int:
    setup = list(spec.get("setup") or [])
    raw_input = spec.get("input")
    has_input = raw_input is not None and str(raw_input).strip()
    return len(setup) + (1 if has_input else 0)


def validate_turn_expects_doc(blob: dict[str, Any]) -> dict[str, Any]:
    scenarios = list(blob.get("scenarios") or [])
    errors: list[str] = []
    ids: set[str] = set()

    for sc in scenarios:
        sid = str(sc.get("id") or "")
        if not sid:
            errors.append("scenario missing id")
            continue
        if sid in ids:
            errors.append(f"duplicate id: {sid}")
        ids.add(sid)

        total = _turn_count(sc)
        if total == 0:
            errors.append(f"{sid}: no setup/input turns")

        expect_map = build_turn_expect_map(sc)
        for idx, exp in expect_map.items():
            if idx >= total:
                errors.append(f"{sid}: turn_expect turn={idx} >= total_turns={total}")
            unknown = set(exp.keys()) - ALLOWED_EXPECT_KEYS
            if unknown:
                errors.append(f"{sid}: turn {idx} unknown expect keys: {sorted(unknown)}")

        for entry in sc.get("turn_expects") or []:
            if not isinstance(entry, dict):
                errors.append(f"{sid}: turn_expects entry must be dict")
                continue
            if entry.get("turn") is None:
                errors.append(f"{sid}: turn_expects missing turn index")

    return {
        "scenario_count": len(scenarios),
        "errors": errors,
        "ok": not errors,
    }


def validate_turn_expects_file(path: Path) -> dict[str, Any]:
    blob = yaml.safe_load(path.read_text(encoding="utf-8"))
    out = validate_turn_expects_doc(blob)
    out["path"] = str(path)
    return out


def main(argv: list[str] | None = None) -> int:
    import argparse
    import json
    import sys

    parser = argparse.ArgumentParser(description="Validate turn_expects golden YAML")
    parser.add_argument("--path", type=Path, required=True)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    path = args.path.expanduser()
    if not path.is_file():
        print(f"ERROR: missing {path}", file=sys.stderr)
        return 2

    result = validate_turn_expects_file(path)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"Validated {result['scenario_count']} scenarios: {path}")
        for err in result.get("errors") or []:
            print(f"  ERROR: {err}")
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
