"""Jev IntentRouter primary — legacy Stage B（OpenAI IntentRouter LLM）を Jev 判定で置き換える。

- deterministic gate / post guards は呼び出し側（legacy_router）に残す
- Jev を採用できないとき（対象外・guard 拒否・失敗・低信頼・高リスク軸）は None を返し、
  呼び出し側が OpenAI Stage B へフォールバックする
- 例外はすべて握りつぶす（ユーザー経路を止めない）
"""
from __future__ import annotations

import copy
import logging
import time
import uuid
from typing import Any, Optional

from src.dialogue.routing.types import RouteDecision

logger = logging.getLogger(__name__)

_ROUTABLE_PRIMARY = frozenset(
    {"Physical", "SessionOps", "Concierge", "Store", "Counseling"}
)


def _is_primary_enabled() -> bool:
    try:
        from config.llm_flags import is_jev_intent_router_primary_enabled

        return bool(is_jev_intent_router_primary_enabled())
    except Exception:
        return False


def _confidence_floor() -> float:
    try:
        from config.routing_config import jev_confidence_floor

        return float(jev_confidence_floor())
    except Exception:
        return 0.70


def _noul_threshold() -> float:
    try:
        from config.routing_config import jev_noul_threshold

        return float(jev_noul_threshold())
    except Exception:
        return 0.75


def _usage_tokens(usage: Any) -> int:
    try:
        if not isinstance(usage, dict):
            return 0
        return int(usage.get("total_tokens") or usage.get("input_tokens") or 0)
    except Exception:
        return 0


def _record(
    *,
    correlation_id: str,
    gate_decision: Optional[RouteDecision],
    jev_decision: Any,
    executed: Optional[RouteDecision],
    state: Any,
    sid: Optional[str],
    model: Optional[str],
    attempted: bool,
    succeeded: bool,
    retry_count: int,
    fallback_reason: Optional[str],
    error_class: Optional[str],
    started: float,
    usage: Any,
    eligible: bool,
) -> None:
    try:
        from src.dialogue.routing.jev_router import (
            _decision_to_payload,
            _obs_hashes,
            _sre_bundle,
        )
        from src.services.jev_metrics import build_state_shape, record_shadow_event

        hashes = _obs_hashes(model)
        record_shadow_event(
            correlation_id=correlation_id,
            legacy_decision=_decision_to_payload(gate_decision),
            jev_decision=_decision_to_payload(jev_decision),
            executed_decision=_decision_to_payload(executed),
            model=model,
            mode="primary",
            attempted=attempted,
            succeeded=succeeded,
            retry_count=retry_count,
            fallback_reason=fallback_reason,
            error_class=error_class,
            latency_ms=round((time.monotonic() - started) * 1000.0, 3),
            usage=usage,
            legacy_saved_calls=1 if executed is not None else 0,
            state_shape=build_state_shape(state) if state is not None else None,
            sid=sid,
            eligible=eligible,
            skip_reason=None if attempted else fallback_reason,
            prompt_hash=hashes.get("prompt_hash"),
            config_hash=hashes.get("config_hash"),
            sre=_sre_bundle(),
        )
    except Exception:
        logger.debug("jev primary metrics emit failed")


