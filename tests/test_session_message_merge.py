"""merge_session_messages / persist_session_from_chat_state の単体テスト"""
from src.services.session_manager import merge_session_messages


def test_merge_session_messages_prefers_server_order():
    server = [
        {"type": "user", "content": "a", "uuid": "1"},
        {"type": "bot", "content": "b", "uuid": "2"},
    ]
    client = [
        {"type": "user", "content": "a", "uuid": "1"},
        {"type": "bot", "content": "c", "uuid": "3"},
    ]
    merged = merge_session_messages(server, client)
    assert len(merged) == 3
    assert merged[0]["uuid"] == "1"
    assert merged[2]["uuid"] == "3"


def test_merge_session_messages_restores_from_client_when_server_empty():
    client = [{"type": "user", "content": "hello", "uuid": "x"}]
    assert merge_session_messages([], client) == client


def test_merge_session_messages_dedupes_same_content_without_uuid():
    msg = {"type": "user", "content": "mrcdev", "timestamp": "t1"}
    merged = merge_session_messages([msg], [dict(msg)])
    assert len(merged) == 1
