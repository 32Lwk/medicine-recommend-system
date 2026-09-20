"""tests for src.services.jev_metrics (Phase 1B)."""
from __future__ import annotations

from unittest.mock import patch

from src.services import jev_metrics as jm


def setup_function() -> None:
    jm.clear_execution_registry_for_tests()


def test_trace_hash_never_equals_raw_sid():
    sid = "line:U-secret-user-id"
    h = jm.trace_hash_for_sid(sid)
    assert h is not None
    assert sid not in h
    assert "U-secret" not in h
    assert len(h) == 32


def test_estimate_jev_cost_usd():
    # 1_000_000 tokens -> $0.042
    assert jm.estimate_jev_cost_usd(1_000_000) == 0.042
    assert jm.estimate_jev_cost_usd(None) is None
    assert jm.estimate_jev_cost_usd("bad") is None


def test_compute_matched_exact():
    legacy = {"primary_route": "Physical", "sub_route": "medicine_qa"}
    jev = {"primary_route": "Physical", "sub_route": "medicine_qa"}
    m = jm.compute_matched(legacy, jev)
    assert m["primary"] is True
    assert m["sub"] is True
    assert m["exact"] is True


def test_normalize_sub_route_emergency_aliases():
    assert (
        jm.normalize_sub_route("Emergency", "chest_pain_breathing_difficulty")
        == "emergency_dispatch"
    )
    assert (
        jm.normalize_sub_route("Emergency", "chest_pain_breathlessness")
        == "emergency_dispatch"
    )
    assert jm.normalize_sub_route("Emergency", "emergency_dispatch") == "emergency_dispatch"
    # Non-Emergency primary must not rewrite chest_pain_* labels.
    assert (
        jm.normalize_sub_route("Physical", "chest_pain_breathing_difficulty")
        == "chest_pain_breathing_difficulty"
    )


def test_normalize_sub_route_session_delete_alias():
    assert jm.normalize_sub_route("SessionOps", "delete_confirm") == "delete"
    assert jm.normalize_sub_route("SessionOps", "delete") == "delete"
    assert jm.normalize_sub_route("Physical", "delete_confirm") == "delete_confirm"


def test_compute_matched_sub_route_aliases():
    m_em = jm.compute_matched(
        {"primary_route": "Emergency", "sub_route": "chest_pain_breathing_difficulty"},
        {"primary_route": "Emergency", "sub_route": "emergency_dispatch"},
    )
    assert m_em["primary"] is True
    assert m_em["sub"] is True
    assert m_em["exact"] is True
    assert m_em["safety"] is True

    m_em2 = jm.compute_matched(
        {"primary_route": "Emergency", "sub_route": "chest_pain_breathlessness"},
        {"primary_route": "Emergency", "sub_route": "emergency_dispatch"},
    )
    assert m_em2["sub"] is True
    assert m_em2["exact"] is True

    m_sess = jm.compute_matched(
        {"primary_route": "SessionOps", "sub_route": "delete"},
        {"primary_route": "SessionOps", "sub_route": "delete_confirm"},
    )
    assert m_sess["primary"] is True
    assert m_sess["sub"] is True
    assert m_sess["exact"] is True

    # Real sub mismatch remains a disagreement.
    m_real = jm.compute_matched(
        {"primary_route": "Physical", "sub_route": "fever"},
        {"primary_route": "Physical", "sub_route": "medicine_qa"},
    )
    assert m_real["sub"] is False
    assert m_real["exact"] is False
    assert jm.compute_disagreement_class(
        {"primary_route": "Emergency", "sub_route": "chest_pain_breathing_difficulty"},
        {"primary_route": "Emergency", "sub_route": "emergency_dispatch"},
    ) == "none"


def test_compute_matched_safety_mismatch():
    legacy = {"primary_route": "Emergency", "sub_route": None}
    jev = {"primary_route": "Physical", "sub_route": None}
    m = jm.compute_matched(legacy, jev)
    assert m["primary"] is False
    assert m["safety"] is False
    assert m["exact"] is False


def test_notify_and_lookup_executed():
    jm.notify_executed_decision(
        "cid-1",
        {"primary_route": "Store", "sub_route": "locator", "source": "legacy"},
    )
    got = jm.lookup_executed_decision("cid-1")
    assert got["primary_route"] == "Store"


def test_record_shadow_event_write_failure_does_not_raise():
    with patch(
        "src.utils.structured_logger._write_to_jsonl",
        side_effect=OSError("disk full"),
    ):
        result = jm.record_shadow_event(
            correlation_id="c-fail",
            legacy_decision={"primary_route": "Physical"},
            jev_decision=None,
            attempted=True,
            succeeded=False,
            fallback_reason="log_error",
            error_class="OSError",
            state_shape={"recent_turn_count": 0, "user_input_len": 3},
            sid="should-not-appear",
        )
    # 外枠の record は例外を握りつぶし payload を返す（emit 内失敗は debug）
    assert result is not None
    assert result["log_type"] == "jev_intent_router_shadow"
    assert result["mode"] == "shadow"
    assert result["adapter_mode"] == "minimal"
    assert result["legacy_saved_calls"] == 0
    assert "should-not-appear" not in str(result)
    assert result["trace_hash"] != "should-not-appear"


def test_record_shadow_event_outer_failure_returns_none():
    with patch(
        "src.services.jev_metrics._route_fields",
        side_effect=RuntimeError("boom"),
    ):
        assert (
            jm.record_shadow_event(
                correlation_id="c",
                legacy_decision={"primary_route": "X"},
            )
            is None
        )


