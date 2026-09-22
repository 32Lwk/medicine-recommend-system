"""tests for src.dialogue.routing.jev_router (Phase 1B)."""
from __future__ import annotations

import inspect
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import src.services.jev_client as jev_client_mod
import src.services.jev_decisions as jev_decisions_mod
import src.services.jev_eligibility as jev_eligibility_mod
import src.services.jev_metrics as jev_metrics_mod
from src.dialogue.routing import jev_router as jr
from src.dialogue.routing.jev_router import (
    build_jev_router_state,
    run_jev_shadow_sync,
    schedule_jev_shadow,
)


def _msgs(n: int) -> list[dict]:
    out = []
    for i in range(n):
        role = "user" if i % 2 == 0 else "bot"
        out.append({"type": role, "content": f"turn-{i}-content"})
    return out


def test_state_allowlist_zero_turns():
    session = {"messages": []}
    state = build_jev_router_state("頭痛です", session, "web-sid-1")
    assert set(state.keys()) == {
        "channel",
        "user_input",
        "recent_turns",
        "recent_context",
        "meta",
        "app_context",
    }
    assert state["recent_context"] == state["recent_turns"]
    assert state["channel"] == "web"
    assert state["user_input"] == "頭痛です"
    assert state["recent_turns"] == []
    assert "baseline_triage_hint" not in state
    assert isinstance(state["app_context"], str)


def test_state_allowlist_one_turn():
    session = {"messages": _msgs(1)}
    state = build_jev_router_state("続き", session, "sid")
    assert len(state["recent_turns"]) == 1
    assert set(state["recent_turns"][0].keys()) == {"role", "content"}


def test_state_allowlist_five_turns():
    session = {"messages": _msgs(5)}
    state = build_jev_router_state("質問", session, "sid")
    assert len(state["recent_turns"]) == 5


def test_state_allowlist_six_turns_truncates_to_five():
    session = {"messages": _msgs(6)}
    state = build_jev_router_state("質問", session, "sid")
    assert len(state["recent_turns"]) == 5
    # 末尾5件（turn-1 .. turn-5）
    assert state["recent_turns"][0]["content"] == "turn-1-content"
    assert state["recent_turns"][-1]["content"] == "turn-5-content"


def test_recent_turn_content_capped_for_payload_size():
    long_text = "あ" * (jr._MAX_RECENT_TURN_CHARS + 50)
    session = {"messages": [{"type": "user", "content": long_text}]}
    state = build_jev_router_state("質問", session, "sid")
    assert len(state["recent_turns"]) == 1
    assert len(state["recent_turns"][0]["content"]) == jr._MAX_RECENT_TURN_CHARS
    assert state["recent_turns"][0]["content"] == long_text[: jr._MAX_RECENT_TURN_CHARS]


def test_baseline_triage_hint_never_present_even_if_triage_has_category():
    session = {"messages": _msgs(2)}
    triage = {"category": "Physical", "subcategory": "fever", "confidence": 0.99}
    state = build_jev_router_state(
        "熱があります",
        session,
        "sid",
        triage_result=triage,
        medicine_qa_focus=["comparison"],
    )
    assert "baseline_triage_hint" not in state
    assert "baseline_triage_hint" not in state.get("meta", {})
    assert "category" not in state
    assert state["meta"].get("medicine_qa_focus") == ["comparison"]
    blob = str(state)
    assert "baseline_triage_hint" not in blob
    assert "Physical" not in state.get("user_input", "")


def test_line_channel_without_sending_sid():
    state = build_jev_router_state("hi", {"messages": []}, "line:U12345")
    assert state["channel"] == "line"
    assert "sid" not in state
    assert "line:U12345" not in str(state)


