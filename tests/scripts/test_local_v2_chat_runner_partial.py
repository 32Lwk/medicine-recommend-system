"""local_v2_chat_test_runner 部分再実行ヘルパーの単体テスト。"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.local_v2_chat_test_runner import (  # noqa: E402
    ScenarioResult,
    TurnResult,
    _atomic_write_json,
    _checkpoint_path,
    _ids_from_report,
    _load_checkpoint,
    _merge_report_results,
    _save_checkpoint,
)


def test_ids_from_report_all():
    report = {
        "results": [
            {"scenario_id": "a", "auto_pass": True},
            {"scenario_id": "b", "auto_pass": False},
        ]
    }
    assert _ids_from_report(report, failed_only=False) == ["a", "b"]


def test_ids_from_report_failed_only():
    report = {
        "results": [
            {"scenario_id": "a", "auto_pass": True},
            {"scenario_id": "b", "auto_pass": False},
            {"scenario_id": "c", "auto_pass": False},
        ]
    }
    assert _ids_from_report(report, failed_only=True) == ["b", "c"]


def test_merge_report_results_overwrites_by_scenario_id():
    base = [
        {"scenario_id": "s1", "category": "store", "auto_pass": False, "turns": []},
        {"scenario_id": "s2", "category": "store", "auto_pass": True, "turns": []},
    ]
    new = [
        ScenarioResult(
            scenario_id="s1",
            category="store",
            wave="v2",
            session_id="sid-new",
            turns=[TurnResult(turn_index=0, user_message="hi", http_status=200, elapsed_ms=10)],
            auto_pass=True,
        ),
        ScenarioResult(
            scenario_id="s3",
            category="counseling",
            wave="v2",
            session_id="sid-3",
            turns=[],
            auto_pass=True,
        ),
    ]
    merged = _merge_report_results(base, new)
    assert [r.scenario_id for r in merged] == ["s1", "s2", "s3"]
    assert merged[0].auto_pass is True
    assert merged[0].session_id == "sid-new"
    assert merged[1].auto_pass is True


def test_checkpoint_atomic_write_and_load(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    ck = tmp_path / "test.checkpoint.json"

    def _fake_checkpoint_path(_date: str, _suffix: str) -> Path:
        return ck

    monkeypatch.setattr(
        "scripts.local_v2_chat_test_runner._checkpoint_path",
        _fake_checkpoint_path,
    )

    results = [
        ScenarioResult(
            scenario_id="x1",
            category="store",
            wave="v2",
            session_id="s1",
            turns=[],
            auto_pass=True,
        )
    ]
    meta = {"date": "2026-07-02", "report_suffix": "partial-test"}
    _save_checkpoint(ck, meta=meta, results=results)

    assert ck.is_file()
    assert not ck.with_suffix(ck.suffix + ".tmp").exists()

    loaded_meta, loaded_results = _load_checkpoint(ck)
    assert loaded_meta["report_suffix"] == "partial-test"
    assert len(loaded_results) == 1
    assert loaded_results[0].scenario_id == "x1"


def test_atomic_write_json_no_tmp_left(tmp_path: Path):
    path = tmp_path / "out.json"
    _atomic_write_json(path, {"ok": True})
    assert json.loads(path.read_text(encoding="utf-8")) == {"ok": True}
    assert not path.with_suffix(path.suffix + ".tmp").exists()


def test_checkpoint_path_format():
    p = _checkpoint_path("2026-07-02", "p4b2-smoke")
    assert p.name == "2026-07-02_local_v2_chat_test_p4b2-smoke.checkpoint.json"
