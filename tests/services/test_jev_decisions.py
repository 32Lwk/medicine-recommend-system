"""Unit tests for Jev answer → shadow decision mapping."""
from __future__ import annotations

import math

import pytest

from src.services.jev_decisions import (
    ADAPTER_MODE,
    DEFAULT_NOUL_THRESHOLD,
    INTENT_ROUTER_QUESTIONS,
    JevConciergeSubRoute,
    JevPhysicalSubRoute,
    JevPrimaryRoute,
    JevSessionSubRoute,
    parse_jev_answers,
    to_route_dict,
)


def _choice(value: str, confidence: float = 0.9) -> dict:
    return {"choice": value, "confidence": confidence}


def _noul(value: float) -> dict:
    return {"noul": value}


def _base_answers(
    *,
    primary: str = "Physical",
    primary_conf: float = 0.91,
    physical_sub: str = "none",
    physical_conf: float = 0.5,
    concierge_sub: str = "none",
    concierge_conf: float = 0.5,
    session_sub: str = "none",
    session_conf: float = 0.5,
    emergency: float = 0.0,
    security: float = 0.0,
    store: float = 0.0,
    counseling: float = 0.0,
) -> dict:
    return {
        "primary_route": _choice(primary, primary_conf),
        "physical_sub_route": _choice(physical_sub, physical_conf),
        "concierge_sub_route": _choice(concierge_sub, concierge_conf),
        "session_sub_route": _choice(session_sub, session_conf),
        "emergency_required": _noul(emergency),
        "security_risk": _noul(security),
        "store_inquiry": _noul(store),
        "counseling_needed": _noul(counseling),
    }


@pytest.mark.parametrize(
    "primary,expected_sub",
    [
        ("Physical", None),
        ("SessionOps", None),
        ("Concierge", None),
        ("Emergency", "emergency_dispatch"),
        ("Security", "known_attack"),
        ("Store", "store_locator"),
        ("Counseling", "emotional_support"),
        ("Unknown", None),
    ],
)
def test_all_primaries(primary: str, expected_sub: str | None) -> None:
    decision = parse_jev_answers(_base_answers(primary=primary))
    assert decision.valid is True
    assert decision.primary_route == primary
    assert decision.sub_route == expected_sub
    assert decision.adapter_mode == ADAPTER_MODE
    assert decision.primary_confidence == 0.91


def test_physical_sub_none_maps_to_null() -> None:
    decision = parse_jev_answers(
        _base_answers(primary="Physical", physical_sub="none", physical_conf=0.77)
    )
    assert decision.valid is True
    assert decision.sub_route is None
    assert decision.selected_sub_confidence == 0.77


@pytest.mark.parametrize("sub", [m.value for m in JevPhysicalSubRoute if m != JevPhysicalSubRoute.NONE])
def test_physical_subs(sub: str) -> None:
    decision = parse_jev_answers(
        _base_answers(primary="Physical", physical_sub=sub, physical_conf=0.88)
    )
    assert decision.valid is True
    assert decision.primary_route == "Physical"
    assert decision.sub_route == sub
    assert decision.selected_sub_confidence == 0.88


@pytest.mark.parametrize("sub", [m.value for m in JevConciergeSubRoute if m != JevConciergeSubRoute.NONE])
def test_concierge_subs(sub: str) -> None:
    decision = parse_jev_answers(
        _base_answers(primary="Concierge", concierge_sub=sub, concierge_conf=0.81)
    )
    assert decision.valid is True
    assert decision.sub_route == sub
    assert decision.selected_sub_confidence == 0.81


@pytest.mark.parametrize(
    "sub,expected",
    [
        ("delete", "delete_confirm"),
        ("summarize", "summarize"),
        ("status", "status"),
        ("none", None),
    ],
)
def test_session_subs(sub: str, expected: str | None) -> None:
    decision = parse_jev_answers(
        _base_answers(primary="SessionOps", session_sub=sub, session_conf=0.79)
    )
    assert decision.valid is True
    assert decision.sub_route == expected
    assert decision.selected_sub_confidence == 0.79


def test_unknown_primary_enum_invalid() -> None:
    answers = _base_answers(primary="Physical")
    answers["primary_route"] = _choice("NotARoute", 0.9)
    decision = parse_jev_answers(answers)
    assert decision.valid is False
    assert decision.invalid_reason is not None
    assert "unknown_choice:primary_route" in decision.invalid_reason


