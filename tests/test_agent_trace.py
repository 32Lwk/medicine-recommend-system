"""agent_trace JSONL"""
import json
from pathlib import Path

from src.utils.agent_trace import log_agent_step


def test_log_agent_step_writes_jsonl(tmp_path, monkeypatch):
    import src.utils.agent_trace as at

    monkeypatch.setattr(at, "_TRACE_DIR", str(tmp_path))
    log_agent_step("trace-1", "TriageAgent", "complete", sid="s", ms=12.5, payload={"category": "Physical"})
    log_file = tmp_path / "agent_trace.jsonl"
    assert log_file.exists()
    line = json.loads(log_file.read_text(encoding="utf-8").strip().splitlines()[-1])
    assert line["trace_id"] == "trace-1"
    assert line["agent"] == "TriageAgent"
