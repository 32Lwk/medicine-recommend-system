"""merge_session_messages / persist_session_from_chat_state の単体テスト"""
from src.services.session_manager import (
    has_recent_counseling_reply_for_user,
    merge_session_messages,
    normalize_session_messages,
)


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


def test_has_recent_counseling_reply_for_user():
    session = {
        "messages": [
            {"type": "user", "content": "こんにちは"},
            {"type": "bot", "content": "返信", "counseling": True},
        ]
    }
    assert has_recent_counseling_reply_for_user(session, "こんにちは") is True
    assert has_recent_counseling_reply_for_user(session, "別の文") is False


def test_normalize_session_messages_drops_duplicate_counseling_bot():
    messages = [
        {"type": "user", "content": "こんにちは", "uuid": "u1"},
        {"type": "bot", "content": "返信", "counseling": True, "uuid": "b1"},
        {"type": "bot", "content": "返信", "counseling": True, "uuid": "b2"},
    ]
    normalized = normalize_session_messages(messages)
    assert len(normalized) == 2
    assert normalized[1]["uuid"] == "b1"


def test_has_recent_counseling_false_after_resend_user_appended():
    """再送で user が末尾に追加された直後は、新しい bot 返信を許可する。"""
    session = {
        "messages": [
            {"type": "user", "content": "こんにちは", "uuid": "u1"},
            {"type": "bot", "content": "返信", "counseling": True, "uuid": "b1"},
            {"type": "user", "content": "こんにちは", "uuid": "u2"},
        ]
    }
    assert has_recent_counseling_reply_for_user(session, "こんにちは") is False


def test_filter_messages_for_user_api_keeps_blocked_placeholder_strips_admin_fields():
    from src.services.session_manager import filter_messages_for_user_api

    messages = [
        {"type": "user", "content": "頭痛", "uuid": "u1"},
        {
            "type": "user",
            "content": "（この入力はブロックされました）",
            "original_content": "sex",
            "admin_only": True,
            "blocked_input": True,
            "uuid": "u2",
        },
        {"type": "bot", "content": "sage_status", "uuid": "b1"},
    ]
    filtered = filter_messages_for_user_api(messages)
    assert len(filtered) == 3
    blocked = filtered[1]
    assert blocked["content"] == "（この入力はブロックされました）"
    assert blocked["uuid"] == "u2"
    assert "original_content" not in blocked
    assert "admin_only" not in blocked
    assert "blocked_input" not in blocked


def test_filter_messages_for_user_api_legacy_placeholder_strips_nothing_extra():
    from src.services.session_manager import filter_messages_for_user_api

    messages = [
        {"type": "user", "content": "（この入力はブロックされました）", "uuid": "u1"},
        {"type": "bot", "content": "notice", "uuid": "b1"},
    ]
    filtered = filter_messages_for_user_api(messages)
    assert len(filtered) == 2
    assert filtered[0]["content"] == "（この入力はブロックされました）"
