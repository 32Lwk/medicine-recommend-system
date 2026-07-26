#!/usr/bin/env python3
"""Docker ビルド時に Git メタデータを static/build-meta.json に書き込む。"""
from __future__ import annotations

import json
import os
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

_HEX_COMMIT_RE = re.compile(r"^[0-9a-f]{7,40}$", re.IGNORECASE)


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


def _looks_like_commit(value: str) -> bool:
    return bool(_HEX_COMMIT_RE.match((value or "").strip()))


def _normalize_date(value: str | None) -> str:
    raw = (value or "").strip()[:10]
    if len(raw) == 10 and raw[4] == "-" and raw[7] == "-":
        return raw
    return ""


def _resolve_from_git(repo_root: Path, commit_ref: str = "HEAD") -> tuple[str, str]:
    if not (repo_root / ".git").exists():
        return "", ""
    try:
        commit_result = subprocess.run(
            ["git", "rev-parse", "--short=7", commit_ref],
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        date_result = subprocess.run(
            ["git", "log", "-1", "--format=%ci", commit_ref],
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        commit = (commit_result.stdout or "").strip() if commit_result.returncode == 0 else ""
        date_raw = (date_result.stdout or "").strip() if date_result.returncode == 0 else ""
        date = _normalize_date(date_raw.split()[0] if date_raw else "")
        if _looks_like_commit(commit):
            return commit[:7], date
    except (OSError, subprocess.SubprocessError):
        pass
    return "", ""


def resolve_build_meta(
    repo_root: Path | None = None,
    existing: dict[str, str] | None = None,
) -> dict[str, str]:
    root = repo_root or Path(__file__).resolve().parent.parent
    meta = dict(existing or {})

    commit = (os.environ.get("GIT_COMMIT") or os.environ.get("COMMIT_SHA") or "").strip()
    date = _normalize_date(os.environ.get("GIT_COMMIT_DATE") or os.environ.get("COMMIT_DATE"))
    commit_changed = False

    if not _looks_like_commit(commit):
        git_commit, git_date = _resolve_from_git(root)
        if git_commit:
            commit = git_commit
        if not date and git_date:
            date = git_date
    elif not date:
        _, git_date = _resolve_from_git(root, commit if len(commit) >= 7 else "HEAD")
        if git_date:
            date = git_date

    if _looks_like_commit(commit):
        short = commit[:7]
        commit_changed = meta.get("gitCommitShort") != short
        meta["gitCommitShort"] = short

    if date:
        meta["gitCommitDateIso"] = date
    elif meta.get("gitCommitShort"):
        _, git_date = _resolve_from_git(root, meta["gitCommitShort"])
        if git_date:
            meta["gitCommitDateIso"] = git_date
        elif commit_changed or not meta.get("gitCommitDateIso"):
            meta["gitCommitDateIso"] = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    return meta


def main() -> None:
    out = Path(__file__).resolve().parent.parent / "static" / "build-meta.json"
    meta = resolve_build_meta(existing=_load_existing_meta(out))
    if not meta:
        return
    out.write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