def test_schedule_with_flags_on_does_not_mutate_session():
    session = {
        "messages": _msgs(2),
        "dialogue_state": {"version": 1, "routing": {"primary_route": "Physical"}},
        "_routing_decision": {"primary_route": "Store"},
    }
    snapshot = {
        k: (dict(v) if isinstance(v, dict) else list(v) if isinstance(v, list) else v)
        for k, v in session.items()
    }
    state = build_jev_router_state("薬局どこ", session, "sid-x")
    legacy = {"primary_route": "Store", "sub_route": "locator", "confidence": 0.9}

    mock_result = SimpleNamespace(
        answers={"primary": "Store"},
        usage={"input_tokens": 10, "output_tokens": 2},
        retry_count=0,
        model="jev-latest",
    )
    mock_decision = SimpleNamespace(
        primary_route="Store",
        sub_route="locator",
        confidence=0.95,
        risk_flags=[],
        to_dialogue_routing_dict=lambda: {
            "primary_route": "Store",
            "sub_route": "locator",
            "confidence": 0.95,
            "source": "jev_systemone_shadow",
        },
    )
    with patch(
        "src.dialogue.routing.jev_router._is_jev_enabled", return_value=True
    ), patch(
        "src.dialogue.routing.jev_router._is_jev_intent_router_shadow_enabled",
        return_value=True,
    ), patch.object(
        jev_client_mod, "evaluate_system_one", return_value=mock_result
    ) as mock_eval, patch.object(
        jev_decisions_mod, "parse_jev_answers", return_value=mock_decision
    ), patch.object(
        jev_decisions_mod, "INTENT_ROUTER_QUESTIONS", []
    ), patch.object(jev_metrics_mod, "record_shadow_event", return_value={}):
        ok = schedule_jev_shadow(
            state=state,
            legacy_decision=legacy,
            correlation_id="corr-1",
            sync=True,
            force=True,
            sid="sid-x",
        )
        assert ok is True
        assert mock_eval.called

    assert session.get("_intent_router_shadow") is None
    assert session.get("_routing_decision") == snapshot["_routing_decision"]
    assert session.get("dialogue_state") == snapshot["dialogue_state"]
    assert session.get("messages") == snapshot["messages"]
    assert "last_triage_result" not in session


def test_sync_path_mocked_client_no_session_change():
    session = {"messages": _msgs(1), "foo": "bar"}
    before = dict(session)
    state = build_jev_router_state("test", session, "s1")
    legacy = {"primary_route": "Physical", "sub_route": None}

    mock_result = SimpleNamespace(
        answers={},
        usage={"input_tokens": 100},
        retry_count=0,
        model="jev-latest",
    )
    mock_decision = {
        "primary_route": "Physical",
        "sub_route": None,
        "confidence": 0.88,
        "source": "jev_systemone_shadow",
    }

    with patch.object(
        jev_client_mod, "evaluate_system_one", return_value=mock_result
    ) as mock_eval, patch.object(
        jev_decisions_mod, "parse_jev_answers", return_value=mock_decision
    ) as mock_parse, patch.object(
        jev_decisions_mod, "INTENT_ROUTER_QUESTIONS", [{"id": "primary"}]
    ), patch.object(
        jev_metrics_mod, "record_shadow_event", return_value={}
    ) as mock_rec:
        ok = run_jev_shadow_sync(
            state=state,
            legacy_decision=legacy,
            correlation_id="c-sync",
            sid="s1",
            force=True,
        )
        assert ok is True
        assert mock_eval.called
        assert mock_parse.called
        assert mock_rec.called

    assert session == before
    assert "_intent_router_shadow" not in session
    assert "routing" not in (session.get("dialogue_state") or {})


def test_flags_off_skips_without_force():
    state = build_jev_router_state("x", {"messages": []}, "s")
    with patch(
        "src.dialogue.routing.jev_router._is_jev_enabled", return_value=False
    ), patch(
        "src.dialogue.routing.jev_router._is_jev_intent_router_shadow_enabled",
        return_value=False,
    ):
        assert (
            schedule_jev_shadow(
                state=state,
                legacy_decision={"primary_route": "Unknown"},
                correlation_id="c",
                sync=True,
                force=False,
            )
            is False
        )


def test_meta_includes_last_routes_from_dialogue_state_not_shadow():
    session = {
        "messages": [],
        "dialogue_state": {
            "version": 1,
            "routing": {
                "primary_route": "Physical",
                "sub_route": "medicine_qa",
            },
        },
        "_intent_router_shadow": {
            "primary_route": "Emergency",
            "sub_route": None,
        },
    }
    state = build_jev_router_state("痛み", session, "sid")
    assert state["meta"]["last_primary_route"] == "Physical"
    assert state["meta"]["last_sub_route"] == "medicine_qa"


