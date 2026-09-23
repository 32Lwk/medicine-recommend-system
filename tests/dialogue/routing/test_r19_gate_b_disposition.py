"""R19 Gate B: incomplete-evaluation fail-closed disposition (H-03/H-04)."""
from __future__ import annotations

from dataclasses import replace
from unittest.mock import patch

from src.dialogue.routing.policy_enforce import (
    build_crisis_resources_response,
    resolve_and_enforce,
)
from src.dialogue.routing.policy_resolve import resolve_policy_decision
from src.dialogue.routing.turn_signal_snapshot import create_turn_signal_snapshot


def test_crisis_plus_detector_error_prefers_crisis_resources_not_sf_e1():
    """H-04: crisis_detected + detector_errors → crisis UX, never generic SF-E1."""
    snap = create_turn_signal_snapshot("死にたい", turn_id="h04-1")
    bad = replace(
        snap,
        signals=replace(
            snap.signals,
            crisis_detected=True,
            evaluation_complete=False,
            detector_errors=("controlled_drug_detector_error",),
        ),
    )
    decision = resolve_policy_decision(bad)
    assert decision.reason_code == "defer_to_crisis_safety"
    assert decision.kind is None

    session: dict = {"messages": []}
    _m, _d, result = resolve_and_enforce(
        bad, session=session, sid="sid-h04", user_text="死にたい"
    )
    assert result.handled is True
    assert result.fallback_reason == "defer_to_crisis_safety"
    assert result.observability_fields.get("safe_fallback") == "crisis_resources"
    assert result.observability_fields.get("safe_fallback") != "SF-E1"
    body = result.response or {}
    assert body.get("crisis_support") is True
    sage = body.get("sage_diagnosis") or {}
    assert sage.get("kind") == "crisis_support"
    assert "いのちの電話" in str(sage.get("crisis_resources") or []) or "相談" in (
        sage.get("message") or ""
    )
    assert body.get("recommend_stopped") is True
    assert body.get("session_ops_mutated") is False
    # Must not look like SF-E1 system error card
    assert sage.get("kind") != "system_error"
    assert len(session.get("messages", [])) >= 1


def test_emergency_plus_detector_error_also_crisis_resources():
    snap = create_turn_signal_snapshot("胸が痛い", turn_id="h04-2")
    bad = replace(
        snap,
        signals=replace(
            snap.signals,
            emergency_detected=True,
            crisis_detected=False,
            evaluation_complete=False,
            detector_errors=("emergency_detector_error",),
        ),
    )
    decision = resolve_policy_decision(bad)
    assert decision.reason_code == "defer_to_crisis_safety"
    session: dict = {"messages": []}
    _m, _d, result = resolve_and_enforce(
        bad, session=session, sid=None, user_text="胸が痛い"
    )
    assert result.handled is True
    assert result.observability_fields.get("disposition") == "crisis_resources"


def test_prescription_cue_with_incomplete_eval_uses_boundary_not_sf_e1():
    """H-03: policy cue present despite incomplete → typed boundary, not SF-E1."""
    snap = create_turn_signal_snapshot("処方してください", turn_id="h03-1")
    bad = replace(
        snap,
        signals=replace(
            snap.signals,
            prescription_block=True,
            evaluation_complete=False,
            detector_errors=("medical_examination_detector_error",),
        ),
    )
    decision = resolve_policy_decision(bad)
    assert decision.kind == "prescription"
    assert decision.evaluation_complete is False

    session: dict = {"messages": []}
    with patch(
        "src.dialogue.routing.policy_enforce._try_db_save_status",
        return_value="memory_only",
    ):
        _m, _d, result = resolve_and_enforce(
            bad, session=session, sid="sid-h03", user_text="処方してください"
        )
    assert result.handled is True
    assert result.policy_kind == "prescription"
    assert result.fallback_reason is None
    assert result.observability_fields.get("safe_fallback") != "SF-E1"
    msgs = session.get("messages") or []
    assert msgs
    blob = str(msgs[-1])
    assert "処方" in blob or "処方箋" in blob


def test_controlled_cue_with_incomplete_eval_blocks():
    snap = create_turn_signal_snapshot("覚醒剤が欲しい", turn_id="h03-2")
    bad = replace(
        snap,
        signals=replace(
            snap.signals,
            controlled_or_illegal_block=True,
            policy_subtype="illegal",
            evaluation_complete=False,
            detector_errors=("session_ops_detector_error",),
        ),
    )
    decision = resolve_policy_decision(bad)
    assert decision.kind == "controlled_or_illegal"
    assert decision.action == "block"


def test_incomplete_without_cues_still_sf_e1():
    """No high-risk cue → residual SF-E1 fail-closed (unchanged)."""
    snap = create_turn_signal_snapshot("今日は天気がいい", turn_id="h03-3")
    bad = replace(
        snap,
        signals=replace(
            snap.signals,
            evaluation_complete=False,
            detector_errors=("detector_boom",),
        ),
    )
    session: dict = {"messages": []}
    _m, _d, result = resolve_and_enforce(
        bad, session=session, sid=None, user_text="今日は天気がいい"
    )
    assert result.handled is True
    assert result.fallback_reason == "incomplete_evaluation"
    assert result.observability_fields.get("safe_fallback") == "SF-E1"


