"""LINE 推奨後の bot メッセージがインメモリ session に残ることの回帰テスト。"""
from __future__ import annotations

from unittest.mock import MagicMock

from src.handlers.chat.chat_pipeline_end_guard import finalize_pipeline_response
from src.handlers.line.line_session import count_bot_messages_in_session, is_line_session_id
from src.services.recommendation_diagnosis_builder import SAGE_RECO_MARKER


def test_is_line_session_id():
    assert is_line_session_id("line:Uabc")
    assert not is_line_session_id("web:s1")


def test_finalize_pipeline_response_ok_when_line_bot_in_memory():
    """推奨フロー後に bot が session.messages にあれば end_guard は missing にならない。"""
    session = {"messages": [{"type": "user", "content": "頭が痛い"}]}
    bot = {
        "type": "bot",
        "content": SAGE_RECO_MARKER,
        "diagnosis": {"render": "sage_reco", "recommended_medicines": []},
    }
    session["messages"].append(bot)

    before = count_bot_messages_in_session(session) - 1
    body, status = finalize_pipeline_response(
        session,
        "line:Utest",
        MagicMock(),
        before,
        ({"status": "ok"}, 200),
        user_message="頭が痛い",
    )

    assert status == 200
    assert body.get("pipeline_end_guard") != "missing"
    assert count_bot_messages_in_session(session) == before + 1


def test_finalize_pipeline_response_missing_without_bot_in_memory():
    session = {"messages": [{"type": "user", "content": "頭が痛い"}]}
    before = count_bot_messages_in_session(session)

    body, _status = finalize_pipeline_response(
        session,
        "line:Utest",
        MagicMock(),
        before,
        ({"status": "ok"}, 200),
        user_message="頭が痛い",
    )

    assert body.get("pipeline_end_guard") == "missing"
    assert session.get("_pipeline_end_guard") == "missing"
