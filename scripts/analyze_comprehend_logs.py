#!/usr/bin/env python3
"""CloudWatch / S3 エクスポート jsonl から Comprehend Medical エンティティを集計。"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path


def _iter_records(path: Path):
    text = path.read_text(encoding="utf-8")
    if path.suffix == ".jsonl":
        for line in text.splitlines():
            line = line.strip()
            if line:
                yield json.loads(line)
        return
    data = json.loads(text)
    if isinstance(data, list):
        for row in data:
            yield row
    else:
        yield data


def _extract_comprehend(payload: dict) -> list[dict]:
    cm = payload.get("comprehend_medical")
    if isinstance(cm, dict):
        return list(cm.get("entities") or [])
    msg = str(payload.get("message") or payload.get("textPayload") or "")
    match = re.search(r"comprehend_medical[^\{]*(\{.*\})", msg)
    if match:
        try:
            parsed = json.loads(match.group(1))
            return list(parsed.get("entities") or [])
        except json.JSONDecodeError:
            return []
    return []


def main() -> int:
    parser = argparse.ArgumentParser(description="Aggregate Comprehend Medical entities from logs")
    parser.add_argument("inputs", nargs="+", help="json / jsonl log export files")
    parser.add_argument("--top", type=int, default=20)
    args = parser.parse_args()

    counter: Counter[str] = Counter()
    total = 0
    for pattern in args.inputs:
        for path in sorted(Path(".").glob(pattern)) if "*" in pattern else [Path(pattern)]:
            if not path.is_file():
                continue
            for row in _iter_records(path):
                entities = _extract_comprehend(row if isinstance(row, dict) else {})
                for ent in entities:
                    key = f"{ent.get('category')}:{ent.get('type')}:{ent.get('text')}"
                    counter[key] += 1
                    total += 1

    print(f"entities_total={total}")
    for key, count in counter.most_common(args.top):
        print(f"{count}\t{key}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
