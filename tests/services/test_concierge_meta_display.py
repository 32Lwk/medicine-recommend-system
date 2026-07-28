"""メタ質問表示整形のテスト。"""
from __future__ import annotations

from src.services.concierge_templates import (
    build_agent_roster_items,
    extract_inline_agent_bullets,
    merge_agent_roster_section,
    split_dynamic_body_paragraphs,
    structure_concierge_meta_display,
)


def test_split_long_text_by_sentences():
    text = (
        "このツールはマルチエージェント構成です。"
        "市販薬の候補選定はルールベースです。"
        "フロントエンドはHTML/CSSです。"
    )
    parts = split_dynamic_body_paragraphs(text)
    assert len(parts) >= 3
    assert all(p.endswith("。") for p in parts)


def test_extract_inline_agent_bullets_from_prose():
    text = (
        "内部はマルチエージェント構成で、"
        "・TriageAgent：内容を分類して振り分ける、"
        "・PhysicalOrchestrator：症状を解析して市販薬候補をルールベースで絞る、"
        "・AskAgent：医薬品の質問に答える。"
    )
    prose, bullets = extract_inline_agent_bullets(text)
    assert "TriageAgent" in bullets[0]
    assert len(bullets) == 3
    assert "・" not in prose
    assert "TriageAgent" not in prose


def test_structure_architecture_inline_bullets_into_section():
    text = (
        "返信はAIが生成しています。"
        "内部はマルチエージェント構成で、"
        "・TriageAgent：振り分け、・ConciergeAgent：案内"
    )
    message, sections = structure_concierge_meta_display("architecture", text)
    assert "TriageAgent" not in message
    assert sections and sections[0]["title"] == "担当の役割"
    assert len(sections[0]["items"]) == 2


def test_structure_architecture_bullets_into_section():
    text = (
        "返信はAIが生成しています。\n\n"
        "・TriageAgent：振り分け\n"
        "・ConciergeAgent：案内"
    )
    message, sections = structure_concierge_meta_display("architecture", text)
    assert "返信はAI" in message
    assert sections and sections[0]["title"] == "担当の役割"
    assert any("TriageAgent" in item for item in sections[0]["items"])


def test_structure_preserves_paragraph_breaks():
    text = "1文目です。\n\n2文目です。"
    message, _ = structure_concierge_meta_display("app_about", text)
    assert "\n\n" in message


def test_structure_doc_privacy_keeps_paragraphs():
    text = (
        "プライバシーポリシーは、データの取得と利用目的を定めています。\n\n"
        "利用規約・免責は、試験運用と免責を定めています。\n\n"
        "詳細は画面右上の ℹ️ から各ドキュメントの全文をお読みいただけます。"
    )
    message, sections = structure_concierge_meta_display("doc_privacy", text)
    assert sections == []
    assert "データの取得と利用目的" in message
    assert "試験運用と免責" in message
    assert "ℹ️" in message
