"""同一文言のユーザーメッセージが保持されることのテスト。"""

from src.services.session_manager import (
    append_user_message,
    has_recent_concierge_reply_for_user,
    was_last_user_message,
    remove_duplicate_user_messages_after_ai_response,
)


def test_append_user_message_allows_same_content_twice():
    session = {'messages': []}
    append_user_message(session, 'Hello')
    append_user_message(session, 'Hello')
    user_contents = [m['content'] for m in session['messages'] if m['type'] == 'user']
    assert user_contents == ['Hello', 'Hello']
    assert session['messages'][0]['uuid'] != session['messages'][1]['uuid']


def test_was_last_user_message_prevents_same_request_double_add():
    session = {'messages': []}
    append_user_message(session, 'Hello')
    assert was_last_user_message(session, 'Hello') is True
    assert was_last_user_message(session, 'Hi') is False


def test_remove_duplicate_user_messages_is_noop():
    assert remove_duplicate_user_messages_after_ai_response('nonexistent') is False


def test_has_recent_concierge_reply_false_when_user_appended_before_bot():
    """パイプライン先追記後は Concierge 応答を許可する。"""
    session = {"messages": [{"type": "user", "content": "あんたについて教えて"}]}
    assert has_recent_concierge_reply_for_user(session, "あんたについて教えて") is False


def test_has_recent_concierge_reply_true_after_bot():
    session = {
        "messages": [
            {"type": "user", "content": "あんたについて教えて"},
            {"type": "bot", "content": "自己紹介", "concierge": True},
        ]
    }
    assert has_recent_concierge_reply_for_user(session, "あんたについて教えて") is True
