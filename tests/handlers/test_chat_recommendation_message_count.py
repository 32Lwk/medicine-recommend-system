"""推奨フロー POST 応答の message_count（Web cookie slimming 後）。"""

from __future__ import annotations

from src.handlers.chat.chat_response_builder import build_success_response


def test_build_success_response_honors_explicit_db_count_after_slimming():
    """Cookie slimming で session.messages が空でも、DB 件数を渡せば正しい count を返す。"""
    session: dict = {}
    db_message_count = 4
    body, status = build_success_response(session, message_count=db_message_count)
    assert status == 200
    assert body["message_count"] == 4
    assert len(session.get("messages", [])) == 0
