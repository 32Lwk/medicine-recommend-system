"""同一文言のユーザーメッセージが保持されることのテスト。"""

from src.services.session_manager import (
    append_user_message,
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
