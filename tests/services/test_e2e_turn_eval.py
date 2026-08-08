"""e2e_turn_eval ユニットテスト。"""
from __future__ import annotations

from src.services.e2e_turn_eval import (
    TurnEvalContext,
    apply_global_rules,
    build_turn_expect_map,
    evaluate_scenario_all_turns,
    evaluate_turn_expect,
    text_similarity,
)


def _kind_route(kind: str, _content: str = "") -> str:
    if "concierge" in (kind or "").lower():
        return "Concierge"
    if "session" in (kind or "").lower():
        return "SessionOps"
    return "Physical"


def test_reject_no_reco_global_rule():
    ctx = TurnEvalContext(
        turn_index=0,
        user_message="飲み合わせは？",
        bot_text="申し訳ありません。推奨医薬品の情報では回答できません。",
        diagnosis_kind="medicine_qa",
    )
    _, failures, rule_ids = apply_global_rules(ctx)
    assert "reject_no_reco" in failures
    assert "reject_no_reco" in rule_ids


def test_comparison_loop_detects_similar_bot():
    prior = "ロキソニンとイブの違いは、成分と効き方です。" * 3
    ctx = TurnEvalContext(
        turn_index=1,
        user_message="どっちがいい？",
        bot_text=prior,
        prior_bot_text=prior,
        is_follow_up=True,
    )
    _, failures, _ = apply_global_rules(ctx)
    assert "comparison_loop" in failures


def test_greeting_reset_on_follow_up():
    ctx = TurnEvalContext(
        turn_index=1,
        user_message="家にもあります",
        bot_text="こんにちは",
        is_follow_up=True,
    )
    _, failures, _ = apply_global_rules(ctx)
    assert "greeting_reset" in failures


def test_build_turn_expect_map_merges_final_expect():
    spec = {
        "setup": ["ロキソニン"],
        "input": "家にもあります",
        "turn_expects": [{"turn": 0, "expect": {"context_keywords": ["ロキソニン"]}}],
        "expect": {"must_not": ["greeting_only"], "context_keywords": ["ロキソニン"]},
    }
    m = build_turn_expect_map(spec)
    assert 0 in m
    assert 1 in m
    assert m[1].get("must_not") == ["greeting_only"]
    assert "ロキソニン" in m[1].get("context_keywords", [])


def test_must_reference_prior_fails_without_keyword():
    ctx = TurnEvalContext(
        turn_index=1,
        user_message="家にもあります",
        bot_text="一般的な市販薬についてご案内します。",
        prior_user_message="ロキソニンの写真を見せてください",
        is_follow_up=True,
    )
    result = evaluate_turn_expect(
        ctx,
        {"must_reference_prior": True, "must_have_response": True},
        kind_route_fn=_kind_route,
    )
    assert not result.passed
    assert any("must_reference_prior" in f for f in result.failures)


def test_must_answer_question_on_follow_up():
    ctx = TurnEvalContext(
        turn_index=1,
        user_message="カロナールの成分は？",
        bot_text="こんにちは。",
        is_follow_up=True,
    )
    result = evaluate_turn_expect(
        ctx,
        {"must_answer_question": True},
        kind_route_fn=_kind_route,
    )
    assert not result.passed


def test_evaluate_scenario_all_turns_backward_compat():
    turns = [
        {"user_message": "頭痛", "response_full": "お大事に。", "diagnosis_kind": "sage_reco", "http_status": 200},
    ]
    spec = {"expect": {"must_have_response": True}}
    ok, _, failures, results = evaluate_scenario_all_turns(
        spec, turns, kind_route_fn=_kind_route
    )
    assert ok
    assert len(results) == 1
    assert not failures


def test_text_similarity_identical():
    assert text_similarity("abc def", "abc def") >= 0.99
