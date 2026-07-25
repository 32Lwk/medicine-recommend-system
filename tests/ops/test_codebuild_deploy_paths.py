"""Tests for CodeBuild deploy path classification."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "lib"))

from codebuild_deploy_paths import (  # noqa: E402
    classify_changed_files,
    full_sync_plan,
    resolve_changed_files,
)


def test_backend_only_skips_static_and_kb():
    plan = classify_changed_files(
        [
            "src/handlers/chat/chat_stream.py",
            "tests/chat/test_chat_stream_api.py",
        ]
    )
    assert plan.needs_static_sync is False
    assert plan.needs_kb_sync is False
    assert plan.changed_files is not None


def test_static_change_requires_static_sync():
    plan = classify_changed_files(["static/css/main.css"])
    assert plan.needs_static_sync is True
    assert plan.needs_kb_sync is False


def test_data_change_requires_kb_sync():
    plan = classify_changed_files(["data/otc_catalog.csv"])
    assert plan.needs_kb_sync is True
    assert plan.needs_static_sync is False


def test_changelog_requires_kb_sync():
    plan = classify_changed_files(["CHANGELOG.md"])
    assert plan.needs_kb_sync is True


def test_kb_script_change_requires_kb_sync():
    plan = classify_changed_files(["scripts/sync-all-kb-to-s3.sh"])
    assert plan.needs_kb_sync is True


def test_mixed_change_requires_both():
    plan = classify_changed_files(
        ["static/js/app.js", "docs/concierge/technical/README.md"]
    )
    assert plan.needs_static_sync is True
    assert plan.needs_kb_sync is True


def test_full_sync_fallback_is_safe():
    plan = full_sync_plan("unknown_changes_fallback")
    assert plan.changed_files is None
    assert plan.needs_static_sync is True
    assert plan.needs_kb_sync is True


def test_git_diff_detection_in_repo():
    plan = resolve_changed_files(str(ROOT))
    assert plan.detection in {
        "git_or_api",
        "unknown_changes_fallback",
        "forced_full",
    }


def test_forced_full_sync_env(monkeypatch):
    monkeypatch.setenv("DEPLOY_FORCE_FULL_SYNC", "true")
    plan = resolve_changed_files(str(ROOT))
    assert plan.detection == "forced_full"
    assert plan.needs_static_sync is True
    assert plan.needs_kb_sync is True


def test_emit_env_cli():
    proc = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "lib" / "codebuild_deploy_paths.py"),
            "--emit-env",
            str(ROOT),
        ],
        capture_output=True,
        text=True,
        check=False,
        env={**os.environ, "DEPLOY_FORCE_FULL_SYNC": "true"},
    )
    assert proc.returncode == 0
    assert "export DEPLOY_NEEDS_STATIC_SYNC=true" in proc.stdout
    assert "export DEPLOY_CHANGED_FILES_KNOWN=false" in proc.stdout
