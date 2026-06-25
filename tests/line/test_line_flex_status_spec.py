"""LINE status Flex スペック解決のテスト。"""
from __future__ import annotations

from unittest.mock import MagicMock

from src.agents.concierge_agent import build_concierge_payload
from src.handlers.line.flex_messages import build_line_messages_from_bot_message
from src.handlers.line.flex_status_spec import (
    coerce_status_flex_spec,
    parse_status_card_html,
    resolve_status_flex_spec,
)
from src.services.concierge_templates import (
    build_concierge_app_about_line_flex,
    format_concierge_app_about_card,
)


def test_coerce_explicit_line_flex():
    spec = coerce_status_flex_spec(
        {
            "variant": "notice",
            "title": "カスタムタイトル",
            "body_paragraphs": ["本文1", "本文2"],
            "hints": ["ヒントA"],
        }
    )
    assert spec is not None
    assert spec["title"] == "カスタムタイトル"
    assert spec["body_paragraphs"] == ["本文1", "本文2"]


def test_parse_status_card_html_extracts_title_and_variant():
    html = format_concierge_app_about_card()
    spec = parse_status_card_html(html)
    assert spec is not None
    assert spec["title"] == "このツールについて"
    assert spec["variant"] == "notice"
    assert any("医薬品" in p for p in spec["body_paragraphs"])


def test_concierge_app_about_uses_custom_header_not_generic_info():
    from unittest.mock import patch

    with patch(
        "src.agents.concierge_agent.concierge_chat",
        return_value=MagicMock(
            choices=[
                MagicMock(
                    message=MagicMock(
                        content="私は市販薬の相談をお手伝いするチャットツールです。"
                    )
                )
            ]
        ),
    ):
        p = build_concierge_payload("app_about", "自己紹介してください", MagicMock())
    bot = {
        "type": "bot",
        "content": p["content"],
        "concierge": True,
        "concierge_intent": "app_about",
        "content_format": p["content_format"],
        "line_flex": p["line_flex"],
    }
    messages = build_line_messages_from_bot_message(bot)
    header = messages[0]["contents"]["header"]["contents"][0]["text"]
    assert messages[0]["type"] == "flex"
    assert header == "このツールについて"
    assert messages[0]["contents"]["header"]["backgroundColor"] == "#8EB8E8"
    body_texts = [
        c.get("text", "")
        for c in messages[0]["contents"]["body"]["contents"]
        if c.get("type") == "text"
    ]
    assert any("市販薬" in t for t in body_texts)


def test_line_flex_builder_matches_template_title():
    assert build_concierge_app_about_line_flex()["title"] == "このツールについて"


def test_resolve_prefers_explicit_line_flex_over_html():
    html = format_concierge_app_about_card()
    bot = {
        "content": html,
        "content_format": "status_card",
        "line_flex": {
            "variant": "info",
            "title": "AI生成タイトル",
            "body_paragraphs": ["AIが書いた本文"],
        },
    }
    spec = resolve_status_flex_spec(bot)
    assert spec is not None
    assert spec["title"] == "AI生成タイトル"
    messages = build_line_messages_from_bot_message(
        {
            "type": "bot",
            "content": html,
            "concierge": True,
            "content_format": "status_card",
            "line_flex": bot["line_flex"],
            "diagnosis": {"status": "success", "recommended_medicines": []},
        }
    )
    assert messages[0]["contents"]["header"]["contents"][0]["text"] == "AI生成タイトル"
