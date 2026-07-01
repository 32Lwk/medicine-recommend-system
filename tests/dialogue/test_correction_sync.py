"""correction 検出 → dialogue_state 同期テスト（Wave 2）。"""
from __future__ import annotations

from src.dialogue.sync_legacy import mark_correction_in_dialogue_state


def test_mark_correction_sets_flag(monkeypatch):
    monkeypatch.setenv("CHAT_PIPELINE_V2", "true")
    session: dict = {}
    mark_correction_in_dialogue_state(session, "line:U1", "違う、熱がある")
    assert session["dialogue_state"]["flags"]["correction_detected"] is True


def test_no_correction_no_flag(monkeypatch):
    monkeypatch.setenv("CHAT_PIPELINE_V2", "true")
    session: dict = {}
    mark_correction_in_dialogue_state(session, "line:U1", "頭痛い")
    assert "correction_detected" not in session.get("dialogue_state", {}).get("flags", {})


def test_correction_skipped_when_v2_off(monkeypatch):
    monkeypatch.delenv("CHAT_PIPELINE_V2", raising=False)
    session: dict = {}
    mark_correction_in_dialogue_state(session, "line:U1", "違う、熱がある")
    assert "dialogue_state" not in session