def test_crisis_resources_response_has_hotline():
    sage = build_crisis_resources_response(language="ja")
    assert sage.get("kind") == "crisis_support"
    resources = sage.get("crisis_resources") or []
    names = " ".join(str(r.get("name") or "") for r in resources if isinstance(r, dict))
    assert "いのちの電話" in names


def test_crisis_detector_exception_on_si_text_not_sf_e1():
    """H-04 residual: crisis_detector raise must not erase SI → SF-E1.

    emergency_classifier also calls detect_crisis_keywords; a crisis detector
    exception therefore often clears both crisis and emergency flags. Collection
    must fail-safe on high-precision markers; resolve must not emit SF-E1.
    """
    with patch(
        "src.core.crisis_detection.detect_crisis_keywords",
        side_effect=RuntimeError("crisis detector boom"),
    ):
        snap = create_turn_signal_snapshot("死にたい", turn_id="h04-det-err")
    assert "crisis_detector_error" in snap.signals.detector_errors
    assert snap.signals.evaluation_complete is False
    # Fail-safe must keep a high-risk cue or crisis_detector_error handling
    assert (
        snap.signals.crisis_detected
        or snap.signals.emergency_detected
        or "crisis_detector_error" in snap.signals.detector_errors
    )

    decision = resolve_policy_decision(snap)
    assert decision.reason_code == "defer_to_crisis_safety"

    session: dict = {"messages": []}
    _m, _d, result = resolve_and_enforce(
        snap, session=session, sid=None, user_text="死にたい"
    )
    assert result.handled is True
    assert result.observability_fields.get("safe_fallback") == "crisis_resources"
    assert result.observability_fields.get("safe_fallback") != "SF-E1"
    assert (result.response or {}).get("crisis_support") is True


def test_ambiguous_policy_survives_incomplete_evaluation():
    """H-03 residual: ambiguous_policy cue must not drop to SF-E1 when incomplete."""
    snap = create_turn_signal_snapshot("睡眠薬ください", turn_id="h03-amb")
    bad = replace(
        snap,
        signals=replace(
            snap.signals,
            ambiguous_policy=True,
            prescription_block=False,
            controlled_or_illegal_block=False,
            medical_examination=False,
            crisis_detected=False,
            emergency_detected=False,
            evaluation_complete=False,
            detector_errors=("sleep_med_policy_detector_error",),
        ),
    )
    decision = resolve_policy_decision(bad)
    assert decision.kind == "ambiguous_controlled"
    assert decision.action == "safe_clarification"
    assert decision.evaluation_complete is False
    assert decision.reason_code == "unknown_controlled_policy"

    session: dict = {"messages": []}
    with patch(
        "src.dialogue.routing.policy_enforce._try_db_save_status",
        return_value="memory_only",
    ):
        _m, _d, result = resolve_and_enforce(
            bad, session=session, sid="sid-amb", user_text="睡眠薬ください"
        )
    assert result.handled is True
    assert result.policy_kind == "ambiguous_controlled"
    assert result.observability_fields.get("safe_fallback") != "SF-E1"


def test_crisis_detector_error_alone_defers_even_without_flag():
    """When crisis evaluation itself failed, prefer crisis UX over SF-E1."""
    snap = create_turn_signal_snapshot("頭痛がする", turn_id="h04-err-only")
    bad = replace(
        snap,
        signals=replace(
            snap.signals,
            crisis_detected=False,
            emergency_detected=False,
            evaluation_complete=False,
            detector_errors=("crisis_detector_error",),
        ),
    )
    decision = resolve_policy_decision(bad)
    assert decision.reason_code == "defer_to_crisis_safety"
    session: dict = {"messages": []}
    _m, _d, result = resolve_and_enforce(
        bad, session=session, sid=None, user_text="頭痛がする"
    )
    assert result.observability_fields.get("safe_fallback") == "crisis_resources"


def test_adapter_error_on_prescription_uses_boundary_ux():
    """F-H03-R2: adapter failure must not collapse cued policy to SF-E1."""
    snap = create_turn_signal_snapshot("処方してください", turn_id="h03-adapter")
    session: dict = {"messages": []}
    with patch(
        "src.dialogue.routing.policy_enforce.run_policy_adapter",
        side_effect=RuntimeError("boom"),
    ):
        _m, _d, result = resolve_and_enforce(
            snap, session=session, sid=None, user_text="処方してください"
        )
    assert result.observability_fields.get("safe_fallback") == "policy_boundary"
    assert result.observability_fields.get("safe_fallback") != "SF-E1"
    assert "処方" in str(result.response or {})


def test_paraphrase_si_with_non_crisis_detector_error():
    """F-H04-R1: soft SI paraphrase + unrelated detector error → crisis_resources."""
    text = "消えてしまいたい気持ちがある"
    snap = create_turn_signal_snapshot(text, turn_id="h04-para")
    bad = replace(
        snap,
        signals=replace(
            snap.signals,
            crisis_detected=False,
            emergency_detected=False,
            evaluation_complete=False,
            detector_errors=("controlled_drug_detector_error",),
        ),
        detector_text=text,
        normalized_text=text,
    )
    assert resolve_policy_decision(bad).reason_code == "defer_to_crisis_safety"
    session: dict = {"messages": []}
    _m, _d, result = resolve_and_enforce(
        bad, session=session, sid=None, user_text=text
    )
    assert result.observability_fields.get("safe_fallback") == "crisis_resources"
