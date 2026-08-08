"""dialogue_turn_trace 読み書きテスト。"""
from __future__ import annotations

import json
import os
import tempfile

from src.services.dialogue_turn_trace import (
    append_dialogue_turn_trace,
    load_traces_for_session,
    prompt_turns_for_latest_trace,
    trace_log_path,
)


def test_trace_roundtrip(tmp_path, monkeypatch):
    log_dir = tmp_path / "log"
    log_dir.mkdir()
    path = str(log_dir / "dialogue_turn_trace.jsonl")
    monkeypatch.setattr(
        "src.services.dialogue_turn_trace.trace_log_path",
        lambda: path,
    )

    append_dialogue_turn_trace(
        session_id="test-sid-1",
        user_message="ロキソニン",
        route="medicine_qa",
        prompt_turns=3,
        source="test",
    )
    # 非同期書き込み待ち
    import time

    time.sleep(0.3)

    rows = load_traces_for_session("test-sid-1", path=path)
    assert len(rows) >= 1
    assert rows[-1].get("prompt_turns") == 3
    assert prompt_turns_for_latest_trace("test-sid-1", path=path) == 3
