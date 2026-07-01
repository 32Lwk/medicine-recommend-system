"""SessionAgent のルーティング・分類テスト。"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from src.agents.memory_delete_agent import classify_memory_delete_intent
from src.agents.session_agent import (
    classify_session_intent,
    probe_session_admin_intent,
    try_handle_session_request,
)


def test_classify_session_intent_delete_variants():
    assert classify_session_intent("履歴消して") == "delete"
    assert classify_session_intent("記憶を消して") == "delete"
    assert classify_memory_delete_intent("履歴消して", client=None).get("is_delete_request") is True


def test_classify_session_intent_status():
    assert classify_session_intent("ステータスを教えて") == "status"
    assert probe_session_admin_intent("ステータスを教えて") == "status"


def test_classify_session_intent_summarize():
    assert classify_session_intent("履歴を要約して") == "summarize"
    assert probe_session_admin_intent("履歴を要約して") == "summarize"


def test_classify_session_intent_via_triage_session_admin():
    triage = {"subcategory": "session_admin", "category": "Other"}
    assert classify_session_intent("状態は？", triage_result=triage) == "status"
    assert classify_session_intent("要約して", triage_result=triage) == "summarize"


def test_classify_session_intent_via_meta_session_ops():
    triage = {"concierge_intent": "session_ops", "category": "Other"}
    assert classify_session_intent("履歴消して", triage_result=triage) == "delete"


@patch("src.services.line_user_memory.is_line_memory_session", return_value=True)
@patch("src.services.line_user_memory.resolve_memory_owner_sid", return_value="line:Utest")
@patch("src.agents.session_agent.classify_memory_delete_intent")
def test_try_handle_delete_requests_confirmation(mock_classify, _owner, _is_line):
    mock_classify.return_value = {"is_delete_request": True, "scope": "all"}
    session: dict = {"messages": []}
    client = MagicMock()
    resp = try_handle_session_request(session, "line:Utest", "履歴消して", client)
    assert resp is not None
    assert session.get("pending_memory_delete", {}).get("scope") == "all"
    assert len(session["messages"]) == 2
    assert session["messages"][-1]["session_agent_kind"] == "delete_confirm"


@patch("src.services.line_user_memory.is_line_memory_session", return_value=True)
@patch("src.services.line_user_memory.resolve_memory_owner_sid", return_value="line:Utest")
@patch("src.services.line_user_memory.load_line_memory", return_value=({"age": 30}, []))
@patch("src.services.session_manager.get_line_session_admin_snapshot", return_value={"messages": [], "session_active": True})
def test_try_handle_status(_snap, _load, _owner, _is_line):
    session: dict = {"messages": []}
    resp = try_handle_session_request(
        session,
        "line:Utest",
        "ステータスを教えて",
        MagicMock(),
    )
    assert resp is not None
    bot = session["messages"][-1]
    assert bot.get("session_agent_kind") == "status"
    diag = bot.get("diagnosis") or {}
    assert diag.get("kind") == "session_integrated_status"


def test_classify_session_intent_status_vocab():
    assert classify_session_intent("何が記録されてる？") == "status"
    assert classify_session_intent("記録を教えて") == "status"


@patch("src.services.line_user_memory.is_line_memory_session", return_value=True)
@patch("src.services.line_user_memory.resolve_memory_owner_sid", return_value="line:Utest")
def test_pending_delete_cancel_phrase_variants(_owner, _is_line):
    session: dict = {
        "messages": [],
        "pending_memory_delete": {"scope": "all", "owner": "line:Utest"},
    }
    resp = try_handle_session_request(session, "line:Utest", "やっぱり消さない", MagicMock())
    assert resp is not None
    assert "pending_memory_delete" not in session


@patch("src.services.line_user_memory.is_line_memory_session", return_value=True)
@patch("src.services.line_user_memory.resolve_memory_owner_sid", return_value="line:Utest")
def test_pending_delete_cancelled_for_headache(_owner, _is_line):
    session: dict = {
        "messages": [],
        "pending_memory_delete": {"scope": "all", "owner": "line:Utest"},
    }
    resp = try_handle_session_request(session, "line:Utest", "頭痛い", MagicMock())
    assert resp is None
    assert "pending_memory_delete" not in session


@patch("src.services.line_user_memory.is_line_memory_session", return_value=True)
@patch("src.services.line_user_memory.resolve_memory_owner_sid", return_value="line:Utest")
def test_pending_delete_cancelled_mirrors_v2_flag(_owner, _is_line, monkeypatch):
    monkeypatch.setenv("CHAT_PIPELINE_V2", "true")
    session: dict = {
        "messages": [],
        "pending_memory_delete": {"scope": "all", "owner": "line:Utest"},
    }
    resp = try_handle_session_request(session, "line:Utest", "39度の熱があります", MagicMock())
    assert resp is None
    assert "pending_memory_delete" not in session
    assert session["dialogue_state"]["flags"]["pending_cancelled_by_physical"] is True


@patch("src.services.line_user_memory.is_line_memory_session", return_value=True)
@patch("src.services.line_user_memory.resolve_memory_owner_sid", return_value="line:Utest")
@patch("src.agents.session_agent.classify_memory_delete_intent")
def test_delete_not_forced_on_physical_triage(mock_classify, _owner, _is_line):
    mock_classify.return_value = {"is_delete_request": False}
    session: dict = {"messages": []}
    triage = {
        "category": "Physical",
        "confidence": 0.99,
        "subcategory": "fever",
        "session_intent": "delete",
    }
    resp = try_handle_session_request(
        session,
        "line:Utest",
        "頭痛い",
        MagicMock(),
        triage_result=triage,
    )
    assert resp is None
    assert "pending_memory_delete" not in session


@patch("src.services.line_user_memory.is_line_memory_session", return_value=True)
@patch("src.services.line_user_memory.resolve_memory_owner_sid", return_value="line:Utest")
@patch("src.agents.session_agent.classify_memory_delete_intent")
def test_delete_still_works_with_session_intent(mock_classify, _owner, _is_line):
    mock_classify.return_value = {"is_delete_request": False}
    session: dict = {"messages": []}
    triage = {"category": "Other", "session_intent": "delete", "subcategory": "session_admin"}
    resp = try_handle_session_request(
        session,
        "line:Utest",
        "整理して",
        MagicMock(),
        triage_result=triage,
    )
    assert resp is not None
    assert session.get("pending_memory_delete")


@patch("src.services.line_user_memory.is_line_memory_session", return_value=False)
def test_non_line_session_skipped(_is_line):
    session: dict = {"messages": []}
    assert (
        try_handle_session_request(session, "web-1", "ステータスを教えて", MagicMock())
        is None
    )


def test_persist_session_includes_pending_memory_delete():
    from unittest.mock import patch

    from src.services.session_manager import persist_session_from_chat_state

    session = {
        "messages": [],
        "pending_memory_delete": {"scope": "all", "owner": "line:Utest"},
    }

    with patch("src.services.session_manager.get_session_from_db", return_value={}):
        with patch("src.services.session_manager.ensure_session_persisted") as ensure:
            persist_session_from_chat_state("line:Utest", session)
            payload = ensure.call_args[0][1]
            assert payload["pending_memory_delete"]["scope"] == "all"
