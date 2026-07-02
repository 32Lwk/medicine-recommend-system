"""p3-correction-sessionops 4b: SessionOps 質問種別ごとの実データ応答。"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src.agents.session_agent import classify_session_ops_detail
from src.dialogue.session_ops import try_handle_session_ops

SESSION_OPS_SCENARIOS = [
    ("session-ops-01", "ステータスを教えて", "status", "session_integrated_status"),
    ("session-ops-02", "何が記録されてる？", "recorded_items", "session_recorded_items"),
    ("session-ops-03", "履歴を要約して", "summarize", "session_summary"),
    ("session-ops-04", "履歴を教えて", "history_overview", "session_history_overview"),
    ("session-ops-08", "今の状態を教えて", "status", "session_integrated_status"),
    ("session-ops-09", "セッションの状態は？", "status", "session_integrated_status"),
    ("session-ops-10", "これまでの会話をまとめて", "summarize", "session_summary"),
    ("session-ops-11", "保存されている情報は？", "recorded_items", "session_recorded_items"),
    ("session-ops-12", "要約して", "summarize", "session_summary"),
]


@pytest.mark.parametrize("scenario_id,text,detail,kind", SESSION_OPS_SCENARIOS)
def test_classify_session_ops_detail(scenario_id, text, detail, kind):
    assert classify_session_ops_detail(text) == detail


@patch("src.services.line_user_memory.is_line_memory_session", return_value=False)
@patch("src.services.session_manager.get_session_from_db", return_value={})
@pytest.mark.parametrize("scenario_id,text,detail,kind", SESSION_OPS_SCENARIOS)
def test_flag_on_distinct_kinds(_db, _is_line, monkeypatch, scenario_id, text, detail, kind):
    monkeypatch.setenv("CHAT_PIPELINE_V2", "true")
    monkeypatch.setenv("UX_SESSION_OPS_REAL_DATA", "true")
    session = {
        "messages": [
            {"type": "user", "content": "頭痛い"},
            {"type": "bot", "content": "ok"},
        ],
        "user_attributes": {"age": 30, "gender": "女性", "allergies": ["花粉"]},
    }
    with patch("src.agents.session_agent._summarize_session_llm", return_value="・頭痛の相談"):
        resp = try_handle_session_ops(session, f"web:{scenario_id}", text, MagicMock())
    assert resp is not None
    bot = session["messages"][-1]
    diag = bot.get("diagnosis") or {}
    assert diag.get("kind") == kind


@patch("src.services.line_user_memory.is_line_memory_session", return_value=False)
@patch("src.services.session_manager.get_session_from_db", return_value={})
def test_flag_on_status_vs_recorded_items_differ(_db, _is_line, monkeypatch):
    monkeypatch.setenv("CHAT_PIPELINE_V2", "true")
    monkeypatch.setenv("UX_SESSION_OPS_REAL_DATA", "true")
    client = MagicMock()

    status_session: dict = {"messages": [], "user_attributes": {"age": 25}}
    try_handle_session_ops(status_session, "web:a", "ステータスを教えて", client)
    status_msg = status_session["messages"][-1]["diagnosis"]["message"]

    recorded_session: dict = {"messages": [], "user_attributes": {"age": 25}}
    try_handle_session_ops(recorded_session, "web:b", "何が記録されてる？", client)
    recorded_msg = recorded_session["messages"][-1]["diagnosis"]["message"]

    assert status_msg != recorded_msg
    assert recorded_session["messages"][-1]["diagnosis"]["kind"] == "session_recorded_items"
    assert status_session["messages"][-1]["diagnosis"]["kind"] == "session_integrated_status"


@patch("src.services.line_user_memory.is_line_memory_session", return_value=False)
@patch("src.services.session_manager.get_session_from_db", return_value={})
def test_flag_on_summarize_vs_history_overview_differ(_db, _is_line, monkeypatch):
    monkeypatch.setenv("CHAT_PIPELINE_V2", "true")
    monkeypatch.setenv("UX_SESSION_OPS_REAL_DATA", "true")
    client = MagicMock()
    session_base = {
        "messages": [
            {"type": "user", "content": "頭痛がします"},
            {"type": "bot", "content": "ok"},
        ],
    }

    summarize_session = dict(session_base)
    summarize_session["messages"] = list(session_base["messages"])
    with patch("src.agents.session_agent._summarize_session_llm", return_value="・頭痛相談の要約"):
        try_handle_session_ops(summarize_session, "web:c", "履歴を要約して", client)
    summarize_kind = summarize_session["messages"][-1]["diagnosis"]["kind"]

    history_session = dict(session_base)
    history_session["messages"] = list(session_base["messages"])
    try_handle_session_ops(history_session, "web:d", "履歴を教えて", client)
    history_kind = history_session["messages"][-1]["diagnosis"]["kind"]

    assert summarize_kind == "session_summary"
    assert history_kind == "session_history_overview"
    assert summarize_session["messages"][-1]["diagnosis"]["message"] != history_session["messages"][-1]["diagnosis"]["message"]


@patch("src.services.line_user_memory.is_line_memory_session", return_value=False)
@patch("src.services.session_manager.get_session_from_db", return_value={})
def test_flag_off_recorded_items_uses_integrated_status(_db, _is_line, monkeypatch):
    monkeypatch.setenv("CHAT_PIPELINE_V2", "true")
    monkeypatch.delenv("UX_SESSION_OPS_REAL_DATA", raising=False)
    session: dict = {"messages": [], "user_attributes": {"age": 20}}
    try_handle_session_ops(session, "web:e", "何が記録されてる？", MagicMock())
    assert session["messages"][-1]["diagnosis"]["kind"] == "session_integrated_status"
