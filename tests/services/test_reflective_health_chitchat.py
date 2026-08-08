"""reflective health chitchat fast-path"""
from __future__ import annotations

from src.services.concierge_intent import (
    build_reflective_health_chitchat_text,
    looks_like_reflective_health_chitchat,
)


def test_reflective_health_detected():
    msg = "最近疲れが取れなくて、市販薬に頼りすぎかもしれません"
    assert looks_like_reflective_health_chitchat(msg)


def test_reflective_health_fast_path_text():
    msg = "最近疲れが取れなくて、市販薬に頼りすぎかもしれません"
    text = build_reflective_health_chitchat_text(msg)
    assert "市販薬" in text
    assert "推奨医薬品の情報では回答できません" not in text
    assert "お聞かせ" in text or "お気軽" in text


def test_medicine_question_not_reflective():
    assert not looks_like_reflective_health_chitchat("ロキソニンとバファリンどっちがいい？")
