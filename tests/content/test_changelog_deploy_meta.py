"""CHANGELOG デプロイ表記と詳細フォローアップ。"""
from __future__ import annotations

from src.content.changelog_digest import (
    build_changelog_ui_sections,
    format_changelog_deploy_subtitle,
    load_changelog_digest,
    wants_changelog_detail,
)


def test_format_changelog_deploy_subtitle_date_only(monkeypatch):
    monkeypatch.setattr(
        "src.content.changelog_digest.load_build_meta",
        lambda: {"gitCommitShort": "c1fe06a"},
    )
    subtitle = format_changelog_deploy_subtitle("2026年7月3日（CHANGELOG）")
    assert subtitle == "最終更新日 2026年7月3日"
    assert "c1fe06a" not in subtitle


def test_build_changelog_ui_sections_first_has_commit(monkeypatch):
    monkeypatch.setattr(
        "src.content.changelog_digest.load_build_meta",
        lambda: {"gitCommitShort": "c1fe06a"},
    )
    _, releases = load_changelog_digest(max_releases=2)
    sections = build_changelog_ui_sections(releases, max_releases=2)
    assert sections[0].get("commit") == "c1fe06a"
    assert not sections[1].get("commit")


def test_wants_changelog_detail_after_changelog_card():
    history = [
        {"type": "user", "content": "最近の更新を教えて"},
        {"type": "bot", "concierge_intent": "doc_changelog"},
    ]
    assert wants_changelog_detail("詳しく教えて", history) is True
    assert wants_changelog_detail("頭が痛い", history) is False
