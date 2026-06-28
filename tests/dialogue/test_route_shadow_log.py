"""dialogue_route_shadow 構造化ログのテスト。"""
from __future__ import annotations

import json

from src.utils.structured_logger import emit_dialogue_route_shadow


def test_emit_dialogue_route_shadow_writes_jsonl(tmp_path, monkeypatch):
    log_dir = tmp_path / "log"
    log_dir.mkdir()
    monkeypatch.setattr("src.utils.structured_logger.LOG_DIR", str(log_dir))

    emit_dialogue_route_shadow(
        session_id="line:U1",
        user_input="頭痛い",
        decision={
            "primary_route": "Physical",
            "sub_route": "rule_based_recommend",
            "resolved_by": "gate",
            "confidence": 0.9,
            "source": "test",
        },
        triage_category="Physical",
        triage_subcategory="headache",
        mismatch=False,
    )

    jsonl = log_dir / "dialogue_route_shadow_log.jsonl"
    assert jsonl.is_file()
    row = json.loads(jsonl.read_text(encoding="utf-8").strip())
    assert row["log_type"] == "dialogue_route_shadow"
    assert row["session_id"] == "line:U1"
    assert row["primary_route"] == "Physical"
    assert row["mismatch"] is False


def test_emit_dialogue_route_shadow_mismatch_warning_level(tmp_path, monkeypatch):
    log_dir = tmp_path / "log"
    log_dir.mkdir()
    monkeypatch.setattr("src.utils.structured_logger.LOG_DIR", str(log_dir))

    emit_dialogue_route_shadow(
        session_id="line:U2",
        user_input="頭痛い",
        decision={"primary_route": "Physical", "sub_route": None, "resolved_by": "gate"},
        triage_category="Other",
        mismatch=True,
    )

    row = json.loads((log_dir / "dialogue_route_shadow_log.jsonl").read_text(encoding="utf-8").strip())
    assert row["mismatch"] is True
