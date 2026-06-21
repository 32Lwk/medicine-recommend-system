"""line_session user_id 抽出のテスト。"""
from src.handlers.line.line_session import user_id_from_line_sid


def test_user_id_from_line_sid():
    assert user_id_from_line_sid("line:Uabc123") == "Uabc123"
    assert user_id_from_line_sid("LINE:Uabc123") == "Uabc123"
    assert user_id_from_line_sid("web-1") is None
    assert user_id_from_line_sid(None) is None


def test_normalize_line_session_id():
    from src.handlers.line.line_session import normalize_line_session_id

    assert normalize_line_session_id("LINE:Uabc") == "line:Uabc"
    assert normalize_line_session_id("line:Uabc") == "line:Uabc"


def test_resolve_session_line_context_native_line():
    from src.handlers.line.line_session import resolve_session_line_context

    ctx = resolve_session_line_context("line:Uabc", {"username": "太郎"})
    assert ctx["is_line_session"] is True
    assert ctx["is_line_handoff"] is False
    assert ctx["is_line_related"] is True
    assert ctx["handoff_from_line"] is None


def test_resolve_session_line_context_handoff_web():
    from src.handlers.line.line_session import resolve_session_line_context

    ctx = resolve_session_line_context(
        "1782062629581934713590",
        {
            "username": "ユーザー3",
            "handoff_from_line": "line:Uabc",
        },
    )
    assert ctx["is_line_session"] is False
    assert ctx["is_line_handoff"] is True
    assert ctx["is_line_related"] is True
    assert ctx["handoff_from_line"] == "line:Uabc"


def test_resolve_session_line_context_pure_web():
    from src.handlers.line.line_session import resolve_session_line_context

    ctx = resolve_session_line_context("1781640419654102951857", {"username": "ユーザー11"})
    assert ctx["is_line_session"] is False
    assert ctx["is_line_handoff"] is False
    assert ctx["is_line_related"] is False
