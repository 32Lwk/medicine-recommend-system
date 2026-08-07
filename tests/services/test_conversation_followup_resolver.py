"""conversation_followup_resolver の単体テスト。"""
from __future__ import annotations

from src.services.conversation_followup_resolver import (
    FollowupIntent,
    _parse_intent_response,
    followup_intent_warrants_rescore,
    should_invoke_ambiguous_resolver,
)


def test_parse_rescore_intent() -> None:
    assert _parse_intent_response('{"user_intent": "rescore"}') == FollowupIntent.RESCORE


def test_parse_medicine_qa_intent() -> None:
    assert _parse_intent_response('{"intent": "medicine_qa"}') == FollowupIntent.MEDICINE_QA


def test_rescore_warrants_rescore() -> None:
    assert followup_intent_warrants_rescore(FollowupIntent.RESCORE)
    assert not followup_intent_warrants_rescore(FollowupIntent.MEDICINE_QA)


def test_should_invoke_with_reco_history() -> None:
    history = [
        {"type": "user", "content": "鼻水が止まらない"},
        {
            "type": "bot",
            "content": "おすすめです",
            "diagnosis": {"kind": "recommendation", "recommended_medicines": [{"name": "A"}]},
        },
    ]
    assert should_invoke_ambiguous_resolver(
        "それ平気？",
        conversation_history=history,
        recommended_medicines=[{"product_name": "A"}],
    )


def test_should_not_invoke_without_context() -> None:
    assert not should_invoke_ambiguous_resolver("平気？", conversation_history=[])
