"""Shared pre-route signals for SafetyGate, SessionOps, Legacy, and Jev eligibility.

Dependency rule (one-way):
  low-level detectors → this module → SafetyGate / SessionOps / Legacy / Jev

This module must NOT import:
  - src.services.jev_eligibility
  - src.agents.session_agent
  - Jev client / LLM / network APIs

SessionOps keyword classification lives in ``src.core.session_ops_classify``
(one-way: this module → session_ops_classify).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Optional

from src.dialogue.routing.medical_emergency_hints import medical_emergency_hint_hit


@dataclass(frozen=True)
class PreRouteSignals:
    emergency_detected: bool = False
    emergency_sub_route: str | None = None

    security_blocked: bool = False
    security_sub_route: str | None = None

    medical_examination: bool = False
    prescription_block: bool = False
    controlled_or_illegal_block: bool = False
    crisis_detected: bool = False

    session_operation: str | None = None

    # R7: ambiguous sleep-med / unknown controlled — policy path, not illegal default
    ambiguous_policy: bool = False
    policy_subtype: str | None = None

    # R7-B: evasion residue with SessionOps → fail-closed pure=False
    evasion_fail_closed: bool = False

    evaluation_complete: bool = True
    detector_errors: tuple[str, ...] = ()

    @property
    def deterministic_high_risk(self) -> bool:
        return bool(
            self.emergency_detected
            or self.security_blocked
            or self.crisis_detected
        )

    @property
    def policy_block(self) -> bool:
        return bool(
            self.medical_examination
            or self.prescription_block
            or self.controlled_or_illegal_block
            or self.ambiguous_policy
        )

    @property
    def session_operation_detected(self) -> bool:
        return self.session_operation is not None


def _truthy(value: Any) -> bool:
    return bool(value) is True


def _safe_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def merge_additive_bag(signals: dict[str, Any], bag: Mapping[str, Any] | None) -> None:
    """OR-merge bag flags into mutable signal dict (additive only)."""
    _merge_bag(signals, bag)


def _merge_bag(signals: dict[str, Any], bag: Mapping[str, Any] | None) -> None:
    if not isinstance(bag, Mapping):
        if _truthy(bag):
            signals["emergency_detected"] = True
        return

    if _truthy(bag.get("emergency_detected")) or _truthy(bag.get("emergency")):
        signals["emergency_detected"] = True
    if _truthy(bag.get("security_blocked")) or _truthy(bag.get("security")):
        signals["security_blocked"] = True
    if _truthy(bag.get("crisis")) or _truthy(bag.get("crisis_detected")):
        signals["crisis_detected"] = True
    if _truthy(bag.get("medical_examination")):
        signals["medical_examination"] = True
    if _truthy(bag.get("prescription")) or _truthy(bag.get("prescription_block")):
        signals["prescription_block"] = True
    if (
        _truthy(bag.get("controlled_or_illegal"))
        or _truthy(bag.get("controlled_or_illegal_block"))
        or _truthy(bag.get("illegal_drug"))
    ):
        signals["controlled_or_illegal_block"] = True
    if _truthy(bag.get("policy_block")) or _truthy(bag.get("policy_block_detected")):
        # Bag-level policy without finer grain → treat as medical examination block.
        signals["medical_examination"] = True
    if _truthy(bag.get("deterministic_high_risk")) or _truthy(bag.get("high_risk")):
        signals["emergency_detected"] = True
    if _truthy(bag.get("known_attack")) or _truthy(bag.get("aggressive")):
        signals["security_blocked"] = True

    sub = _safe_str(bag.get("emergency_sub_route"))
    if sub:
        signals["emergency_sub_route"] = sub
    sec_sub = _safe_str(bag.get("security_sub_route"))
    if sec_sub:
        signals["security_sub_route"] = sec_sub


def _detect_prompt_injection_cues(user_text: str) -> bool:
    text = (user_text or "").strip()
    if not text:
        return False
    low = text.lower()
    cues = (
        "システムプロンプト",
        "system prompt",
        "systemprompt",
        "prompt injection",
        "プロンプトインジェクション",
        "ignore all previous",
        "ignore previous instructions",
        "disregard previous",
        "前の指示を",
        "以前の指示を無視",
        "指示を全部無視",
        "指示を無視",
        "jailbreak",
        "開発者モード",
        "DANモード",
        "do anything now",
    )
    return any(c in text or c in low for c in cues)


def _detect_overdose_cues(user_text: str) -> bool:
    text = (user_text or "").strip()
    if not text:
        return False
    overdose_cues = (
        "過量",
        "大量に飲",
        "薬を大量",
        "オーバードーズ",
        "overdose",
        "全部飲",
        "まとめ飲み",
    )
    return any(c in text for c in overdose_cues)


def _detect_sleep_self_harm_cues(user_text: str) -> bool:
    """Sleep-med + self-harm / overdose intent — Emergency, not ambiguous policy."""
    text = (user_text or "").strip()
    if not text or "睡眠薬" not in text:
        return False
    harm = (
        "死にたい",
        "自殺",
        "全部飲",
        "大量に飲",
        "過量",
        "オーバードーズ",
        "まとめ飲み",
    )
    return any(h in text for h in harm)


def _detect_prescription_markers(user_text: str) -> bool:
    text = (user_text or "").strip()
    if not text:
        return False
    # Align with llm_triage prescription taxonomy (SessionOps×prescription FN guard).
    rx_markers = (
        "処方して",
        "処方してください",
        "処方箋",
        "処方薬をください",
        "処方薬を教えて",
        "マンジャロ",
        "チルゼパチド",
    )
    return any(m in text for m in rx_markers)


def collect_safety_policy_signals(
    user_text: str = "",
    *,
    deterministic_signals: Any = None,
    detector_text: str | None = None,
) -> PreRouteSignals:
    """Collect emergency / security / crisis / policy signals only.

    ``user_text`` is the display/canonical string (SessionOps / observability).
    ``detector_text`` is the detector comparison view (R7-B). When omitted,
    detectors run on ``user_text`` (legacy callers).
    """
    display = (user_text or "").strip()
    text = (detector_text if detector_text is not None else user_text) or ""
    text = text.strip()
    state: dict[str, Any] = {
        "emergency_detected": False,
        "emergency_sub_route": None,
        "security_blocked": False,
        "security_sub_route": None,
        "medical_examination": False,
        "prescription_block": False,
        "controlled_or_illegal_block": False,
        "crisis_detected": False,
        "session_operation": None,
        "ambiguous_policy": False,
        "policy_subtype": None,
    }
    errors: list[str] = []

    _merge_bag(state, deterministic_signals)

    if text:
        if _detect_prompt_injection_cues(text):
            state["security_blocked"] = True
        if _detect_overdose_cues(text):
            state["emergency_detected"] = True
        if _detect_sleep_self_harm_cues(text):
            state["emergency_detected"] = True
            # Prefer crisis when explicit SI markers present (detector view already may set it)
            if any(k in text for k in ("死にたい", "自殺")):
                state["crisis_detected"] = True
        if medical_emergency_hint_hit(text):
            state["emergency_detected"] = True
            if not state["emergency_sub_route"]:
                state["emergency_sub_route"] = "medical_emergency"
        if _detect_prescription_markers(text):
            # 「処方箋なし」は処方要求ではない
            if "処方箋なし" not in text and "処方箋が不要" not in text:
                state["prescription_block"] = True

        try:
            from src.security.known_attack_rules import match_known_attack

            if match_known_attack(text)[0]:
                state["security_blocked"] = True
                if not state["security_sub_route"]:
                    state["security_sub_route"] = "known_attack"
        except Exception:
            errors.append("known_attack_detector_error")

        try:
            from src.security.aggressive_input import is_aggressive_expression

            if is_aggressive_expression(text)[0]:
                state["security_blocked"] = True
                if not state["security_sub_route"]:
                    state["security_sub_route"] = "aggressive"
        except Exception:
            errors.append("aggressive_detector_error")

        try:
            from src.agents.emergency_classifier import is_emergency_candidate

            if is_emergency_candidate(text):
                state["emergency_detected"] = True
        except Exception:
            errors.append("emergency_detector_error")

        try:
            from src.core.crisis_detection import detect_crisis_keywords

            hit, _keywords = detect_crisis_keywords(text)
            if hit:
                state["crisis_detected"] = True
        except Exception:
            errors.append("crisis_detector_error")

        try:
            from src.services.medical_examination_request import (
                detect_medical_examination_request_contained,
            )

            if detect_medical_examination_request_contained(text):
                state["medical_examination"] = True
        except Exception:
            errors.append("medical_examination_detector_error")

        sleep_kind = None
        try:
            from src.dialogue.routing.sleep_med_policy import (
                classify_sleep_or_controlled_intent,
                sleep_intent_to_policy_flags,
            )

            # Crisis/emergency already wins — do not also open ambiguous sleep policy
            if not (
                state["emergency_detected"]
                or state["crisis_detected"]
            ):
                sleep_kind = classify_sleep_or_controlled_intent(text)
                flags = sleep_intent_to_policy_flags(sleep_kind)
                if flags.get("controlled_or_illegal_block"):
                    state["controlled_or_illegal_block"] = True
                if flags.get("prescription_block"):
                    state["prescription_block"] = True
                if flags.get("ambiguous_policy"):
                    state["ambiguous_policy"] = True
                if flags.get("policy_subtype"):
                    state["policy_subtype"] = flags["policy_subtype"]
        except Exception:
            errors.append("sleep_med_policy_detector_error")

        # Named-drug keyword hit must not override general-information classification
        if sleep_kind != "general_information" and not (
            state["emergency_detected"] or state["crisis_detected"]
        ):
            try:
                from src.services.llm_triage import detect_illegal_or_controlled_drug

                if detect_illegal_or_controlled_drug(text):
                    state["controlled_or_illegal_block"] = True
            except Exception:
                errors.append("controlled_drug_detector_error")
        elif sleep_kind == "general_information":
            # Keep info path open — do not set criminal/controlled block
            state["controlled_or_illegal_block"] = False
            state["ambiguous_policy"] = False

    del display  # reserved for future display-only probes
    evaluation_complete = len(errors) == 0
    return PreRouteSignals(
        emergency_detected=bool(state["emergency_detected"]),
        emergency_sub_route=state["emergency_sub_route"],
        security_blocked=bool(state["security_blocked"]),
        security_sub_route=state["security_sub_route"],
        medical_examination=bool(state["medical_examination"]),
        prescription_block=bool(state["prescription_block"]),
        controlled_or_illegal_block=bool(state["controlled_or_illegal_block"]),
        crisis_detected=bool(state["crisis_detected"]),
        session_operation=None,
        ambiguous_policy=bool(state["ambiguous_policy"]),
        policy_subtype=state.get("policy_subtype"),
        evasion_fail_closed=False,
        evaluation_complete=evaluation_complete,
        detector_errors=tuple(errors),
    )


def collect_pre_route_signals(
    user_text: str = "",
    *,
    deterministic_signals: Any = None,
    include_session_operation: bool = True,
    detector_text: str | None = None,
    evasion_fail_closed: bool = False,
) -> PreRouteSignals:
    """Collect full pre-route signals including optional SessionOps classification.

    SessionOps runs on ``user_text`` (canonical/display).
    Safety/policy detectors prefer ``detector_text`` when provided.
    """
    base = collect_safety_policy_signals(
        user_text,
        deterministic_signals=deterministic_signals,
        detector_text=detector_text,
    )
    errors = list(base.detector_errors)
    session_operation: str | None = None

    if include_session_operation:
        text = (user_text or "").strip()
        if text:
            try:
                from src.core.session_ops_classify import classify_session_intent

                intent = classify_session_intent(text)
                if intent is not None and str(intent) != "none":
                    session_operation = str(intent)
            except Exception:
                errors.append("session_ops_detector_error")

    # R7-A/B: SessionOps + unresolved evasion → never pure
    fail_closed = bool(evasion_fail_closed and session_operation is not None)

    return PreRouteSignals(
        emergency_detected=base.emergency_detected,
        emergency_sub_route=base.emergency_sub_route,
        security_blocked=base.security_blocked,
        security_sub_route=base.security_sub_route,
        medical_examination=base.medical_examination,
        prescription_block=base.prescription_block,
        controlled_or_illegal_block=base.controlled_or_illegal_block,
        crisis_detected=base.crisis_detected,
        session_operation=session_operation,
        ambiguous_policy=base.ambiguous_policy,
        policy_subtype=base.policy_subtype,
        evasion_fail_closed=fail_closed,
        evaluation_complete=len(errors) == 0,
        detector_errors=tuple(errors),
    )


def safety_or_policy_blocks_session_ops(signals: PreRouteSignals) -> bool:
    """True when SessionOps probe must yield to Safety / Policy paths."""
    if not signals.evaluation_complete:
        # Fail-closed for probe: do not claim SessionOps when detectors failed.
        return True
    return bool(signals.deterministic_high_risk or signals.policy_block)


__all__ = [
    "PreRouteSignals",
    "collect_pre_route_signals",
    "collect_safety_policy_signals",
    "merge_additive_bag",
    "safety_or_policy_blocks_session_ops",
]
