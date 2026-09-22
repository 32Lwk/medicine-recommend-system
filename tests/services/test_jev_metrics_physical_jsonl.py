"""Physical shadow JSONL file verification (tmp dir; never commit outputs)."""
from __future__ import annotations

import json
from pathlib import Path

from src.services import jev_metrics as jm


def setup_function() -> None:
    jm.clear_execution_registry_for_tests()


def test_physical_shadow_jsonl_append_restart_and_privacy(tmp_path, monkeypatch) -> None:
    """Write real JSONL under tmp_path — no paid API, no repo log pollution."""
    import src.utils.structured_logger as sl

    monkeypatch.setattr(sl, "LOG_DIR", str(tmp_path))
    jsonl_path = Path(tmp_path) / jm.LOG_FILE

    legacy = {"primary_route": "Physical", "sub_route": "medicine_qa"}
    cid1 = "corr-physical-jsonl-001"
    cid2 = "corr-physical-jsonl-002"

    jm.notify_executed_decision(cid1, legacy)
    row1 = jm.record_shadow_event(
        correlation_id=cid1,
        legacy_decision=legacy,
        jev_decision=None,
        model="mock-jev",
        mode="shadow",
        attempted=False,
        succeeded=False,
        failure_reason="not_eligible",
        error_class="none",
        latency_ms=12.5,
        sid="line:U-secret-should-hash",
        extra={
            "jev_eligible": False,
            "jev_eligibility_reason": "sessionops_fast_path",
            "jev_attempted": False,
        },
    )
    assert row1 is not None
    assert jsonl_path.is_file()

    # Restart-equivalent: drop in-memory registry, reopen file, append again.
    jm.clear_execution_registry_for_tests()
    jm.notify_executed_decision(cid2, legacy)
    row2 = jm.record_shadow_event(
        correlation_id=cid2,
        legacy_decision=legacy,
        jev_decision={
            "primary_route": "Physical",
            "sub_route": "medicine_qa",
            "primary_confidence": 0.9,
        },
        model="mock-jev",
        mode="shadow",
        attempted=True,
        succeeded=True,
        latency_ms=210.0,
        usage={"input_tokens": 10, "output_tokens": 5, "total_tokens": 15},
        sid="line:U-another-secret",
        state_shape={"recent_turn_count": 2, "user_input_len": 12},
        extra={"jev_eligible": True, "jev_attempted": True},
    )
    assert row2 is not None

    lines = jsonl_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) >= 2

    parsed = [json.loads(line) for line in lines]
    for payload in parsed:
        assert payload.get("schema_version") == jm.SCHEMA_VERSION
        assert payload.get("log_type") == "jev_intent_router_shadow"
        assert payload.get("correlation_id")
        # Privacy / denylist
        for forbidden in jm.FORBIDDEN_LOG_KEYS:
            assert forbidden not in payload
        blob = json.dumps(payload, ensure_ascii=False)
        assert "line:U-secret" not in blob
        assert "U-secret-should-hash" not in blob
        assert "sk-" not in blob.lower()
        assert "system prompt" not in blob.lower()
        assert "authorization" not in blob.lower()
        # History must not exceed 5 turns even if shape reports counts
        turns = (payload.get("state_shape") or {}).get("recent_turn_count")
        if turns is not None:
            assert int(turns) <= 5
        completeness = jm.assess_event_completeness(payload)
        assert completeness["schema_version"] == jm.SCHEMA_VERSION

    # Correlation IDs must bind distinct rows
    cids = {p.get("correlation_id") for p in parsed}
    assert cid1 in cids and cid2 in cids

    # Generated file stays under tmp — not the repo log/ path
    assert "medicine-recommend" not in str(jsonl_path) or str(tmp_path) in str(jsonl_path)
    assert jsonl_path.parent == tmp_path