def test_unknown_sub_enum_invalid() -> None:
    answers = _base_answers(primary="Physical", physical_sub="none")
    answers["physical_sub_route"] = _choice("not_a_sub", 0.9)
    decision = parse_jev_answers(answers)
    assert decision.valid is False
    assert "unknown_choice:physical_sub_route" in (decision.invalid_reason or "")


@pytest.mark.parametrize(
    "mutate,reason_substr",
    [
        (lambda a: a.pop("primary_route"), "missing_choice:primary_route"),
        (lambda a: a.__setitem__("primary_route", {"confidence": 0.9}), "missing_choice:primary_route"),
        (lambda a: a.__setitem__("primary_route", _choice("Physical", "high")), "non_numeric"),
        (lambda a: a.__setitem__("primary_route", _choice("Physical", -0.1)), "out_of_range"),
        (lambda a: a.__setitem__("primary_route", _choice("Physical", 1.01)), "out_of_range"),
        (lambda a: a.__setitem__("primary_route", _choice("Physical", float("nan"))), "non_numeric"),
        (lambda a: a.__setitem__("emergency_required", {"noul": "bad"}), "non_numeric"),
        (lambda a: a.__setitem__("security_risk", {"noul": 1.5}), "out_of_range"),
    ],
)
def test_malformed_answers_invalid(mutate, reason_substr: str) -> None:
    answers = _base_answers()
    mutate(answers)
    decision = parse_jev_answers(answers)
    assert decision.valid is False
    assert decision.invalid_reason is not None
    assert reason_substr in decision.invalid_reason


def test_confidence_separation_primary_vs_sub() -> None:
    decision = parse_jev_answers(
        _base_answers(
            primary="Physical",
            primary_conf=0.95,
            physical_sub="medicine_qa",
            physical_conf=0.61,
        )
    )
    assert decision.valid is True
    assert decision.primary_confidence == 0.95
    assert decision.selected_sub_confidence == 0.61
    assert decision.primary_confidence != decision.selected_sub_confidence


def test_noul_override_does_not_reuse_primary_confidence() -> None:
    decision = parse_jev_answers(
        _base_answers(primary="Physical", primary_conf=0.99, security=0.81)
    )
    assert decision.primary_route == "Security"
    assert decision.sub_route == "known_attack"
    assert decision.primary_confidence == 0.99
    assert decision.selected_sub_confidence == 0.81


@pytest.mark.parametrize(
    "key,value,primary,sub",
    [
        ("security", DEFAULT_NOUL_THRESHOLD, "Security", "known_attack"),
        ("emergency", DEFAULT_NOUL_THRESHOLD, "Emergency", "emergency_dispatch"),
    ],
)
def test_noul_high_risk_threshold_overrides_physical(
    key: str, value: float, primary: str, sub: str
) -> None:
    kwargs = {key: value}
    decision = parse_jev_answers(
        _base_answers(primary="Physical", physical_sub="medicine_qa", **kwargs)
    )
    assert decision.valid is True
    assert decision.primary_route == primary
    assert decision.sub_route == sub


@pytest.mark.parametrize(
    "key,value,primary,sub",
    [
        ("store", DEFAULT_NOUL_THRESHOLD, "Store", "store_locator"),
        ("counseling", DEFAULT_NOUL_THRESHOLD, "Counseling", "emotional_support"),
    ],
)
def test_noul_store_counseling_override_when_primary_not_physical(
    key: str, value: float, primary: str, sub: str
) -> None:
    # Matches eval script: Physical/Concierge/SessionOps branches run before store/counseling Noul.
    kwargs = {key: value}
    decision = parse_jev_answers(_base_answers(primary="Unknown", **kwargs))
    assert decision.valid is True
    assert decision.primary_route == primary
    assert decision.sub_route == sub


def test_store_noul_does_not_override_physical_primary() -> None:
    decision = parse_jev_answers(
        _base_answers(primary="Physical", physical_sub="medicine_qa", store=0.99)
    )
    assert decision.primary_route == "Physical"
    assert decision.sub_route == "medicine_qa"


@pytest.mark.parametrize(
    "key,value",
    [
        ("security", DEFAULT_NOUL_THRESHOLD - 1e-9),
        ("emergency", DEFAULT_NOUL_THRESHOLD - 1e-9),
        ("store", DEFAULT_NOUL_THRESHOLD - 1e-9),
        ("counseling", DEFAULT_NOUL_THRESHOLD - 1e-9),
    ],
)
def test_noul_just_below_threshold_keeps_primary(key: str, value: float) -> None:
    decision = parse_jev_answers(
        _base_answers(primary="Physical", physical_sub="fever_flow", physical_conf=0.7, **{key: value})
    )
    assert decision.primary_route == "Physical"
    assert decision.sub_route == "fever_flow"


