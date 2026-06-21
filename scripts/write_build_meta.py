#!/usr/bin/env python3
"""Docker ビルド時に Git メタデータを static/build-meta.json に書き込む。"""
import json
import os
from pathlib import Path


def main() -> None:
    commit = (os.environ.get("GIT_COMMIT") or "").strip()
    date = (os.environ.get("GIT_COMMIT_DATE") or "").strip()[:10]
    meta: dict[str, str] = {}
    if len(commit) >= 7:
        meta["gitCommitShort"] = commit[:7]
    if len(date) == 10 and date[4] == "-" and date[7] == "-":
        meta["gitCommitDateIso"] = date
    if not meta:
        return
    out = Path(__file__).resolve().parent.parent / "static" / "build-meta.json"
    out.write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
