"""プロンプト流出除去と CHANGELOG UI セクション。"""
from __future__ import annotations

from src.content.changelog_digest import (
    build_changelog_ui_sections,
    load_changelog_digest,
    overview_to_user_bullets,
    sanitize_changelog_intro_for_user,
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


def test_build_changelog_ui_sections_positive_user_facing():
    _, releases = load_changelog_digest(max_releases=2)
    sections = build_changelog_ui_sections(releases, max_releases=2)
    assert sections
    joined = " ".join(item for sec in sections for item in sec["items"])
    assert "PMDA live fetch" not in joined
    assert "data/pmda" not in joined
    assert ".env" not in joined.lower()
    assert "static/" not in joined
    assert "Medicine eval" not in joined


def test_build_changelog_ui_sections_default_caps_at_three_items():
    _, releases = load_changelog_digest(max_releases=4)
    sections = build_changelog_ui_sections(releases, max_releases=4, detailed=False)
    assert sections
    assert len(sections[0]["items"]) <= 3


def test_pmda_overview_rewrites_to_user_friendly():
    ov = (
        "PMDA live fetch の添付文書 HTML を data/pmda/raw/ に永続化（680 件）。"
        "§マーカー空白不一致・全文フォールバック・merge バグを修正し、raw から正本 CSV を再生成。"
    )
    items = overview_to_user_bullets(ov, max_items=3)
    assert items
    joined = " ".join(items)
    assert "PMDA" not in joined
    assert "data/" not in joined
    assert "§" not in joined
    assert "相互作用" in joined or "公的" in joined


def test_soften_filters_dev_paths():
    raw = "src/content/changelog_digest.py: CHANGELOG.md から抽出"
    assert _soften_for_user_display(raw) == ""


def test_build_changelog_ui_sections_filters_ingestion_job_noise():
    from src.content.changelog_digest import _keep_user_facing_bullet

    assert _keep_user_facing_bullet("相互作用・副作用の案内がより信頼しやすくなりました")
    assert not _keep_user_facing_bullet("ingestion job OG6SSAO4QN COMPLETE")
    _, releases = load_changelog_digest(max_releases=2)
    sections = build_changelog_ui_sections(releases, max_releases=2)
    joined = " ".join(item for sec in sections for item in sec["items"])
    assert "ingestion job" not in joined.lower()
    assert "OG6SSAO4QN" not in joined


def test_sanitize_changelog_intro_removes_pmda_dev_terms():
    leaked = (
        "最近の更新では、PMDA 正本の反映や品質フィルタの強化が進み、"
        "より正確にご案内できるようになりました。"
        "あわせて、更新内容の表示も見直し、全体としてより使いやすくなりました。"
    )
    cleaned = sanitize_changelog_intro_for_user(leaked)
    assert "PMDA" not in cleaned
    assert "正本" not in cleaned
    assert "品質フィルタ" not in cleaned
    assert "使いやすく" in cleaned or "アップデート" in cleaned


def test_sanitize_changelog_intro_removes_meta_ui_dev_talk():
    _, releases = load_changelog_digest(max_releases=1)
    leaked = (
        "最近の更新では、医薬品情報の反映精度がさらに整い、より使いやすくなりました。"
        "画面の「最近の更新」も、開発者向けの情報をできるだけ減らして、見やすい表示に整えています。"
        "あわせて、更新の確認や案内の流れも、より安心して使える形になりました。"
    )
    cleaned = sanitize_changelog_intro_for_user(
        leaked,
        header_date="2026年7月24日",
        releases=releases,
    )
    assert "開発者向け" not in cleaned
    assert "反映精度" not in cleaned
    assert "最近の更新」も" not in cleaned
    assert "アップデート" in cleaned or "改善" in cleaned or "使いやす" in cleaned
