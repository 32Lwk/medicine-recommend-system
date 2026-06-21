"""LINE Flex Message ビルダーのテスト。"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.handlers.line.flex_messages import (
    PRIMARY,
    SCORE_LOW,
    SCORE_MEDIUM,
    build_line_messages_from_bot_message,
    html_to_plain_text,
    truncate_text,
)
from src.handlers.line.line_i18n import get_line_ui_strings
from tests._paths import FIXTURES_DIR

FIXTURE_PATH = FIXTURES_DIR / "line_flex_success.json"

SAMPLE_MEDICINES = [
    {
        "rank": 1,
        "product_name": "イブA錠",
        "manufacturer": "エスエス製薬",
        "efficacy": "頭痛、歯痛、生理痛",
        "explanation": "胃にやさしい成分。眠くなりにくい解熱鎮痛剤です。",
        "usage_notes": "用法用量を守ってご使用ください。",
        "display_score": 85,
    },
    {
        "rank": 2,
        "product_name": "カロナールA",
        "manufacturer": "第一三共",
        "efficacy": "発熱時の解熱",
        "explanation": "痛みが強い方に。速く効く製剤です。",
        "usage_notes": "過量服用に注意。",
        "display_score": 72,
    },
    {
        "rank": 3,
        "product_name": "リングルアイビー",
        "manufacturer": "佐藤製薬",
        "efficacy": "頭痛",
        "explanation": "速く効かせたい方におすすめ。",
        "usage_notes": "15歳未満は服用しないでください。",
        "display_score": 55,
    },
]


def _success_bot_message() -> dict:
    return {
        "type": "bot",
        "content": "<p>推奨</p>",
        "diagnosis": {
            "status": "success",
            "medicine_type": "解熱鎮痛剤",
            "recommended_medicines": SAMPLE_MEDICINES,
            "doctor_consultation": "",
        },
    }


def test_truncate_text():
    assert truncate_text("あ" * 25, 20) == ("あ" * 19) + "…"
    assert truncate_text("short", 20) == "short"


def test_html_to_plain_text():
    assert "頭痛" in html_to_plain_text("<p>頭痛<strong>です</strong></p>")


def test_success_returns_two_flex_messages():
    messages = build_line_messages_from_bot_message(_success_bot_message())
    assert len(messages) == 2
    assert messages[0]["type"] == "flex"
    assert messages[1]["type"] == "flex"


def test_carousel_has_three_bubbles_with_noimage_hero(monkeypatch):
    monkeypatch.delenv("PUBLIC_SITE_URL", raising=False)
    messages = build_line_messages_from_bot_message(_success_bot_message())
    carousel = messages[1]["contents"]
    assert carousel["type"] == "carousel"
    assert len(carousel["contents"]) == 3
    for bubble in carousel["contents"]:
        hero = bubble["hero"]
        assert hero["type"] == "image"
        assert "medicine-noimage-hero" in hero["url"]
        assert hero["url"].startswith("https://")


def test_advice_contains_caution_and_bullets():
    messages = build_line_messages_from_bot_message(_success_bot_message())
    body = messages[0]["contents"]["body"]["contents"]
    texts = [c.get("text", "") for c in body if c.get("type") == "text"]
    joined = "\n".join(texts)
    assert "医師・薬剤師" in joined
    assert "イブA錠" in joined
    assert messages[0]["contents"]["header"]["backgroundColor"] == PRIMARY


def test_advice_includes_symptoms_and_overlap_when_present():
    bot = _success_bot_message()
    bot["diagnosis"]["symptoms"] = ["頭痛"]
    bot["diagnosis"]["personalized_advice"] = "頭痛いのはつらいですね。安静にして水分をとってください。"
    bot["diagnosis"]["ingredient_overlap"] = {
        "severity": "red",
        "title": "成分の重複について（重複禁止）",
        "summaries": ["アセトアミノフェン：カロナールA、タイレノールA"],
    }
    messages = build_line_messages_from_bot_message(bot)
    body_text = "\n".join(
        c.get("text", "") for c in messages[0]["contents"]["body"]["contents"] if c.get("type") == "text"
    )
    assert "推定症状" in body_text
    assert "頭痛" in body_text
    assert "重複禁止" in body_text
    assert "安静" in body_text


def test_fixture_meta():
    meta = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    messages = build_line_messages_from_bot_message(_success_bot_message())
    assert len(messages) == meta["expected_message_count"]
    assert [m["type"] for m in messages] == meta["expected_types"]


def _flex_body_text(message: dict) -> str:
    body = message["contents"]["body"]["contents"]
    return "\n".join(c.get("text", "") for c in body if c.get("type") == "text")


def test_crisis_returns_critical_status_flex():
    bot = {
        "type": "bot",
        "crisis_support": True,
        "content": "<p>相談窓口 <a href='https://example.com'>リンク</a></p>",
    }
    messages = build_line_messages_from_bot_message(bot)
    assert len(messages) == 1
    assert messages[0]["type"] == "flex"
    assert messages[0]["contents"]["header"]["backgroundColor"] == "#E8A0A8"
    assert "相談窓口" in _flex_body_text(messages[0])


def test_empty_medicines_pharmacist_fallback_flex():
    bot = {
        "type": "bot",
        "content": "",
        "diagnosis": {"status": "success", "recommended_medicines": []},
    }
    messages = build_line_messages_from_bot_message(bot)
    assert messages[0]["type"] == "flex"
    assert "薬剤師" in _flex_body_text(messages[0])


def test_escalation_returns_critical_status_flex():
    bot = {
        "type": "bot",
        "diagnosis": {
            "status": "escalation_required",
            "doctor_consultation": "妊娠中のため医師にご相談してください。",
            "recommended_medicines": [],
        },
    }
    messages = build_line_messages_from_bot_message(bot)
    assert messages[0]["type"] == "flex"
    assert messages[0]["contents"]["header"]["backgroundColor"] == "#E8A0A8"
    assert "妊娠" in _flex_body_text(messages[0])


def test_questions_returns_notice_status_flex():
    bot = {
        "type": "bot",
        "diagnosis": {
            "status": "success",
            "recommended_medicines": [],
            "additional_questions": ["痛みはいつからですか？", "熱はありますか？"],
        },
    }
    messages = build_line_messages_from_bot_message(bot)
    assert messages[0]["type"] == "flex"
    assert messages[0]["contents"]["header"]["backgroundColor"] == "#8EB8E8"
    assert "痛み" in _flex_body_text(messages[0])


def test_emergency_returns_critical_status_flex():
    bot = {
        "type": "bot",
        "emergency_detected": True,
        "content": "<p>緊急のため受診してください。</p>",
    }
    messages = build_line_messages_from_bot_message(bot)
    assert messages[0]["type"] == "flex"
    assert "緊急" in _flex_body_text(messages[0])


def test_greeting_returns_plain_text():
    bot = {
        "type": "bot",
        "content": "こんにちは。症状やお薬についてのご質問を承ります。",
        "greeting": True,
    }
    messages = build_line_messages_from_bot_message(bot)
    assert messages[0]["type"] == "text"
    assert "こんにちは" in messages[0]["text"]


def test_greeting_sage_marker_uses_diagnosis_message():
    bot = {
        "type": "bot",
        "content": "sage_status",
        "greeting": True,
        "concierge": True,
        "concierge_intent": "greeting",
        "content_format": "text",
        "diagnosis": {
            "render": "sage_status",
            "layout": "plain",
            "title": "ご挨拶",
            "message": "こんー！こちらはOTC（市販薬）の相談窓口だよ。",
            "kind": "concierge_greeting",
        },
    }
    messages = build_line_messages_from_bot_message(bot)
    assert messages[0]["type"] == "text"
    assert messages[0]["text"] == bot["diagnosis"]["message"]
    assert "sage_status" not in messages[0]["text"]


def test_counseling_sage_marker_uses_diagnosis_message():
    bot = {
        "type": "bot",
        "content": "sage_status",
        "counseling": True,
        "diagnosis": {
            "render": "sage_status",
            "title": "カウンセリング",
            "message": "お疲れのようですね。十分な休息をお勧めします。",
        },
    }
    messages = build_line_messages_from_bot_message(bot)
    assert messages[0]["type"] == "text"
    assert "お疲れ" in messages[0]["text"]


def test_chitchat_concierge_returns_plain_text():
    bot = {
        "type": "bot",
        "content": "今日はいい天気ですね。お体の調子はいかがですか？",
        "concierge": True,
        "concierge_intent": "chitchat",
        "content_format": "text",
    }
    messages = build_line_messages_from_bot_message(bot)
    assert messages[0]["type"] == "text"
    assert "天気" in messages[0]["text"]


def test_counseling_flag_returns_plain_text():
    bot = {
        "type": "bot",
        "content": "お疲れのようですね。十分な休息をお勧めします。",
        "counseling": True,
    }
    messages = build_line_messages_from_bot_message(bot)
    assert messages[0]["type"] == "text"
    assert "お疲れ" in messages[0]["text"]


def test_advisory_plain_content_without_counseling_flag_info_flex():
    bot = {
        "type": "bot",
        "content": "<p>お疲れのようですね。十分な休息をお勧めします。</p>",
        "diagnosis": {"status": "success", "recommended_medicines": []},
    }
    messages = build_line_messages_from_bot_message(bot)
    assert messages[0]["type"] == "flex"
    assert messages[0]["contents"]["header"]["backgroundColor"] == PRIMARY
    assert "お疲れ" in _flex_body_text(messages[0])


def test_i18n_ui_strings_en():
    ui = get_line_ui_strings("en")
    messages = build_line_messages_from_bot_message(_success_bot_message(), lang="en")
    header = messages[0]["contents"]["header"]["contents"][0]["text"]
    assert header == ui["advice_header"]
    assert "Recommended medicines" in messages[1]["altText"]


def test_score_three_tier_colors():
    messages = build_line_messages_from_bot_message(_success_bot_message())
    bubbles = messages[1]["contents"]["contents"]

    def _score_color(bubble: dict) -> str:
        for block in bubble["body"]["contents"]:
            if block.get("type") == "box" and block.get("layout") == "baseline":
                for item in block["contents"]:
                    if item.get("weight") == "bold":
                        return item["color"]
        raise AssertionError("score color not found")

    assert _score_color(bubbles[0]) == PRIMARY
    assert _score_color(bubbles[1]) == SCORE_MEDIUM
    assert _score_color(bubbles[2]) == SCORE_LOW


def test_carousel_alt_includes_count():
    messages = build_line_messages_from_bot_message(_success_bot_message())
    assert "（3件）" in messages[1]["altText"]
