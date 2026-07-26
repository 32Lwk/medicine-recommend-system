#!/usr/bin/env python3
"""Bedrock vs local RAG eval 結果の diff 比較。

Usage:
  .venv/bin/python scripts/compare_rag_eval.py \\
    log/analysis/medicine_kb_bedrock.json \\
    log/analysis/medicine_kb_local.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List


def _load(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _rows_by_id(data: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    rows = data.get("results") or data.get("scenarios") or []
    out: Dict[str, Dict[str, Any]] = {}
    for row in rows:
        rid = str(row.get("id") or "")
        if rid:
            out[rid] = row
    return out


def compare(a_path: Path, b_path: Path) -> int:
    a = _load(a_path)
    b = _load(b_path)
    a_rows = _rows_by_id(a)
    b_rows = _rows_by_id(b)

    improved: List[str] = []
    regressed: List[str] = []
    for rid, a_row in a_rows.items():
        b_row = b_rows.get(rid)
        if not b_row:
            continue
        a_pass = bool(a_row.get("pass"))
        b_pass = bool(b_row.get("pass"))
        if b_pass and not a_pass:
            improved.append(rid)
        elif a_pass and not b_pass:
            regressed.append(rid)

    def _summary(data: Dict[str, Any]) -> str:
        passed = data.get("passed") or data.get("pass_count")
        total = data.get("total") or data.get("scenario_count")
        if passed is not None and total:
            return f"{passed}/{total}"
        rows = data.get("results") or []
        if rows:
            p = sum(1 for r in rows if r.get("pass"))
            return f"{p}/{len(rows)}"
        return "n/a"

    print(f"A ({a_path.name}): {_summary(a)}")
    print(f"B ({b_path.name}): {_summary(b)}")
    print(f"Improved ({len(improved)}): {', '.join(improved) or '-'}")
    print(f"Regressed ({len(regressed)}): {', '.join(regressed) or '-'}")
    return 0 if not regressed else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Compare two RAG eval JSON reports")
    parser.add_argument("baseline", type=Path)
    parser.add_argument("candidate", type=Path)
    args = parser.parse_args()
    return compare(args.baseline, args.candidate)


if __name__ == "__main__":
    raise SystemExit(main())
