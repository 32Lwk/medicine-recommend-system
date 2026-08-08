"""medicine_thread_context — プレーン履歴展開とスレッド継続判定。"""

from __future__ import annotations

from unittest.mock import patch


def test_expand_messages_for_llm_resolves_sage_markers():
    from src.services.medicine_thread_context import expand_messages_for_llm

    messages = [
        {"type": "user", "content": "ロキソニンの写真を見せて"},
        {
            "type": "bot",
            "content": "sage_qa",
            "diagnosis": {
                "message": "ロキソニンSのパッケージ画像です。",
            },
        },
    ]
    expanded = expand_messages_for_llm(messages)
    assert len(expanded) == 2
    assert expanded[1]["role"] == "assistant"
    assert "ロキソニンS" in expanded[1]["content"]
    assert expanded[1]["content"] != "sage_qa"


def test_should_continue_medicine_thread_from_intent_router():
    from src.services.medicine_thread_context import should_continue_medicine_thread

    session = {
        "_intent_router_dispatch": {
            "primary_route": "Physical",
            "sub_route": "medicine_followup_qa",
        },
        "messages": [],
    }
    source = should_continue_medicine_thread(
        "Sはついていません",
        session=session,
        sid="test-sid",
    )
    assert source == "intent_router_medicine_followup_qa"


def test_should_not_continue_medicine_thread_on_architecture_pivot():
    from src.services.medicine_thread_context import should_continue_medicine_thread

    session = {
        "_intent_router_dispatch": {
            "primary_route": "Physical",
            "sub_route": "medicine_side_effect_qa",
        },
        "messages": [
            {"type": "user", "content": "ロキソニンの副作用教えて"},
            {"type": "bot", "content": "副作用は...", "diagnosis": {"kind": "medicine_side_effect_qa"}},
        ],
    }
    source = should_continue_medicine_thread(
        "技術スタックは？",
        session=session,
        sid="test-sid",
        conversation_history=session["messages"],
    )
    assert source is None


def test_collect_active_medicine_products_from_user_statement():
    from src.services.medicine_thread_context import collect_active_medicine_products

    messages = [
        {"type": "user", "content": "今ロキソニン飲んでます"},
        {
            "type": "bot",
            "content": "カロナールAもあります",
            "diagnosis": {"recommended_medicines": [{"product_name": "カロナールA"}]},
        },
    ]
    products = collect_active_medicine_products(None, messages=messages)
    names = [str(p.get("product_name") or "") for p in products]
    assert any("ロキソニン" in n for n in names)
    assert "ロキソニン" in names[0]


def test_resolve_session_prioritizes_user_stated_medicine():
    from src.services.medicine_thread_context import resolve_session_recommended_medicines

    session = {
        "messages": [
            {"type": "user", "content": "今ロキソニン飲んでます"},
            {
                "type": "bot",
                "content": "カロナールAもあります",
                "diagnosis": {"recommended_medicines": [{"product_name": "カロナールA"}]},
            },
        ],
    }
    resolved = resolve_session_recommended_medicines(session, messages=session["messages"])
    assert resolved
    assert "ロキソニン" in str(resolved[0].get("product_name") or "")


def test_collect_active_medicine_products_from_expanded_history():
    from src.services.medicine_thread_context import collect_active_medicine_products

    expanded = [
        {"role": "user", "content": "ロキソニンの写真を見せて"},
        {"role": "assistant", "content": "ロキソニンSのパッケージ画像です。"},
    ]
    products = collect_active_medicine_products(None, messages=expanded)
    assert any("ロキソニン" in str(p.get("product_name") or "") for p in products)


def test_should_continue_medicine_thread_rule_based():
    from src.services.medicine_thread_context import should_continue_medicine_thread

    session = {
        "messages": [
            {"type": "user", "content": "ロキソニンの写真を見せて"},
            {
                "type": "bot",
                "content": "sage_qa",
                "diagnosis": {
                    "message": "ロキソニンSのパッケージ画像です。",
                    "is_question": True,
                },
            },
        ],
    }
    source = should_continue_medicine_thread(
        "家にもあります",
        session=session,
        sid="sid-2",
        client=None,
    )
    assert source == "rule_medicine_thread_continuation"


def test_resolve_session_recommended_medicines_from_sage_qa():
    from src.services.medicine_thread_context import resolve_session_recommended_medicines

    session = {
        "messages": [
            {"type": "user", "content": "ロキソニンの写真を見せて"},
            {
                "type": "bot",
                "content": "sage_qa",
                "diagnosis": {
                    "message": "ロキソニンSのパッケージ画像です。",
                    "is_question": True,
                },
            },
        ],
    }
    resolved = resolve_session_recommended_medicines(session, messages=session["messages"])
    assert resolved
    assert any("ロキソニン" in str(m.get("product_name") or "") for m in resolved)


def test_resolve_medicine_qa_route_skips_structural_ack_for_thread():
    from src.services.medicine_qa_eligibility import MedicineQaRoute, resolve_medicine_qa_route

    session = {
        "_intent_router_dispatch": {
            "sub_route": "medicine_followup_qa",
        },
        "messages": [
            {"type": "user", "content": "ロキソニンの写真"},
            {
                "type": "bot",
                "content": "sage_qa",
                "diagnosis": {
                    "message": "ロキソニンSの画像です",
                    "is_question": True,
                    "chat_response": {"answer": "ロキソニンS"},
                },
            },
        ],
    }
    with patch(
        "src.services.concierge_intent.infer_structural_concierge_intent",
        return_value="greeting",
    ):
        decision = resolve_medicine_qa_route(
            "家にもあります",
            session=session,
            sid="sid-1",
            client=None,
        )
    assert decision.route == MedicineQaRoute.MEDICINE_QA
    assert decision.source.startswith(("intent_router_", "rule_medicine_thread_"))


def test_should_continue_medicine_thread_pain_ack_not_new_symptom():
    """「痛みが和らぐ」等の感想は新規症状相談とみなさない。"""
    from src.services.medicine_thread_context import should_continue_medicine_thread

    session = {
        "messages": [
            {"type": "user", "content": "ロキソニンの写真見せて"},
            {
                "type": "bot",
                "content": "sage_qa",
                "diagnosis": {
                    "message": "ロキソニンSのパッケージ画像です。",
                    "is_question": True,
                },
            },
        ],
    }
    source = should_continue_medicine_thread(
        "うん、痛みが和らぐのはありがたいよね。使うときはちゃんと説明書読んでおこう！",
        session=session,
        sid="sid-pain-ack",
        client=None,
    )
    assert source == "rule_medicine_thread_continuation"
