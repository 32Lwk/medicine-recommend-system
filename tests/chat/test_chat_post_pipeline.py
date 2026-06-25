"""chat_post_pipeline のスモークテスト"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from src.handlers.chat.chat_post_pipeline import ChatPostContext, run_chat_post_pipeline
from src.utils.chat_http_context import ChatClientInfo


def test_empty_message_short_circuit():
    session = {"messages": []}
    client = ChatClientInfo(client_ip="127.0.0.1", user_agent="test")
    with patch(
        "src.handlers.chat.chat_post_pipeline.empty_message_response",
        return_value=({"status": "ok", "message_count": 0}, 200),
    ):
        resp = run_chat_post_pipeline(session, client, "", "sid", MagicMock())
    assert resp[0]["status"] == "ok"


def test_context_dataclass_defaults():
    ctx = ChatPostContext(
        session={},
        client_info=ChatClientInfo(client_ip="1", user_agent="t"),
        sid=None,
        monitor=MagicMock(),
        user_agent="t",
        client_ip="1",
    )
    assert ctx.triage_result is None
    assert ctx.inappropriate_request_detected is False


def test_sync_routing_context_sets_ask_category():
    """Ask トリアージ後に RoutingContext が同期される（capabilities 誤爆防止の前提）。"""
    from src.handlers.chat.chat_post_pipeline import sync_routing_context
    from src.services.concierge_intent import classify_concierge_intent

    session = {
        "messages": [],
        "last_triage_result": {"category": "Ask", "confidence": 0.95},
    }
    ctx = ChatPostContext(
        session=session,
        client_info=ChatClientInfo(client_ip="127.0.0.1", user_agent="test"),
        sid="sid-ask",
        monitor=MagicMock(),
        user_agent="test",
        client_ip="127.0.0.1",
        user_message="陸上競技でも使える風邪薬を教えてください。",
        sanitized_message="陸上競技でも使える風邪薬を教えてください。",
        triage_result={"category": "Ask", "confidence": 0.95},
    )
    sync_routing_context(ctx)
    assert ctx.routing is not None
    assert ctx.routing.triage_category == "Ask"
    assert classify_concierge_intent(ctx.user_message) is None


def test_sync_messages_not_shadowed_by_conditional_import():
    """memory_delete 分岐の関数内 import がモジュール import をシャドウしないこと。"""
    import inspect

    from src.handlers.chat import chat_post_pipeline as mod

    src = inspect.getsource(mod.run_chat_post_pipeline)
    assert (
        "from src.handlers.chat.chat_session_route import sync_messages_to_db_for_admin"
        not in src
    )


def test_finalize_pipeline_response_appends_redirect_when_no_bot():
    """当該ターンで bot が無い場合、終端ガードが redirect を補完する。"""
    from src.handlers.chat.chat_pipeline_end_guard import finalize_pipeline_response

    session = {
        "messages": [{"type": "user", "content": "ふわふわ"}],
        "user_attributes": {},
        "ui_variant": "sage",
    }
    client = ChatClientInfo(client_ip="127.0.0.1", user_agent="test")
    body, status = finalize_pipeline_response(
        session,
        "sid-guard",
        client,
        0,
        ({"status": "ok", "message_count": 1}, 200),
    )
    assert status == 200
    assert body.get("pipeline_end_guard") == "redirect"
    bots = [m for m in session["messages"] if m.get("type") == "bot"]
    assert len(bots) == 1
    assert bots[0].get("concierge_intent") == "redirect"
