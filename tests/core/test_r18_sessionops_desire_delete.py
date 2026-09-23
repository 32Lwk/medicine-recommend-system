"""R18: SessionOps desire-form delete must not be Jev-eligible."""
from __future__ import annotations

from src.core.session_ops_classify import classify_session_intent
from src.dialogue.routing.pre_route_signals import collect_pre_route_signals
from src.services.jev_eligibility import decide_jev_intent_eligibility


def test_r18_delete_desire_form_sessionops_ineligible():
    text = "この相談の記録を丸ごと消したいです。"
    assert classify_session_intent(text) == "delete"
    sig = collect_pre_route_signals(text)
    assert sig.session_operation == "delete"
    decision = decide_jev_intent_eligibility(sig)
    assert decision.eligible is False
    assert decision.reason == "sessionops_fast_path"
