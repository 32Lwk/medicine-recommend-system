"""dialogue sync_legacy テスト。"""
from __future__ import annotations

from src.dialogue.sync_legacy import mirror_counseling_mode, mirror_handoff, sync_dialogue_legacy_mirrors


def test_mirror_counseling_mode_v2(monkeypatch):
    monkeypatch.setenv("CHAT_PIPELINE_V2", "true")
    session = {"counseling_mode": {"active": True, "symptom_type": "insomnia"}}
    mirror_counseling_mode(session, "line:U1")
    assert session["dialogue_state"]["counseling"]["active"] is True
    assert session["dialogue_state"]["counseling"]["theme"] == "insomnia"


def test_mirror_handoff_v2(monkeypatch):
    monkeypatch.setenv("CHAT_PIPELINE_V2", "true")
    session = {"agent_handoff": "CounselingManager"}
    mirror_handoff(session, "line:U2")
    assert session["dialogue_state"]["handoff"]["target"] == "CounselingManager"
    assert session["dialogue_state"]["handoff"]["active_channel"] == "line"


def test_sync_skipped_when_v2_off(monkeypatch):
    monkeypatch.delenv("CHAT_PIPELINE_V2", raising=False)
    session = {"counseling_mode": {"active": True}, "agent_handoff": "X"}
    sync_dialogue_legacy_mirrors(session, "line:U1")
    assert "dialogue_state" not in session


def test_mirror_concierge_state_v2(monkeypatch):
    monkeypatch.setenv("CHAT_PIPELINE_V2", "true")
    from src.dialogue.sync_legacy import mirror_concierge_state

    session = {
        "concierge_state": {"last_intent": "architecture", "off_topic_turns": 2},
    }
    mirror_concierge_state(session, "line:U6")
    assert session["dialogue_state"]["concierge"]["last_intent"] == "architecture"
    assert session["dialogue_state"]["concierge"]["off_topic_turns"] == 2


def test_mirror_fever_context_v2(monkeypatch):
    monkeypatch.setenv("CHAT_PIPELINE_V2", "true")
    from src.dialogue.sync_legacy import mirror_fever_context

    session = {"_fever_context_active": True}
    mirror_fever_context(session, "line:U4")
    assert session["dialogue_state"]["flags"]["fever_context"] is True


def test_mirror_pending_medical_cancel(monkeypatch):
    monkeypatch.setenv("CHAT_PIPELINE_V2", "true")
    from src.dialogue.sync_legacy import mirror_pending_medical_cancel

    session = {
        "dialogue_state": {
            "version": 1,
            "pending": {"session_delete": {"scope": "all"}},
        }
    }
    mirror_pending_medical_cancel(session, "line:U3")
    assert session["dialogue_state"]["flags"]["pending_cancelled_by_physical"] is True
    assert "session_delete" not in session["dialogue_state"]["pending"]


def test_clear_pending_medical_cancel_flag(monkeypatch):
    monkeypatch.setenv("CHAT_PIPELINE_V2", "true")
    from src.dialogue.sync_legacy import clear_pending_medical_cancel_flag

    session = {
        "dialogue_state": {
            "version": 1,
            "flags": {"pending_cancelled_by_physical": True},
        }
    }
    clear_pending_medical_cancel_flag(session, "line:U5")
    assert "pending_cancelled_by_physical" not in session["dialogue_state"]["flags"]


def test_clear_pending_memory_delete_syncs_dialogue_state(monkeypatch):
    monkeypatch.setenv("CHAT_PIPELINE_V2", "true")
    from src.agents.session_agent import _clear_pending_memory_delete

    session = {
        "pending_memory_delete": {"scope": "all", "owner": "line:U7"},
        "dialogue_state": {
            "version": 1,
            "pending": {"session_delete": {"scope": "all"}},
        },
    }
    _clear_pending_memory_delete(session, "line:U7")
    assert "pending_memory_delete" not in session
    assert "session_delete" not in session["dialogue_state"]["pending"]


def test_mirror_pending_session_delete(monkeypatch):
    monkeypatch.setenv("CHAT_PIPELINE_V2", "true")
    from src.dialogue.sync_legacy import mirror_pending_session_delete

    session = {"pending_memory_delete": {"scope": "all", "owner": "line:U1"}}
    mirror_pending_session_delete(session, "line:U1")
    assert session["dialogue_state"]["pending"]["session_delete"]["scope"] == "all"


def test_load_merges_counseling_and_handoff():
    from src.dialogue.context import load_dialogue_context

    session = {
        "counseling_mode": {"active": True, "symptom_type": "sleepiness"},
        "agent_handoff": "PhysicalOrchestrator",
    }
    ctx = load_dialogue_context(session)
    assert ctx["counseling"]["active"] is True
    assert ctx["counseling"]["theme"] == "sleepiness"
    assert ctx["handoff"]["target"] == "PhysicalOrchestrator"