def try_jev_primary_route(
    user_text: str,
    session: Any,
    sid: Optional[str],
    *,
    triage_result: Optional[dict[str, Any]] = None,
    gate_decision: Optional[RouteDecision] = None,
) -> Optional[RouteDecision]:
    """Jev 判定を RouteDecision で返す。採用しない場合は None（OpenAI Stage B へ）。"""
    if not _is_primary_enabled():
        return None

    started = time.monotonic()
    correlation_id = str(uuid.uuid4())
    state: Optional[dict[str, Any]] = None
    model: Optional[str] = None

    def _skip(reason: str, *, eligible: bool = True) -> None:
        _record(
            correlation_id=correlation_id,
            gate_decision=gate_decision,
            jev_decision=None,
            executed=None,
            state=state,
            sid=sid,
            model=model,
            attempted=False,
            succeeded=False,
            retry_count=0,
            fallback_reason=reason,
            error_class=reason,
            started=started,
            usage=None,
            eligible=eligible,
        )

    try:
        from src.dialogue.routing.jev_router import (
            _jev_model,
            _sync_recent_aliases,
            build_jev_router_state,
            scrub_forbidden_jev_state_keys,
        )
        from src.dialogue.routing.pre_route_signals import collect_pre_route_signals
        from src.dialogue.routing.router import _deterministic_signals_from_context
        from src.services.jev_eligibility import decide_jev_intent_eligibility

        model = _jev_model()
        deterministic_signals = (
            _deterministic_signals_from_context(
                legacy=gate_decision, triage_result=triage_result
            )
            if gate_decision is not None
            else {}
        )
        signals = collect_pre_route_signals(
            user_text or "", deterministic_signals=deterministic_signals
        )
        eligibility = decide_jev_intent_eligibility(signals)
        if not eligibility.eligible:
            _skip(str(eligibility.reason), eligible=False)
            return None

        state = build_jev_router_state(user_text, session, sid, triage_result=triage_result)
        payload = copy.deepcopy(state)
        scrub_forbidden_jev_state_keys(payload)
        _sync_recent_aliases(payload)

        from src.dialogue.routing.jev_shadow_guards import get_shadow_guards

        guards = get_shadow_guards()
        admit = guards.check_admit(
            pending_count=0, est_tokens=max(1, len(str(payload.get("user_input") or "")) // 2)
        )
        if not admit.allow:
            _skip(admit.reason)
            return None
        guards.record_scheduled()

        from src.services.jev_client import evaluate_system_one
        from src.services.jev_decisions import (
            INTENT_ROUTER_QUESTIONS,
            jev_alone_may_confirm,
            parse_jev_answers,
        )

        result = evaluate_system_one(
            state=payload, questions=INTENT_ROUTER_QUESTIONS, model=model
        )
        model = result.model or model
        if not result.ok:
            guards.record_failure()
            _record(
                correlation_id=correlation_id,
                gate_decision=gate_decision,
                jev_decision=None,
                executed=None,
                state=state,
                sid=sid,
                model=model,
                attempted=True,
                succeeded=False,
                retry_count=result.retry_count,
                fallback_reason=result.error_class,
                error_class=result.error_class,
                started=started,
                usage=result.usage,
                eligible=True,
            )
            return None

        jev_decision = parse_jev_answers(
            result.answers or {},
            deterministic_signals=deterministic_signals,
            noul_threshold=_noul_threshold(),
        )
        if not jev_decision.valid:
            guards.record_failure()
        else:
            guards.record_success(tokens=_usage_tokens(result.usage))

        fallback_reason: Optional[str] = None
        if not jev_decision.valid:
            fallback_reason = "invalid_schema"
        elif jev_decision.primary_route not in _ROUTABLE_PRIMARY or not jev_alone_may_confirm(
            jev_decision.primary_route
        ):
            fallback_reason = "jev_alone_forbidden_axis"
        elif float(jev_decision.primary_confidence) < _confidence_floor():
            fallback_reason = "low_confidence"

        executed: Optional[RouteDecision] = None
        if fallback_reason is None:
            from src.dialogue.routing.intent_router_llm import (
                maybe_correct_concierge_app_about_route,
                maybe_correct_concierge_keyword_meta_route,
            )

            executed = RouteDecision(
                primary_route=jev_decision.primary_route,  # type: ignore[arg-type]
                sub_route=jev_decision.sub_route,
                confidence=float(jev_decision.primary_confidence),
                resolved_by="jev",
                source=f"jev_primary:{jev_decision.source}",
                meta={"jev_correlation_id": correlation_id},
            )
            executed = maybe_correct_concierge_keyword_meta_route(
                executed, user_text, triage_result=triage_result
            )
            executed = maybe_correct_concierge_app_about_route(executed, user_text)

        _record(
            correlation_id=correlation_id,
            gate_decision=gate_decision,
            jev_decision=jev_decision,
            executed=executed,
            state=state,
            sid=sid,
            model=model,
            attempted=True,
            succeeded=bool(jev_decision.valid),
            retry_count=result.retry_count,
            fallback_reason=fallback_reason,
            error_class=None if jev_decision.valid else jev_decision.invalid_reason,
            started=started,
            usage=result.usage,
            eligible=True,
        )
        return executed
    except Exception:
        logger.debug("jev primary route failed; falling back to OpenAI Stage B")
        return None


__all__ = ["try_jev_primary_route"]
