"""language_utils の優先順位と LINE プロフィールフォールバック"""
from src.core.language_utils import (
    is_weak_language_signal,
    language_hint_from_session,
    line_profile_language,
    resolve_message_language,
    update_session_language_from_message,
)


class _Session(dict):
    pass


def test_line_profile_language_normalized():
    s = _Session(line_profile={"language": "en"})
    assert line_profile_language(s) == "en"
    s2 = _Session(line_profile={"language": "zh-TW"})
    assert line_profile_language(s2) == "zh"


def test_language_hint_priority():
    s = _Session(
        line_profile={"language": "en"},
        language="ko",
        detected_language="ja",
    )
    assert language_hint_from_session(s) == "ja"

    s2 = _Session(line_profile={"language": "en"}, language="ko")
    assert language_hint_from_session(s2) == "ko"

    s3 = _Session(line_profile={"language": "en"})
    assert language_hint_from_session(s3) == "en"


def test_weak_signal_uses_hint_not_english_default():
    s = _Session(line_profile={"language": "ja"})
    assert is_weak_language_signal("ok") is True
    assert resolve_message_language("ok", s) == "ja"


def test_input_language_overrides_line_profile():
    s = _Session(line_profile={"language": "ja"})
    assert resolve_message_language("I have a headache", s) == "en"
    assert update_session_language_from_message(s, "I have a headache") == "en"
    assert s["detected_language"] == "en"


def test_weak_signal_keeps_detected_language():
    s = _Session(line_profile={"language": "ja"}, detected_language="en")
    assert update_session_language_from_message(s, "ok") == "en"
    assert s["detected_language"] == "en"


def test_weak_signal_without_detected_uses_profile():
    s = _Session(line_profile={"language": "en"})
    assert update_session_language_from_message(s, "yes") == "en"
    assert s["detected_language"] == "en"
