"""e2e_gpt_user_sim の単体テスト。"""
from __future__ import annotations

from src.services.e2e_gpt_user_sim import (
    build_persona_block,
    sanitize_simulated_user_text,
    validate_simulated_user_output,
)


def test_build_persona_block_includes_demographics() -> None:
    block = build_persona_block(
        system="関西弁",
        demographics={"age": "40代", "region": "関西"},
        label="関西弁ユーザー",
    )
    assert "40代" in block
    assert "関西" in block
    assert "関西弁" in block


def test_sanitize_strips_bot_prefix() -> None:
    assert sanitize_simulated_user_text("アシスタント: のど痛いですね") == "のど痛いですね"


def test_sanitize_long_advice_collapses() -> None:
    advice = (
        "咳が出るのは辛いですね。水分をしっかり取るのが大事です。"
        "温かい飲み物も効果的かもしれません。試してみてください。"
    )
    out = sanitize_simulated_user_text(advice, opening="咳がつらい")
    assert out == "咳がつらい"


def test_validate_rejects_bot_echo_interview() -> None:
    ok, reason = validate_simulated_user_output("具体的にどんな症状がありますか？教えてください")
    assert not ok
    assert reason == "bot_echo_symptom_interview"


def test_validate_accepts_patient_pivot() -> None:
    ok, reason = validate_simulated_user_output("いや、やっぱ咳の方がキツい")
    assert ok
    assert reason == ""
