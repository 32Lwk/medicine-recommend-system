"""line_session user_id 抽出のテスト。"""
from src.handlers.line.line_session import user_id_from_line_sid


def test_user_id_from_line_sid():
    assert user_id_from_line_sid("line:Uabc123") == "Uabc123"
    assert user_id_from_line_sid("web-1") is None
    assert user_id_from_line_sid(None) is None
