"""turn_user_goal / must_answer_question テスト。"""
from __future__ import annotations

from src.services.e2e_turn_eval import TurnEvalContext, evaluate_turn_expect
from src.services.turn_user_goal import resolve_turn_user_goal


def test_resolve_correction_goal():
    assert resolve_turn_user_goal("いや、違う、イブの方が気になる") == "correction"


def test_resolve_clarify_without_product():
    assert resolve_turn_user_goal("他の薬と一緒に飲んでも大丈夫？") == "clarify"


def test_must_answer_alcohol_synonym():
    ctx = TurnEvalContext(
        turn_index=1,
        user_message="お酒飲んでも平気？",
        bot_text="ロキソニン服用中の飲酒は避けるのが安全です。アルコールとの併用に注意。",
        is_follow_up=True,
    )
    result = evaluate_turn_expect(ctx, {"must_answer_question": True})
    assert result.passed, result.failures
