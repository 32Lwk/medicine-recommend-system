"""同一文言のユーザーメッセージが保持されることのテスト。"""

from src.services.session_manager import (
    append_user_message,
    was_last_user_message,
    should_skip_duplicate_user_append,
    should_skip_append_user_message,
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


def test_should_skip_duplicate_user_append_after_info_notification():
    session = {
        'messages': [
            {'type': 'user', 'content': '花粉症です'},
            {'type': 'bot', 'user_info_notification': True, 'content': 'sage_status'},
        ]
    }
    assert should_skip_duplicate_user_append(session, '花粉症です') is True
    assert should_skip_append_user_message(session, '花粉症です') is True


def test_should_allow_resend_after_counseling_bot():
    session = {
        'messages': [
            {'type': 'user', 'content': '花粉症です'},
            {'type': 'bot', 'user_info_notification': True},
            {'type': 'bot', 'counseling': True, 'content': 'sage_status'},
        ]
    }
    assert should_skip_duplicate_user_append(session, '花粉症です') is False
    assert should_skip_append_user_message(session, '花粉症です') is False


def test_should_skip_duplicate_user_append_after_diagnosis_notice():
    session = {
        'messages': [
            {'type': 'user', 'content': '花粉症で、頭が痛いです'},
            {
                'type': 'bot',
                'diagnosis_type': 'other',
                'diagnosis': {'kind': 'diagnosis_detected'},
            },
        ]
    }
    assert should_skip_duplicate_user_append(session, '花粉症で、頭が痛いです') is True
    assert should_skip_append_user_message(session, '花粉症で、頭が痛いです') is True


def test_has_diagnosis_notice_for_user():
    session = {
        'messages': [
            {'type': 'user', 'content': '糖尿病です'},
            {'type': 'bot', 'diagnosis_type': 'chronic', 'diagnosis': {'kind': 'diagnosis_detected'}},
        ]
    }
    from src.services.session_manager import has_diagnosis_notice_for_user

    assert has_diagnosis_notice_for_user(session, '糖尿病です') is True
    assert has_diagnosis_notice_for_user(session, '別の入力') is False


def test_remove_duplicate_user_messages_is_noop():
    assert remove_duplicate_user_messages_after_ai_response('nonexistent') is False