def test_forbidden_keys_raise_not_assert():
    """assert ではなく ForbiddenJevStateError（python -O でも有効）。"""
    poisoned = {
        "channel": "web",
        "user_input": "x",
        "recent_turns": [],
        "recent_context": [],
        "meta": {},
        "app_context": "ctx",
        "baseline_triage_hint": "Physical",
    }
    try:
        jr.validate_jev_state_contract(poisoned)
        raised = False
    except jr.ForbiddenJevStateError as exc:
        raised = True
        assert "baseline_triage_hint" in exc.keys
    assert raised is True

    scrubbed = dict(poisoned)
    removed = jr.scrub_forbidden_jev_state_keys(scrubbed)
    assert "baseline_triage_hint" in removed
    assert "baseline_triage_hint" not in scrubbed


def test_medicine_qa_focus_kwarg_api_accepts_injection():
    """resolve_route 未注入でも build API は medicine_qa_focus を受け取る。"""
    state = build_jev_router_state(
        "比較して",
        {"messages": []},
        "sid",
        medicine_qa_focus="comparison",
    )
    assert state["meta"]["medicine_qa_focus"] == ["comparison"]


def test_recent_context_alias_same_object_and_length():
    state = build_jev_router_state("x", {"messages": _msgs(3)}, "sid")
    assert state["recent_turns"] is state["recent_context"]
    assert len(state["recent_turns"]) == len(state["recent_context"]) == 3


def test_schedule_scrubs_poisoned_recent_alias_divergence():
    turns = [{"role": "user", "content": "a"}]
    poisoned = {
        "channel": "web",
        "user_input": "hi",
        "recent_turns": turns,
        "recent_context": turns + [{"role": "assistant", "content": "b"}],
        "meta": {},
        "app_context": "ctx",
        "baseline_triage_hint": "leak",
    }
    captured_states = []

    def _fake_eval(*, state, questions, model):
        captured_states.append(state)
        return SimpleNamespace(
            ok=True,
            answers={},
            usage={},
            retry_count=0,
            model=model,
            error_class=None,
        )

    with patch.object(
        jev_client_mod, "evaluate_system_one", side_effect=_fake_eval
    ), patch.object(
        jev_decisions_mod,
        "parse_jev_answers",
        return_value={"primary_route": "Unknown", "valid": True},
    ), patch.object(jev_decisions_mod, "INTENT_ROUTER_QUESTIONS", []), patch.object(
        jev_metrics_mod, "record_shadow_event", return_value={}
    ):
        schedule_jev_shadow(
            state=poisoned,
            legacy_decision={"primary_route": "Unknown"},
            correlation_id="scrub-1",
            sync=True,
            force=True,
        )

    assert captured_states
    sent = captured_states[0]
    assert "baseline_triage_hint" not in sent
    assert len(sent["recent_turns"]) == len(sent["recent_context"])
    assert sent["recent_turns"] is sent["recent_context"]


# --- Runtime reliability: queue / submit / shutdown / correlation / faults ---


def test_queue_saturation_records_not_eligible_and_returns_false():
    jr._reset_runtime_for_tests()
    state = build_jev_router_state("x", {"messages": []}, "sid")
    legacy = {"primary_route": "Physical"}

    with patch.object(jr, "_MAX_PENDING_SHADOW", 0), patch.object(
        jev_metrics_mod, "record_shadow_event", return_value={}
    ) as mock_rec:
        ok = schedule_jev_shadow(
            state=state,
            legacy_decision=legacy,
            correlation_id="corr-q",
            sync=False,
            force=True,
            sid="sid-q",
        )

    assert ok is False
    assert mock_rec.called
    kwargs = mock_rec.call_args.kwargs
    assert kwargs["attempted"] is False
    assert kwargs["fallback_reason"] == "not_eligible"
    assert kwargs["error_class"] == "queue_full"
    assert kwargs["correlation_id"] == "corr-q"
    jr._reset_runtime_for_tests()


