"""RequestSafeSession — dict 互換の pop 挙動"""
from src.utils.request_safe_session import RequestSafeSession


def test_pop_missing_key_with_none_default():
    session = RequestSafeSession()
    assert session.pop("_user_attr_notice_appended", None) is None
    assert session.modified is False


def test_pop_existing_key():
    session = RequestSafeSession({"flag": True})
    assert session.pop("flag", None) is True
    assert session.modified is True
