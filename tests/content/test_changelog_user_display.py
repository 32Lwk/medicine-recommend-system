"""プロンプト流出除去と CHANGELOG UI セクション。"""
from __future__ import annotations

from src.content.changelog_digest import (
    build_changelog_ui_sections,
    load_changelog_digest,
    overview_to_user_bullets,
    _soften_for_user_display,
)
from src.utils.sage_message_plain import strip_concierge_prompt_leakage


def test_strip_concierge_prompt_leakage_removes_meta():
    leaked = (
        "・提供された「CHANGELOG 要約」には、直近の更新内容の記載がありません。\n"
        "・記載にない変更は推測で補わないよう指定されています。\n\n"
        "最近は相談の流れをわかりやすく整えています。"
    )
    cleaned = strip_concierge_prompt_leakage(leaked)
    assert "CHANGELOG" not in cleaned
    assert "推測で補わない" not in cleaned
    assert "相談の流れ" in cleaned


def test_overview_to_user_bullets_user_friendly():
    ov = (
        "ブランチ main に、処理中ステータスマスコットの段階別アニメーション、"
        "チャットビューポートとシーズン装飾のレイヤー修正、オンボーディングスライドの文言刷新を実装。"
    )
    items = overview_to_user_bullets(ov, max_items=3)
    assert items
    assert not any("src/" in i for i in items)
    assert not any("CHANGELOG.md" in i for i in items)
    assert any("処理中" in i or "表示" in i for i in items)


def test_build_changelog_ui_sections_uses_overview_not_file_paths():
    _, releases = load_changelog_digest(max_releases=1)
    sections = build_changelog_ui_sections(releases, max_releases=1)
    assert sections
    joined = " ".join(sections[0]["items"])
    assert "static/" not in joined
    assert "doc_changelog" not in joined.lower()


def test_soften_filters_dev_paths():
    raw = "src/content/changelog_digest.py: CHANGELOG.md から抽出"
    assert _soften_for_user_display(raw) == ""