def test_worker_scheduling_failure_records_submit_failed():
    jr._reset_runtime_for_tests()
    state = build_jev_router_state("x", {"messages": []}, "sid")
    legacy = {"primary_route": "Store"}

    fake_executor = MagicMock()
    fake_executor.submit.side_effect = RuntimeError("thread pool rejected")

    with patch.object(jr, "_get_executor", return_value=fake_executor), patch.object(
        jev_metrics_mod, "record_shadow_event", return_value={}
    ) as mock_rec:
        ok = schedule_jev_shadow(
            state=state,
            legacy_decision=legacy,
            correlation_id="corr-sub",
            sync=False,
            force=True,
            sid="sid-sub",
        )

    assert ok is False
    assert mock_rec.called
    kwargs = mock_rec.call_args.kwargs
    assert kwargs["attempted"] is False
    assert kwargs["error_class"] == "submit_failed"
    assert kwargs["fallback_reason"] == "not_eligible"
    assert jr._pending_count == 0
    jr._reset_runtime_for_tests()


def test_log_write_failure_does_not_raise_on_sync_path():
    state = build_jev_router_state("logfail", {"messages": []}, "sid")
    legacy = {"primary_route": "Physical"}

    mock_result = SimpleNamespace(
        ok=True,
        answers={},
        usage={"input_tokens": 1},
        retry_count=0,
        model="jev-latest",
        error_class=None,
    )
    mock_decision = SimpleNamespace(
        primary_route="Physical",
        sub_route=None,
        confidence=0.9,
        risk_flags=[],
        valid=True,
        to_dialogue_routing_dict=lambda: {
            "primary_route": "Physical",
            "confidence": 0.9,
        },
    )
    with patch.object(
        jev_client_mod, "evaluate_system_one", return_value=mock_result
    ), patch.object(
        jev_decisions_mod, "parse_jev_answers", return_value=mock_decision
    ), patch.object(jev_decisions_mod, "INTENT_ROUTER_QUESTIONS", []), patch.object(
        jev_metrics_mod,
        "record_shadow_event",
        side_effect=OSError("disk full"),
    ):
        ok = run_jev_shadow_sync(
            state=state,
            legacy_decision=legacy,
            correlation_id="corr-log",
            force=True,
        )
    assert ok is True


def test_unknown_enum_answers_recorded_as_invalid_schema():
    """Transport OK + unknown choice → shadow fail-open with invalid_schema."""
    from src.services.jev_decisions import INTENT_ROUTER_QUESTIONS, parse_jev_answers

    state = build_jev_router_state("謎ルート", {"messages": []}, "sid")
    legacy = {"primary_route": "Physical", "sub_route": None}

    def _choice(value: str, confidence: float = 0.9) -> dict:
        return {"choice": value, "confidence": confidence}

    unknown_answers = {
        "primary_route": _choice("NotARealRoute", 0.9),
        "physical_sub_route": _choice("none", 0.5),
        "concierge_sub_route": _choice("none", 0.5),
        "session_sub_route": _choice("none", 0.5),
        "emergency_required": {"noul": 0.0},
        "security_risk": {"noul": 0.0},
        "store_inquiry": {"noul": 0.0},
        "counseling_needed": {"noul": 0.0},
    }
    # Confirm decisions layer tags unknown enum (Agent B contract; we only assert adapter).
    parsed = parse_jev_answers(unknown_answers)
    assert parsed.valid is False
    assert parsed.invalid_reason and "unknown_choice" in parsed.invalid_reason

    mock_result = SimpleNamespace(
        ok=True,
        answers=unknown_answers,
        usage={},
        retry_count=0,
        model="jev-latest",
        error_class=None,
    )

    with patch.object(
        jev_client_mod, "evaluate_system_one", return_value=mock_result
    ), patch.object(
        jev_metrics_mod, "record_shadow_event", return_value={}
    ) as mock_rec:
        ok = run_jev_shadow_sync(
            state=state,
            legacy_decision=legacy,
            correlation_id="corr-enum",
            force=True,
        )

    assert ok is True
    assert INTENT_ROUTER_QUESTIONS  # questions module importable for worker
    kwargs = mock_rec.call_args.kwargs
    assert kwargs["succeeded"] is False
    assert kwargs["fallback_reason"] == "invalid_schema"
    assert kwargs["error_class"] and "unknown_choice" in str(kwargs["error_class"])