def test_record_uses_notified_executed_decision():
    jm.notify_executed_decision(
        "corr-join",
        {"primary_route": "Counseling", "sub_route": None, "source": "legacy"},
    )
    captured = {}

    def _capture(log_file, data):
        captured["file"] = log_file
        captured["data"] = data

    with patch("src.utils.structured_logger._write_to_jsonl", side_effect=_capture):
        jm.record_shadow_event(
            correlation_id="corr-join",
            legacy_decision={"primary_route": "Physical", "sub_route": "fever"},
            jev_decision={
                "primary_route": "Physical",
                "sub_route": "fever",
                "primary_confidence": 0.9,
            },
            executed_decision=None,
            model="jev-latest",
            succeeded=True,
            usage={"input_tokens": 1358, "output_tokens": 368},
            state_shape=jm.build_state_shape(
                {
                    "channel": "web",
                    "user_input": "secret text must not appear",
                    "recent_turns": [{"role": "user", "content": "x"}],
                    "meta": {"last_recommended_medicines": ["A", "B"]},
                    "app_context": "ctx",
                }
            ),
            sid="raw-sid-xyz",
        )

    assert captured["file"] == "jev_intent_router_shadow.jsonl"
    data = captured["data"]
    assert data["executed_decision"]["primary_route"] == "Counseling"
    assert data["jev_cost_usd"] is not None
    assert "secret text" not in str(data)
    assert "raw-sid-xyz" not in str(data)
    assert data["state_shape"]["recent_turn_count"] == 1
    assert data["state_shape"]["recommended_medicine_count"] == 2
    assert "user_input" not in data


def test_notify_failure_non_propagating():
    # 壊れた OrderedDict 操作を模擬 — 例外は握りつぶす
    with patch.object(
        jm._executed_by_correlation,
        "__setitem__",
        side_effect=RuntimeError("nope"),
    ):
        jm.notify_executed_decision("x", {"primary_route": "X"})  # must not raise


def test_disagreement_class_priority():
    assert (
        jm.compute_disagreement_class(
            {"primary_route": "Physical", "sub_route": "a"},
            {"primary_route": "Physical", "sub_route": "a"},
        )
        == "none"
    )
    assert (
        jm.compute_disagreement_class(
            {"primary_route": "Emergency", "sub_route": None},
            {"primary_route": "Physical", "sub_route": None},
        )
        == "high_risk_signal"
    )
    assert (
        jm.compute_disagreement_class(
            {"primary_route": "Store", "sub_route": "locator"},
            {"primary_route": "Physical", "sub_route": "fever"},
        )
        == "primary_route"
    )
    assert (
        jm.compute_disagreement_class(
            {"primary_route": "Physical", "sub_route": "fever"},
            {"primary_route": "Physical", "sub_route": "medicine_qa"},
        )
        == "sub_route"
    )
    assert (
        jm.compute_disagreement_class(
            {"primary_route": "Physical", "sub_route": "fever"},
            {"primary_route": "Physical", "sub_route": "fever"},
            executed_decision={"primary_route": "Counseling", "sub_route": None},
        )
        == "execution_effect"
    )
    assert (
        jm.compute_disagreement_class(
            {"primary_route": "Physical"},
            None,
        )
        == "none"
    )


def test_record_includes_disagreement_class():
    captured = {}

    def _capture(log_file, data):
        captured["data"] = data

    with patch("src.utils.structured_logger._write_to_jsonl", side_effect=_capture):
        jm.record_shadow_event(
            correlation_id="d1",
            legacy_decision={"primary_route": "Store", "sub_route": "locator"},
            jev_decision={"primary_route": "Physical", "sub_route": None},
            executed_decision={"primary_route": "Store", "sub_route": "locator"},
            succeeded=True,
        )
    assert captured["data"]["disagreement_class"] == "primary_route"
    assert captured["data"]["disagreement_class"] in jm.DISAGREEMENT_CLASSES


def test_state_shape_counts_both_aliases_and_flags_mismatch():
    ok_shape = jm.build_state_shape(
        {
            "channel": "web",
            "user_input": "x",
            "recent_turns": [{"role": "user", "content": "a"}],
            "recent_context": [{"role": "user", "content": "a"}],
            "meta": {},
            "app_context": "c",
        }
    )
    assert ok_shape["recent_turn_count"] == 1
    assert ok_shape["recent_context_count"] == 1
    assert ok_shape["recent_context_mismatch"] is False

    bad_shape = jm.build_state_shape(
        {
            "recent_turns": [{"role": "user", "content": "a"}],
            "recent_context": [
                {"role": "user", "content": "a"},
                {"role": "assistant", "content": "b"},
            ],
            "meta": {},
        }
    )
    assert bad_shape["recent_turn_count"] == 1
    assert bad_shape["recent_context_count"] == 2
    assert bad_shape["recent_context_mismatch"] is True

    captured = {}

    def _capture(log_file, data):
        captured["data"] = data

    with patch("src.utils.structured_logger._write_to_jsonl", side_effect=_capture):
        jm.record_shadow_event(
            correlation_id="mismatch-1",
            legacy_decision={"primary_route": "Physical"},
            jev_decision={"primary_route": "Physical"},
            state_shape=bad_shape,
            succeeded=True,
        )
    assert captured["data"]["error_class"] == "recent_context_mismatch"
    assert captured["data"]["state_shape"]["recent_context_mismatch"] is True
