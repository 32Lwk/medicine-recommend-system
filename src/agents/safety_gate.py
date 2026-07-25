"""
SafetyGate — LLM 前の決定的安全チェック集約
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional, Tuple

from src.utils.chat_http_context import ChatClientInfo

ResponseTuple = Tuple[dict, int]


@dataclass
class SafetyGateResult:
    blocked: bool = False
    response: Optional[ResponseTuple] = None
    needs_llm_review: bool = False
    review_reason: str = ""


def _borderline_crisis_hint(text: str) -> bool:
    t = (text or "").strip()
    if not t:
        return False
    hints = ("死にたいわけでは", "消えたいわけでは", "本当に死にたい")
    if any(h in t for h in hints):
        return True
    if "死にたい" in t or "自殺" in t:
        return False
    return False


def run_safety_gate_pre(
    session: Any,
    client_info: ChatClientInfo,
    sid: Optional[str],
    user_message: str,
    sanitized_message: str,
    *,
    recommendation_client: Any = None,
) -> Tuple[SafetyGateResult, str]:
    """トリアージ前: 入力検証・診断名・不適切入力。更新済み sanitized を返す。"""
    from src.handlers.chat.chat_input_validator import validate_and_block_input

    sanitized, error_response = validate_and_block_input(session, client_info, user_message, sid)
    if error_response is not None:
        return SafetyGateResult(blocked=True, response=error_response), sanitized

    gate = run_safety_gate(
        session,
        client_info,
        sid,
        user_message,
        sanitized,
        triage_result=None,
        recommendation_client=recommendation_client,
        phase="pre",
    )
    return gate, sanitized


def run_safety_gate(
    session: Any,
    client_info: ChatClientInfo,
    sid: Optional[str],
    user_message: str,
    sanitized_message: str,
    *,
    triage_result: Optional[dict] = None,
    recommendation_client: Any = None,
    phase: str = "full",
) -> SafetyGateResult:
    from src.handlers.chat.chat_diagnosis_handler import handle_diagnosis_if_detected
    from src.handlers.chat.chat_emergency_handler import handle_emergency_if_detected
    from src.handlers.chat.chat_inappropriate_route import handle_inappropriate_message_if_detected

    if phase in ("pre", "full"):
        diagnosis_resp = handle_diagnosis_if_detected(
            session, client_info, sid, sanitized_message
        )
        if diagnosis_resp is not None:
            return SafetyGateResult(blocked=True, response=diagnosis_resp)

    if phase == "pre":
        inapp_resp = handle_inappropriate_message_if_detected(
            session,
            client_info,
            sid,
            user_message,
            sanitized_message,
            recommendation_client,
        )
        if inapp_resp is not None:
            return SafetyGateResult(blocked=True, response=inapp_resp)
        return SafetyGateResult()

    if phase == "full" and recommendation_client is not None:
        try:
            from config.llm_flags import is_meta_safety_shortpath_enabled
            from src.dialogue.routing.meta_safety_shortpath import (
                is_meta_safety_shortpath_eligible,
            )

            if is_meta_safety_shortpath_enabled() and is_meta_safety_shortpath_eligible(
                triage_result, session
            ):
                return SafetyGateResult()
        except ImportError:
            pass

        emergency_resp = handle_emergency_if_detected(
            session,
            client_info,
            sid,
            sanitized_message,
            recommendation_client,
            triage_result,
        )
        if emergency_resp is not None:
            return SafetyGateResult(blocked=True, response=emergency_resp)

        inapp_resp = handle_inappropriate_message_if_detected(
            session,
            client_info,
            sid,
            user_message,
            sanitized_message,
            recommendation_client,
        )
        if inapp_resp is not None:
            return SafetyGateResult(blocked=True, response=inapp_resp)

    needs_review = False
    reason = ""
    if triage_result:
        conf = float(triage_result.get("confidence") or 1.0)
        if conf < 0.6:
            needs_review = True
            reason = "low_triage_confidence"
    if _borderline_crisis_hint(sanitized_message):
        needs_review = True
        reason = reason or "borderline_crisis_language"

    return SafetyGateResult(needs_llm_review=needs_review, review_reason=reason)
