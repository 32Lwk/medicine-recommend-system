"""Concierge 公式ドキュメントローダのテスト"""
from src.content.concierge_docs import (
    DOC_CONCIERGE_INTENTS,
    is_doc_concierge_intent,
    load_concierge_doc,
)


def test_all_doc_intents_load():
    assert len(DOC_CONCIERGE_INTENTS) == 6
    file_backed = DOC_CONCIERGE_INTENTS - {"doc_changelog"}
    for intent in file_backed:
        assert is_doc_concierge_intent(intent)
        title, body = load_concierge_doc(intent)
        assert title
        assert len(body) > 50
    assert is_doc_concierge_intent("doc_changelog")


def test_privacy_doc_contains_policy_heading():
    title, body = load_concierge_doc("doc_privacy")
    assert "プライバシー" in title
    assert "プライバシーポリシー" in body


def test_operator_doc_excludes_personal_attributes():
    title, body = load_concierge_doc("doc_operator")
    assert "お問い合わせ" in title
    assert "ConciergeAgent 専用" in body
    assert "weary-scoots.7y@icloud.com" in body
    assert "川嶋" not in body
    assert "名古屋大学" not in body


def test_operator_doc_is_separate_from_public_operator_md():
    """公開用 docs/public/運営者情報.md は Concierge の doc_operator では読まない。"""
    from tests._paths import PROJECT_ROOT

    public = (PROJECT_ROOT / "docs" / "public" / "運営者情報.md").read_text(
        encoding="utf-8"
    )
    _, concierge_body = load_concierge_doc("doc_operator")
    assert "川嶋" in public
    assert "川嶋" not in concierge_body
