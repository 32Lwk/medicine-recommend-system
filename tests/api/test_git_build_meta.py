"""Git ビルドメタデータ（オンボーディング最終更新日・コミット）の解決テスト。"""
import json
from pathlib import Path

import main


def test_resolve_git_commit_from_baked_meta(tmp_path, monkeypatch):
    meta_path = tmp_path / "static" / "build-meta.json"
    meta_path.parent.mkdir(parents=True)
    meta_path.write_text(
        json.dumps({"gitCommitShort": "abc1234", "gitCommitDateIso": "2026-06-22"}),
        encoding="utf-8",
    )
    monkeypatch.setattr(main, "_BAKED_BUILD_META", None)
    monkeypatch.setattr(main, "Path", lambda *a, **k: meta_path if a and a[0] == main.__file__ else Path(*a, **k))
    # Path(__file__).parent を tmp に差し替える
    monkeypatch.setattr(
        main,
        "_load_baked_build_meta",
        lambda: json.loads(meta_path.read_text(encoding="utf-8")),
    )
    monkeypatch.delenv("GIT_COMMIT", raising=False)
    monkeypatch.delenv("GIT_COMMIT_DATE", raising=False)
    monkeypatch.setenv("APP_VERSION", "")

    assert main._resolve_git_commit_short() == "abc1234"
    assert main._resolve_git_commit_date_iso() == "2026-06-22"


def test_resolve_git_commit_date_from_env(monkeypatch):
    monkeypatch.setattr(main, "_BAKED_BUILD_META", {})
    monkeypatch.setenv("GIT_COMMIT_DATE", "2026-06-18T12:00:00+09:00")
    assert main._resolve_git_commit_date_iso() == "2026-06-18"


def test_baked_meta_used_when_git_unavailable(monkeypatch):
    monkeypatch.setattr(main, "_BAKED_BUILD_META", {
        "gitCommitShort": "deadbee",
        "gitCommitDateIso": "2026-06-18",
    })
    monkeypatch.setattr(main, "_git_repo_available", lambda: False)
    monkeypatch.delenv("GIT_COMMIT", raising=False)
    monkeypatch.delenv("GIT_COMMIT_DATE", raising=False)
    assert main._resolve_git_commit_short() == "deadbee"
    assert main._resolve_git_commit_date_iso() == "2026-06-18"