def test_noul_security_beats_emergency_when_both_high() -> None:
    decision = parse_jev_answers(
        _base_answers(primary="Unknown", security=0.9, emergency=0.95)
    )
    assert decision.primary_route == "Security"
    assert decision.sub_route == "known_attack"


def test_deterministic_security_cannot_be_weakened_by_low_noul() -> None:
    decision = parse_jev_answers(
        _base_answers(primary="Physical", physical_sub="medicine_qa", security=0.01, emergency=0.0),
        deterministic_signals={"security_blocked": True},
    )
    assert decision.valid is True
    assert decision.primary_route == "Security"
    assert decision.sub_route == "known_attack"
    assert decision.source == "deterministic_security_override"
    assert decision.primary_confidence == 1.0
    assert "security" in decision.risk_flags


def test_deterministic_emergency_cannot_be_weakened() -> None:
    decision = parse_jev_answers(
        _base_answers(primary="Concierge", concierge_sub="greeting", emergency=0.0),
        deterministic_signals={"emergency_detected": True},
    )
    assert decision.primary_route == "Emergency"
    assert decision.sub_route == "emergency_dispatch"
    assert decision.source == "deterministic_emergency_override"


def test_deterministic_medical_examination_override() -> None:
    decision = parse_jev_answers(
        _base_answers(primary="Store", store=0.9),
        deterministic_signals={"medical_examination": True},
    )
    assert decision.primary_route == "Emergency"
    assert decision.sub_route == "medical_examination"
    assert decision.source == "deterministic_medical_examination_override"
    assert "medical_examination" in decision.risk_flags


def test_deterministic_security_wins_over_emergency_signal() -> None:
    decision = parse_jev_answers(
        _base_answers(primary="Unknown"),
        deterministic_signals={
            "security_blocked": True,
            "emergency_detected": True,
            "medical_examination": True,
        },
    )
    assert decision.primary_route == "Security"
    assert decision.source == "deterministic_security_override"


def test_joint_primary_and_sub_mapping() -> None:
    decision = parse_jev_answers(
        _base_answers(
            primary="Physical",
            primary_conf=0.93,
            physical_sub="medicine_side_effect_qa",
            physical_conf=0.84,
        )
    )
    assert (decision.primary_route, decision.sub_route) == (
        "Physical",
        "medicine_side_effect_qa",
    )
    logged = to_route_dict(decision)
    assert logged["primary_route"] == "Physical"
    assert logged["sub_route"] == "medicine_side_effect_qa"
    assert logged["confidence"] == 0.93
    assert logged["selected_sub_confidence"] == 0.84
    assert "answers" not in logged
    assert set(JevPrimaryRoute)  # enums export smoke
    assert math.isclose(DEFAULT_NOUL_THRESHOLD, 0.75)


def test_intent_router_questions_export_matches_expected_keys() -> None:
    assert set(INTENT_ROUTER_QUESTIONS) >= {
        "primary_route",
        "physical_sub_route",
        "concierge_sub_route",
        "session_sub_route",
        "emergency_required",
        "security_risk",
        "store_inquiry",
        "counseling_needed",
    }
    assert INTENT_ROUTER_QUESTIONS["primary_route"]["type"] == "choice"
    assert INTENT_ROUTER_QUESTIONS["emergency_required"]["type"] == "noul"
    assert set(INTENT_ROUTER_QUESTIONS["primary_route"]["criteria"]) == {
        m.value for m in JevPrimaryRoute
    }
    assert set(INTENT_ROUTER_QUESTIONS["session_sub_route"]["criteria"]) == {
        m.value for m in JevSessionSubRoute
    }


def test_missing_noul_keys_default_to_zero() -> None:
    answers = {
        "primary_route": _choice("Physical", 0.9),
        "physical_sub_route": _choice("rule_based_recommend", 0.8),
        "concierge_sub_route": _choice("none", 0.5),
        "session_sub_route": _choice("none", 0.5),
    }
    decision = parse_jev_answers(answers)
    assert decision.valid is True
    assert decision.noul == {
        "emergency_required": 0.0,
        "security_risk": 0.0,
        "store_inquiry": 0.0,
        "counseling_needed": 0.0,
    }
