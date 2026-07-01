"""SessionOps / gate / empty reco の追加テスト。"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from src.agents.session_agent import (
    classify_session_intent,
    try_handle_session_request,
)
from src.dialogue.routing.gate import run_deterministic_gate
from src.handlers.chat.chat_recommendation_flow import _build_empty_recommendation_fallback


def test_saved_info_classified_as_status_not_delete() -> None:
    assert classify_session_intent("保存されている情報は？") == "status"
    assert classify_session_intent("保存されている情報は？") != "delete"


def test_cancel_phrase_not_classified_as_delete() -> None:
    assert classify_session_intent("やっぱり消さない") == "none"


@patch("src.services.line_user_memory.is_line_memory_session", return_value=True)
@patch("src.services.line_user_memory.resolve_memory_owner_sid", return_value="line:U1")
@patch("src.services.session_manager.save_session_to_db")
@patch("src.services.session_manager.get_session_from_db", return_value={})
def test_pending_delete_explain_mode(_get, _save, _owner, _is_line) -> None:
    session = {
        "messages": [],
        "pending_memory_delete": {"scope": "all", "owner": "line:U1"},
    }
    resp = try_handle_session_request(
        session,
        "line:U1",
        "何が削除されますか？",
        MagicMock(),
    )
    assert resp is not None
    assert resp[1] == 200
    bot = session["messages"][-1]
    diag = bot.get("diagnosis") or {}
    assert diag.get("kind") == "memory_delete_explain"
    assert "削除対象" in str(diag.get("message") or "")


def test_gate_physical_lifestyle_during_consultation() -> None:
    session = {
        "physical_consultation_active": True,
        "messages": [
            {"type": "user", "content": "頭痛い"},
            {"type": "bot", "diagnosis": {"render": "sage_reco", "recommended_medicines": [{"product_name": "A"}]}},
        ],
    }
    d = run_deterministic_gate("運動は週に2回しています", session, "web-1")
    assert d is not None
    assert d.primary_route == "Physical"
    assert d.source == "physical_consultation_lifestyle"


def test_gate_counseling_followup_still_works() -> None:
    session = {
        "counseling_mode": {"active": True, "symptom_type": "insomnia"},
        "messages": [{"type": "user", "content": "最近眠れません"}],
    }
    d = run_deterministic_gate("2週間くらいです", session, "web-1")
    assert d is not None
    assert d.primary_route == "Counseling"


def test_empty_recommendation_fallback_returns_status() -> None:
    session: dict = {"messages": []}
    resp = _build_empty_recommendation_fallback(
        session,
        "web-1",
        {"doctor_consultation": "医療機関への受診をお勧めします。"},
        "子どもが熱",
    )
    assert resp[1] == 200
    bot = session["messages"][-1]
    diag = bot.get("diagnosis") or {}
    assert diag.get("kind") == "no_recommendation"
    assert diag.get("render") == "sage_status"
