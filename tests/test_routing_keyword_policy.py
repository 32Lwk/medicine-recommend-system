"""ルーティングキーワードポリシーのテスト"""
from src.handlers.chat.chat_session_route import apply_emotional_keyword_routing
from src.services.concierge_keyword_probe import probe_concierge_keyword_candidates
from src.services.routing_keyword_policy import (
    attach_routing_keyword_candidates,
    is_decisive_keyword_domain,
    keyword_finalize_allowed,
)
from src.services.store_inquiry_handler import (
    classify_inquiry_with_llm,
    probe_store_keyword_candidates,
)


def test_decisive_domains():
    assert is_decisive_keyword_domain("illegal_drug")
    assert is_decisive_keyword_domain("crisis")
    assert not is_decisive_keyword_domain("store_inquiry")


def test_keyword_finalize_requires_llm_and_gate():
    assert not keyword_finalize_allowed(domain="store_inquiry")
    assert keyword_finalize_allowed(
        domain="store_inquiry", llm_confirmed=True, context_gate_passed=True
    )


def test_attach_candidates_dedup():
    triage = attach_routing_keyword_candidates({}, ["store_facilities", "store_facilities"])
    assert triage["routing_keyword_candidates"] == ["store_facilities"]


def test_emotional_does_not_override_triage_category():
    triage = {"category": "Physical", "confidence": 0.95}
    apply_emotional_keyword_routing(
        {}, triage, "眠くて仕方ない", phase="sleepiness"
    )
    assert triage["category"] == "Physical"
    assert "emotional_sleepiness" in triage.get("routing_keyword_candidates", [])


def test_chitchat_probe_only():
    assert "concierge_chitchat" in probe_concierge_keyword_candidates("今日はいい天気")


def test_university_not_store_candidate():
    assert "store_facilities" not in probe_store_keyword_candidates("大学はどこ？")


def test_classify_inquiry_defers_university_to_concierge():
    triage = {"category": "Other", "subcategory": "store_inquiry", "confidence": 0.84}
    result = classify_inquiry_with_llm("大学はどこ？", None, triage)  # type: ignore[arg-type]
    assert result["is_store_inquiry"] is False
