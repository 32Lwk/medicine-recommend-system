"""ユーザー言及順（回答順序）の unit tests。"""
from __future__ import annotations

from src.services.concierge_response_order import (
    append_mention_order_requirements,
    build_legal_crossdoc_fallback_body,
    build_legal_crossdoc_requirements,
    extract_legal_crossdoc_topic_order,
    legal_crossdoc_card_title,
    resolve_legal_crossdoc_topic_order,
)


def test_extract_terms_before_privacy():
    q = "免責事項・利用規約（β版）とプライバシーの違いは？"
    order = extract_legal_crossdoc_topic_order(q)
    assert [t.topic_id for t in order] == ["terms", "privacy"]


def test_extract_privacy_before_terms():
    q = "プライバシーと利用規約の違いは？"
    order = extract_legal_crossdoc_topic_order(q)
    assert [t.topic_id for t in order] == ["privacy", "terms"]


def test_requirements_follow_user_order():
    q = "免責事項・利用規約（β版）とプライバシーの違いは？"
    req = build_legal_crossdoc_requirements(q)
    assert "利用規約・免責 → プライバシーポリシー" in req
    assert req.index("第1段落: 利用規約") < req.index("第2段落: プライバシー")


def test_card_title_follows_user_order():
    assert legal_crossdoc_card_title("免責とプライバシーの違い") == "利用規約とプライバシー"
    assert legal_crossdoc_card_title("プライバシーと利用規約") == "プライバシーと利用規約"


def test_fallback_body_terms_first():
    body = build_legal_crossdoc_fallback_body(
        "免責事項・利用規約とプライバシーの違い",
        info_hint="hint",
    )
    assert body.index("利用規約・免責は") < body.index("プライバシーポリシーは")


def test_resolve_default_when_single_mention():
    q = "プライバシーポリシーについて"
    order = resolve_legal_crossdoc_topic_order(q)
    assert [t.topic_id for t in order] == ["privacy", "terms"]


def test_append_mention_order_for_comparison_question():
    q = "GCPとAWSの違いは？"
    base = "【要件】\n- 参照のみ"
    out = append_mention_order_requirements(base, q, intent="architecture")
    assert "質問文に現れた順" in out
