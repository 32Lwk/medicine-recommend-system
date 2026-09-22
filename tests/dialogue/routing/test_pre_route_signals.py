"""Unit tests for shared PreRouteSignals collector and pure eligibility."""
from __future__ import annotations

from unittest.mock import patch

from src.dialogue.routing.pre_route_signals import (
    PreRouteSignals,
    collect_pre_route_signals,
    collect_safety_policy_signals,
    safety_or_policy_blocks_session_ops,
)
from src.services.jev_eligibility import (
    JevEligibilityReason,
    decide_jev_intent_eligibility,
    is_jev_intent_router_eligible,
)


def test_decide_pure_eligible() -> None:
    signals = PreRouteSignals(evaluation_complete=True)
    d = decide_jev_intent_eligibility(signals)
    assert d.eligible is True
    assert d.reason == JevEligibilityReason.INTENT_CLASSIFICATION_CANDIDATE.value


def test_decide_fail_closed_on_detector_error() -> None:
    signals = PreRouteSignals(
        evaluation_complete=False,
        detector_errors=("emergency_detector_error",),
        emergency_detected=False,
    )
    d = decide_jev_intent_eligibility(signals)
    assert d.eligible is False
    assert d.reason == JevEligibilityReason.SIGNAL_EVALUATION_ERROR.value


def test_decide_emergency_over_sessionops() -> None:
    signals = PreRouteSignals(
        emergency_detected=True,
        session_operation="delete",
        evaluation_complete=True,
    )
    d = decide_jev_intent_eligibility(signals)
    assert d.eligible is False
    assert d.reason == JevEligibilityReason.DETERMINISTIC_HIGH_RISK.value
    assert d.sessionops_fast_path_suppressed is True


def test_decide_policy_over_sessionops() -> None:
    signals = PreRouteSignals(
        medical_examination=True,
        session_operation="delete",
        evaluation_complete=True,
    )
    d = decide_jev_intent_eligibility(signals)
    assert d.eligible is False
    assert d.reason == JevEligibilityReason.POLICY_BLOCK.value
    assert d.sessionops_fast_path_suppressed is True


def test_decide_sessionops_alone() -> None:
    signals = PreRouteSignals(
        session_operation="delete",
        evaluation_complete=True,
    )
    d = decide_jev_intent_eligibility(signals)
    assert d.eligible is False
    assert d.reason == JevEligibilityReason.SESSIONOPS_FAST_PATH.value
    assert d.sessionops_fast_path_suppressed is False


def test_collect_safety_policy_does_not_import_jev() -> None:
    import ast
    from pathlib import Path

    path = Path("src/dialogue/routing/pre_route_signals.py")
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported.add(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
    assert not any("jev_eligibility" in m or "jev_router" in m for m in imported)


def test_session_agent_probe_does_not_import_jev() -> None:
    import ast
    import inspect

    from src.agents import session_agent as sa

    src = inspect.getsource(sa._session_admin_probe_blocked_by_safety)
    tree = ast.parse(src)
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                imported.add(alias.name)
    assert not any("jev_eligibility" in m for m in imported)


def test_detector_error_marks_incomplete() -> None:
    with patch(
        "src.agents.emergency_classifier.is_emergency_candidate",
        side_effect=RuntimeError("boom"),
    ):
        signals = collect_safety_policy_signals("頭痛がします")
    assert signals.evaluation_complete is False
    assert "emergency_detector_error" in signals.detector_errors
    assert safety_or_policy_blocks_session_ops(signals) is True
    d = decide_jev_intent_eligibility(
        PreRouteSignals(
            evaluation_complete=False,
            detector_errors=signals.detector_errors,
            session_operation="delete",
        )
    )
    assert d.eligible is False
    assert d.reason == JevEligibilityReason.SIGNAL_EVALUATION_ERROR.value


def test_override_false_cannot_clear_detector_high_risk() -> None:
    """BE-H1 Closed: boolean overrides only add risk, never erase detector hits."""
    d = is_jev_intent_router_eligible(
        "薬を大量に飲んだ",
        deterministic_high_risk=False,
        policy_block_detected=False,
        session_operation_detected=False,
    )
    assert d.eligible is False
    assert d.reason == JevEligibilityReason.DETERMINISTIC_HIGH_RISK.value


def test_medical_emergency_hints_single_source() -> None:
    """BE-H2 Closed: gate and pre_route share medical_emergency_hints."""
    from src.dialogue.routing import gate as gate_mod
    from src.dialogue.routing.medical_emergency_hints import MEDICAL_EMERGENCY_HINTS
    from src.dialogue.routing.medical_emergency_hints import medical_emergency_hint_hit

    assert gate_mod._MEDICAL_EMERGENCY_HINTS is MEDICAL_EMERGENCY_HINTS
    assert medical_emergency_hint_hit("胸が痛くて息が苦しい") is True
    signals = collect_pre_route_signals("胸が痛くて息が苦しい")
    assert signals.emergency_detected is True


def test_wrapper_still_matches_collect_decide() -> None:
    text = "頭痛がします。市販薬でおすすめはありますか？"
    via_wrapper = is_jev_intent_router_eligible(text)
    via_pure = decide_jev_intent_eligibility(collect_pre_route_signals(text))
    assert via_wrapper == via_pure


def test_pre_route_does_not_import_session_agent() -> None:
    import ast
    import inspect
    from pathlib import Path

    path = Path("src/dialogue/routing/pre_route_signals.py")
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                imported.add(alias.name)
    assert not any("session_agent" in m for m in imported)
    collect_src = inspect.getsource(
        __import__(
            "src.dialogue.routing.pre_route_signals", fromlist=["collect_pre_route_signals"]
        ).collect_pre_route_signals
    )
    assert "session_ops_classify" in collect_src
    assert "session_agent" not in collect_src


def test_session_ops_classify_does_not_import_pre_route_or_session_agent() -> None:
    import ast
    from pathlib import Path

    path = Path("src/core/session_ops_classify.py")
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                imported.add(alias.name)
    assert not any("pre_route_signals" in m for m in imported)
    assert not any("session_agent" in m for m in imported)
    assert not any("jev_eligibility" in m for m in imported)


def test_no_bidirectional_session_agent_pre_route_on_session_ops_path() -> None:
    """Full collect uses session_ops_classify; probe uses safety-only collect."""
    import ast
    import inspect

    from src.agents import session_agent as sa
    from src.dialogue.routing import pre_route_signals as prs

    probe_src = inspect.getsource(sa._session_admin_probe_blocked_by_safety)
    assert "pre_route_signals" in probe_src
    assert "classify_session_intent" not in probe_src

    collect_src = inspect.getsource(prs.collect_pre_route_signals)
    assert "session_ops_classify" in collect_src
    assert "session_agent" not in collect_src

    # Top-level: session_agent may import pre_route lazily; pre_route must never
    # import session_agent (AST).
    prs_tree = ast.parse(
        __import__("pathlib").Path("src/dialogue/routing/pre_route_signals.py").read_text(
            encoding="utf-8"
        )
    )
    for node in ast.walk(prs_tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            assert "session_agent" not in node.module
