"""Concierge 公式ドキュメントローダのテスト"""
from src.content.concierge_docs import (
    DOC_CONCIERGE_INTENTS,
    is_doc_concierge_intent,
    load_concierge_doc,
)


def test_all_doc_intents_load():
    assert len(DOC_CONCIERGE_INTENTS) == 5
    for intent in DOC_CONCIERGE_INTENTS:
        assert is_doc_concierge_intent(intent)
        title, body = load_concierge_doc(intent)
        assert title
        assert len(body) > 50


def test_privacy_doc_contains_policy_heading():
    title, body = load_concierge_doc("doc_privacy")
    assert "プライバシー" in title
    assert "プライバシーポリシー" in body
