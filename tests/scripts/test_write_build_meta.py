"""write_build_meta.py のテスト。"""
from __future__ import annotations

import json
import runpy
from pathlib import Path


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
    monkeypatch.setenv("GIT_COMMIT", "new5678deadbeef")
    monkeypatch.setenv("GIT_COMMIT_DATE", "2026-06-22")

    out = _run_write_meta(tmp_path, monkeypatch)
    saved = json.loads(out.read_text(encoding="utf-8"))
    assert saved["gitCommitShort"] == "new5678"
    assert saved["gitCommitDateIso"] == "2026-06-22"
