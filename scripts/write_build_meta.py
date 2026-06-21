#!/usr/bin/env python3
"""Docker ビルド時に Git メタデータを static/build-meta.json に書き込む。"""
import json
import os
from datetime import datetime, timezone
from pathlib import Path


def _load_existing_meta(path: Path) -> dict[str, str]:
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return {k: str(v) for k, v in data.items() if v is not None}
    except (OSError, json.JSONDecodeError, TypeError):
        pass
    return {}


def main() -> None:
    out = Path(__file__).resolve().parent.parent / "static" / "build-meta.json"
    meta = _load_existing_meta(out)

    commit = (os.environ.get("GIT_COMMIT") or os.environ.get("COMMIT_SHA") or "").strip()
    date = (os.environ.get("GIT_COMMIT_DATE") or os.environ.get("COMMIT_DATE") or "").strip()[:10]

    if len(commit) >= 7:
        meta["gitCommitShort"] = commit[:7]

    has_valid_env_date = len(date) == 10 and date[4] == "-" and date[7] == "-"
    if has_valid_env_date:
        meta["gitCommitDateIso"] = date
    elif not meta.get("gitCommitDateIso") and meta.get("gitCommitShort"):
        meta["gitCommitDateIso"] = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    if not meta:
        return
    out.write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
