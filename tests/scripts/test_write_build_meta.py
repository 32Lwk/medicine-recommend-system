"""write_build_meta.py のテスト。"""
from __future__ import annotations

import json
import runpy
import subprocess
from pathlib import Path

from scripts.write_build_meta import resolve_build_meta


def _run_write_meta(root: Path, monkeypatch) -> Path:
    scripts_dir = root / "scripts"
    scripts_dir.mkdir(parents=True, exist_ok=True)
    static_dir = root / "static"
    static_dir.mkdir(parents=True, exist_ok=True)
    script = Path(__file__).resolve().parents[2] / "scripts" / "write_build_meta.py"
    (scripts_dir / "write_build_meta.py").write_text(
        script.read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    monkeypatch.chdir(root)
    runpy.run_path(str(scripts_dir / "write_build_meta.py"), run_name="__main__")
    return static_dir / "build-meta.json"


def test_write_build_meta_preserves_existing_without_env(tmp_path, monkeypatch):
    meta_path = tmp_path / "static" / "build-meta.json"
    meta_path.parent.mkdir(parents=True)
    meta_path.write_text(
        json.dumps({"gitCommitShort": "abc1234", "gitCommitDateIso": "2026-06-18"}),
        encoding="utf-8",
    )
    monkeypatch.delenv("GIT_COMMIT", raising=False)
    monkeypatch.delenv("COMMIT_SHA", raising=False)
    monkeypatch.delenv("GIT_COMMIT_DATE", raising=False)

    out = _run_write_meta(tmp_path, monkeypatch)
    saved = json.loads(out.read_text(encoding="utf-8"))
    assert saved["gitCommitShort"] == "abc1234"
    assert saved["gitCommitDateIso"] == "2026-06-18"


def test_write_build_meta_overwrites_with_env(tmp_path, monkeypatch):
    meta_path = tmp_path / "static" / "build-meta.json"
    meta_path.parent.mkdir(parents=True)
    meta_path.write_text(
        json.dumps({"gitCommitShort": "old1234", "gitCommitDateIso": "2026-01-01"}),
        encoding="utf-8",
    )
    monkeypatch.setenv("GIT_COMMIT", "a1b2c3d4e5f6789")
    monkeypatch.setenv("GIT_COMMIT_DATE", "2026-06-22")

    out = _run_write_meta(tmp_path, monkeypatch)
    saved = json.loads(out.read_text(encoding="utf-8"))
    assert saved["gitCommitShort"] == "a1b2c3d"
    assert saved["gitCommitDateIso"] == "2026-06-22"


def test_resolve_build_meta_from_git(tmp_path, monkeypatch):
    monkeypatch.delenv("GIT_COMMIT", raising=False)
    monkeypatch.delenv("COMMIT_SHA", raising=False)
    monkeypatch.delenv("GIT_COMMIT_DATE", raising=False)

    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    sample = tmp_path / "sample.txt"
    sample.write_text("hello", encoding="utf-8")
    subprocess.run(["git", "add", "sample.txt"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "-c", "user.email=test@example.com", "-c", "user.name=Test User", "commit", "-m", "init"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )

    meta = resolve_build_meta(repo_root=tmp_path)
    assert len(meta["gitCommitShort"]) == 7
    assert meta["gitCommitDateIso"]


def test_resolve_build_meta_updates_date_when_commit_env_only(tmp_path, monkeypatch):
    monkeypatch.delenv("GIT_COMMIT_DATE", raising=False)
    monkeypatch.setenv("GIT_COMMIT", "deadbeef1234567890abcdef1234567890abcd")

    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    sample = tmp_path / "sample.txt"
    sample.write_text("hello", encoding="utf-8")
    subprocess.run(["git", "add", "sample.txt"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "-c", "user.email=test@example.com", "-c", "user.name=Test User", "commit", "-m", "init"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )

    meta = resolve_build_meta(
        repo_root=tmp_path,
        existing={"gitCommitShort": "old1234", "gitCommitDateIso": "2026-01-01"},
    )
    assert meta["gitCommitShort"] == "deadbee"
    assert meta["gitCommitDateIso"] != "2026-01-01"
