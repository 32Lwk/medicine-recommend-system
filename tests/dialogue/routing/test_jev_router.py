"""tests for src.dialogue.routing.jev_router (Phase 1B)."""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

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
    import sys

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
    client_mod = MagicMock()
    client_mod.evaluate_system_one = MagicMock(return_value=mock_result)
    decisions_mod = MagicMock()
    decisions_mod.parse_jev_answers = MagicMock(return_value=mock_decision)
    decisions_mod.INTENT_ROUTER_QUESTIONS = []

    with patch(
        "src.dialogue.routing.jev_router._is_jev_enabled", return_value=True
    ), patch(
        "src.dialogue.routing.jev_router._is_jev_intent_router_shadow_enabled",
        return_value=True,
    ), patch.dict(
        sys.modules,
        {
            "src.services.jev_client": client_mod,
            "src.services.jev_decisions": decisions_mod,
        },
    ), patch("src.services.jev_metrics.record_shadow_event", return_value={}):
        ok = schedule_jev_shadow(
            state=state,
            legacy_decision=legacy,
            correlation_id="corr-1",
            sync=True,
            force=True,
            sid="sid-x",
        )
        assert ok is True
        assert client_mod.evaluate_system_one.called

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

    import sys

    client_mod = MagicMock()
    client_mod.evaluate_system_one = MagicMock(return_value=mock_result)
    decisions_mod = MagicMock()
    decisions_mod.parse_jev_answers = MagicMock(return_value=mock_decision)
    decisions_mod.INTENT_ROUTER_QUESTIONS = [{"id": "primary"}]

    with patch.dict(
        sys.modules,
        {
            "src.services.jev_client": client_mod,
            "src.services.jev_decisions": decisions_mod,
        },
    ), patch("src.services.jev_metrics.record_shadow_event", return_value={}) as mock_rec:
        ok = run_jev_shadow_sync(
            state=state,
            legacy_decision=legacy,
            correlation_id="c-sync",
            sid="s1",
            force=True,
        )
        assert ok is True
        assert client_mod.evaluate_system_one.called
        assert decisions_mod.parse_jev_answers.called
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
    from src.dialogue.routing import jev_router as jr

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
    import sys

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

    client_mod = MagicMock()
    client_mod.evaluate_system_one = MagicMock(side_effect=_fake_eval)
    decisions_mod = MagicMock()
    decisions_mod.parse_jev_answers = MagicMock(
        return_value={"primary_route": "Unknown", "valid": True}
    )
    decisions_mod.INTENT_ROUTER_QUESTIONS = []

    with patch.dict(
        sys.modules,
        {
            "src.services.jev_client": client_mod,
            "src.services.jev_decisions": decisions_mod,
        },
    ), patch("src.services.jev_metrics.record_shadow_event", return_value={}):
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