def test_correlation_id_none_still_fail_open_and_uses_legacy_executed():
    state = build_jev_router_state("corr-none", {"messages": []}, "sid")
    legacy = {"primary_route": "Concierge", "sub_route": "faq"}

    mock_result = SimpleNamespace(
        ok=False,
        answers=None,
        usage=None,
        retry_count=0,
        model="jev-latest",
        error_class="timeout",
    )
    with patch.object(
        jev_client_mod, "evaluate_system_one", return_value=mock_result
    ), patch.object(
        jev_metrics_mod, "record_shadow_event", return_value={}
    ) as mock_rec, patch.object(
        jev_metrics_mod, "lookup_executed_decision", return_value=None
    ):
        ok = run_jev_shadow_sync(
            state=state,
            legacy_decision=legacy,
            correlation_id=None,
            force=True,
        )

    assert ok is True
    kwargs = mock_rec.call_args.kwargs
    assert kwargs["correlation_id"] is None
    assert kwargs["executed_decision"]["primary_route"] == "Concierge"
    assert kwargs["succeeded"] is False


def test_shutdown_executor_idempotent():
    jr._reset_runtime_for_tests()
    ex = jr._get_executor()
    assert ex is not None
    jr._shutdown_executor()
    assert jr._executor is None
    jr._shutdown_executor()  # second call safe
    assert jr._executor is None
    jr._reset_runtime_for_tests()


def test_jev_router_does_not_branch_on_primary_flag():
    source = inspect.getsource(jr)
    assert "is_jev_intent_router_primary" not in source
    assert "JEV_INTENT_ROUTER_PRIMARY" not in source


def test_missing_api_key_fail_open_through_shadow_worker(monkeypatch):
    """API key 欠落は client が fail-open → worker が metrics のみ（例外なし）。"""
    monkeypatch.delenv("JEV_API_KEY", raising=False)
    monkeypatch.delenv("TYPESAFE_API_KEY", raising=False)
    state = build_jev_router_state("nokey", {"messages": []}, "sid")
    legacy = {"primary_route": "Physical"}

    with patch.object(
        jev_metrics_mod, "record_shadow_event", return_value={}
    ) as mock_rec:
        ok = run_jev_shadow_sync(
            state=state,
            legacy_decision=legacy,
            correlation_id="corr-nokey",
            force=True,
        )

    assert ok is True
    kwargs = mock_rec.call_args.kwargs
    assert kwargs["succeeded"] is False
    assert kwargs["fallback_reason"] == "missing_api_key"
    assert kwargs["error_class"] == "missing_api_key"


def test_eligibility_exception_fail_closed_skips_jev_api(monkeypatch):
    """AE6-H2(b)/R10: eligibility 例外時は Jev API を呼ばず False（fail-closed）。

    Patch the actual callsite: decide_jev_intent_eligibility (not is_* wrapper).
    Use an otherwise-eligible Physical-like utterance so SessionOps ineligibility
    cannot falsely satisfy the assert.
    """
    jr._reset_runtime_for_tests()
    state = build_jev_router_state("頭痛がします", {"messages": []}, "sid")
    legacy = {"primary_route": "Physical"}

    with patch(
        "src.dialogue.routing.jev_router._is_jev_enabled", return_value=True
    ), patch(
        "src.dialogue.routing.jev_router._is_jev_intent_router_shadow_enabled",
        return_value=True,
    ), patch.object(
        jev_eligibility_mod,
        "decide_jev_intent_eligibility",
        side_effect=RuntimeError("eligibility boom"),
    ), patch.object(
        jev_client_mod, "evaluate_system_one", MagicMock()
    ) as mock_eval, patch.object(
        jev_metrics_mod, "record_shadow_event", return_value={}
    ) as mock_rec:
        ok = schedule_jev_shadow(
            state=state,
            legacy_decision=legacy,
            correlation_id="corr-elig-err",
            sync=True,
            force=False,
            sid="sid-elig",
        )

    assert ok is False
    assert not mock_eval.called
    assert mock_rec.called
    kwargs = mock_rec.call_args.kwargs
    assert kwargs.get("attempted") is False
    assert kwargs.get("fallback_reason") == "not_eligible"
    assert kwargs.get("error_class") == "signal_evaluation_error"
    assert kwargs.get("executed_decision", {}).get("primary_route") == "Physical"
    jr._reset_runtime_for_tests()
