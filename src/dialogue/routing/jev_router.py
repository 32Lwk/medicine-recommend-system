"""Jev IntentRouter adapter — Phase 1 shadow（実行 route は変えない）。

- state allowlist のみ送信
- session / dialogue_state / triage を一切 mutate しない
- 例外はすべて握りつぶす
"""
from __future__ import annotations

import atexit
import copy
import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Mapping, Optional

logger = logging.getLogger(__name__)

# Production payload boundary: current turn is ``user_input``; recent context is
# minimal prior turns only (not a session/medical-profile dump).
_MAX_RECENT_TURNS = 2
_MAX_RECENT_TURN_CHARS = 160
_MAX_MEDICINE_NAMES = 3
_APP_CONTEXT = "Japanese OTC medicine routing"
_EXECUTOR_WORKERS = 2
_MAX_PENDING_SHADOW = 8

_executor: Optional[ThreadPoolExecutor] = None
_executor_lock = threading.Lock()
_pending_count = 0
_pending_lock = threading.Lock()

_FORBIDDEN_STATE_KEYS = frozenset(
    {
        "baseline_triage_hint",
        "sid",
        "session_id",
        "user_id",
        "line_user_id",
        "user_attributes",
        "medical_profile",
        "profile",
        "answers",
        "raw_answers",
        "dialogue_state",
        "messages",
        "history",
        "rag",
        "rag_text",
        "system_prompt",
        "prompt",
        "api_key",
        "authorization",
        "token",
        "password",
        "email",
        "phone",
        "address",
        # Symptom / profile dumps — routing uses free-text user_input only.
        "active_symptoms",
        "symptoms",
        "diagnosis",
    }
)

_ALLOWED_TOP_LEVEL_KEYS = frozenset(
    {
        "channel",
        "user_input",
        "recent_turns",
        "recent_context",
        "meta",
        "app_context",
    }
)


class ForbiddenJevStateError(ValueError):
    """Allowlist 契約違反（-O でも消えない明示例外）。"""

    def __init__(self, keys: list[str]):
        self.keys = list(keys)
        super().__init__(f"forbidden jev state keys: {self.keys}")


def _collect_forbidden_keys(state: Mapping[str, Any]) -> list[str]:
    found: list[str] = []
    for key in state.keys():
        if key in _FORBIDDEN_STATE_KEYS:
            found.append(str(key))
    meta = state.get("meta")
    if isinstance(meta, Mapping):
        for key in meta.keys():
            if key in _FORBIDDEN_STATE_KEYS:
                found.append(f"meta.{key}")
    return found


def validate_jev_state_contract(state: Mapping[str, Any]) -> None:
    """禁止キー混入を -O でも検出して raise。本番向け契約ガード。"""
    found = _collect_forbidden_keys(state)
    if found:
        logger.error("jev_router forbidden state keys detected: %s", found)
        raise ForbiddenJevStateError(found)


def scrub_forbidden_jev_state_keys(state: dict[str, Any]) -> list[str]:
    """送信直前の防衛的 scrub。削除したキー名を返す（本文は残さない）。"""
    removed: list[str] = []
    for key in list(state.keys()):
        if key in _FORBIDDEN_STATE_KEYS:
            state.pop(key, None)
            removed.append(str(key))
    meta = state.get("meta")
    if isinstance(meta, dict):
        for key in list(meta.keys()):
            if key in _FORBIDDEN_STATE_KEYS:
                meta.pop(key, None)
                removed.append(f"meta.{key}")
    if removed:
        logger.error("jev_router scrubbed forbidden state keys: %s", removed)
    return removed


def _sync_recent_aliases(state: dict[str, Any]) -> None:
    """recent_turns と recent_context を同一参照に揃える（長さ不一致防止）。"""
    turns = state.get("recent_turns")
    ctx = state.get("recent_context")
    if isinstance(turns, list) and isinstance(ctx, list):
        if turns is not ctx and (
            len(turns) != len(ctx) or turns != ctx
        ):
            logger.error(
                "jev_router recent_turns/recent_context diverged "
                "(turns=%s context=%s); forcing alias sync",
                len(turns),
                len(ctx),
            )
        state["recent_context"] = turns
    elif isinstance(turns, list):
        state["recent_context"] = turns
    elif isinstance(ctx, list):
        state["recent_turns"] = ctx
        state["recent_context"] = ctx



def _effective_executor_workers() -> int:
    try:
        from src.dialogue.routing.jev_shadow_guards import get_shadow_guards

        return max(1, int(get_shadow_guards().config.concurrency or _EXECUTOR_WORKERS))
    except Exception:
        return int(_EXECUTOR_WORKERS)


def _effective_max_pending() -> int:
    """Soft pending cap.

    Tests patch ``_MAX_PENDING_SHADOW`` (e.g. to 0). When left at the import
    default (8), prefer live ``JEV_MAX_PENDING`` / shadow-guard config.
    """
    if int(_MAX_PENDING_SHADOW) != 8:
        return max(0, int(_MAX_PENDING_SHADOW))
    try:
        from src.dialogue.routing.jev_shadow_guards import get_shadow_guards

        return max(0, int(get_shadow_guards().config.max_pending))
    except Exception:
        return 8


def _get_executor() -> ThreadPoolExecutor:
    global _executor
    with _executor_lock:
        if _executor is None:
            _executor = ThreadPoolExecutor(
                max_workers=_effective_executor_workers(),
                thread_name_prefix="jev_shadow",
            )
        return _executor


def _shutdown_executor() -> None:
    global _executor
    with _executor_lock:
        if _executor is not None:
            try:
                _executor.shutdown(wait=False, cancel_futures=True)
            except TypeError:
                # Python <3.9 compat: cancel_futures unsupported
                try:
                    _executor.shutdown(wait=False)
                except Exception:
                    pass
            except Exception:
                pass
            _executor = None


atexit.register(_shutdown_executor)


def _reset_runtime_for_tests() -> None:
    """Test helper: drain pending counter and shut down the shadow executor."""
    global _pending_count
    _shutdown_executor()
    with _pending_lock:
        _pending_count = 0
    try:
        from src.dialogue.routing.jev_shadow_guards import reset_shadow_guards_for_tests

        reset_shadow_guards_for_tests()
    except Exception:
        pass


def _pending_depth() -> int:
    with _pending_lock:
        return int(_pending_count)


def _obs_hashes(model: Optional[str] = None) -> dict[str, Optional[str]]:
    try:
        from src.services.jev_decisions import INTENT_ROUTER_QUESTIONS
        from src.services.jev_metrics import config_hash_snapshot, prompt_hash_for_questions

        return {
            "prompt_hash": prompt_hash_for_questions(
                INTENT_ROUTER_QUESTIONS, model=model or _jev_model()
            ),
            "config_hash": config_hash_snapshot(),
        }
    except Exception:
        return {"prompt_hash": None, "config_hash": None}


def _sre_bundle() -> dict[str, Any]:
    try:
        from src.services.jev_sre_guards import observability_bundle

        return observability_bundle(queue_depth=_pending_depth())
    except Exception:
        return {"queue": {"pending": _pending_depth()}}


def _record_schedule_skip(
    *,
    correlation_id: Optional[str],
    legacy_decision: Any,
    snapshot: Mapping[str, Any],
    sid: Optional[str],
    error_class: str,
    eligible: bool = True,
    skip_reason: Optional[str] = None,
) -> None:
    """Fail-open skip metric (queue_full / circuit / rate / submit). Never raises."""
    try:
        from src.services.jev_metrics import build_state_shape, record_shadow_event

        hashes = _obs_hashes()
        reason = skip_reason or error_class
        record_shadow_event(
            correlation_id=correlation_id,
            legacy_decision=_decision_to_payload(legacy_decision),
            jev_decision=None,
            executed_decision=_decision_to_payload(legacy_decision),
            model=_jev_model(),
            attempted=False,
            succeeded=False,
            retry_count=0,
            fallback_reason="not_eligible",
            error_class=error_class,
            latency_ms=0.0,
            legacy_saved_calls=0,
            state_shape=build_state_shape(snapshot),
            sid=sid,
            eligible=eligible,
            skip_reason=reason,
            prompt_hash=hashes.get("prompt_hash"),
            config_hash=hashes.get("config_hash"),
            sre=_sre_bundle(),
        )
    except Exception:
        logger.debug("jev schedule_skip metric failed error_class=%s", error_class)


def _is_jev_enabled() -> bool:
    try:
        from config.llm_flags import is_jev_enabled

        return bool(is_jev_enabled())
    except Exception:
        return False


def _is_jev_intent_router_shadow_enabled() -> bool:
    try:
        from config.llm_flags import is_jev_intent_router_shadow_enabled

        return bool(is_jev_intent_router_shadow_enabled())
    except Exception:
        return False


def _jev_model() -> str:
    try:
        from config.routing_config import jev_model

        return str(jev_model() or "jev-latest")
    except Exception:
        return "jev-latest"


def _sanitize_user_text(user_text: Any) -> str:
    text = "" if user_text is None else str(user_text)
    text = text.replace("\x00", "").strip()
    # 極端な長文は送らない（本文はログに出さない）
    if len(text) > 4000:
        text = text[:4000]
    try:
        from src.dialogue.routing.jev_pii_redact import redact_pii_text

        text, _hits = redact_pii_text(text)
    except Exception:
        pass
    return text


def _role_of(msg: Mapping[str, Any]) -> str:
    role = msg.get("role") or msg.get("type") or "user"
    role_s = str(role).strip().lower()
    if role_s in ("bot", "assistant", "ai", "system"):
        if role_s == "bot" or role_s == "ai":
            return "assistant"
        return role_s if role_s in ("assistant", "system") else "assistant"
    return "user"


def _content_of(msg: Mapping[str, Any]) -> str:
    content = msg.get("content")
    if content is None:
        content = msg.get("text")
    return str(content or "").strip()


def _trim_recent_turn_content(text: Any) -> str:
    content = "" if text is None else str(text)
    content = content.replace("\x00", "").strip()
    if len(content) > _MAX_RECENT_TURN_CHARS:
        content = content[:_MAX_RECENT_TURN_CHARS]
    try:
        from src.dialogue.routing.jev_pii_redact import redact_pii_text

        content, _hits = redact_pii_text(content)
    except Exception:
        pass
    return content


def _extract_recent_turns(session: Any, sid: Optional[str]) -> list[dict[str, str]]:
    messages: list[Any] = []
    try:
        from src.services.triage_history import get_recent_messages

        # Pull a few extras then truncate to minimal recent depth.
        messages = list(get_recent_messages(session, sid, limit=_MAX_RECENT_TURNS + 2) or [])
    except Exception:
        try:
            raw = []
            if session is not None and hasattr(session, "get"):
                raw = list(session.get("messages") or [])
            messages = raw[-(_MAX_RECENT_TURNS + 2) :]
        except Exception:
            messages = []

    turns: list[dict[str, str]] = []
    for msg in messages:
        if not isinstance(msg, Mapping):
            continue
        content = _trim_recent_turn_content(_content_of(msg))
        if not content:
            continue
        turns.append({"role": _role_of(msg), "content": content})
    return turns[-_MAX_RECENT_TURNS:]


def _last_routes(session: Any) -> tuple[Optional[str], Optional[str]]:
    """dialogue_state.routing → _routing_decision。_intent_router_shadow は使わない。"""
    primary = None
    sub = None
    try:
        from src.dialogue.context import load_dialogue_context

        ctx = load_dialogue_context(session)
        routing = ctx.get("routing") if isinstance(ctx, dict) else None
        if isinstance(routing, dict) and routing.get("primary_route"):
            primary = routing.get("primary_route")
            sub = routing.get("sub_route")
            return (
                str(primary) if primary is not None else None,
                str(sub) if sub is not None else None,
            )
    except Exception:
        pass

    try:
        if session is not None and hasattr(session, "get"):
            rd = session.get("_routing_decision")
            if isinstance(rd, dict) and rd.get("primary_route"):
                primary = rd.get("primary_route")
                sub = rd.get("sub_route")
                return (
                    str(primary) if primary is not None else None,
                    str(sub) if sub is not None else None,
                )
    except Exception:
        pass
    return None, None


def _medicine_names(session: Any, sid: Optional[str]) -> list[str]:
    names: list[str] = []
    try:
        from src.services.medicine_thread_context import resolve_session_recommended_medicines

        recommended = resolve_session_recommended_medicines(
            session,
            sid=sid,
            max_products=_MAX_MEDICINE_NAMES,
        )
        for med in recommended or []:
            if not isinstance(med, Mapping):
                continue
            name = str(med.get("product_name") or med.get("name") or "").strip()
            if name and name not in names:
                names.append(name)
            if len(names) >= _MAX_MEDICINE_NAMES:
                break
    except Exception:
        logger.debug("jev medicine names resolve skipped", exc_info=True)
    return names[:_MAX_MEDICINE_NAMES]


def _normalize_focus(medicine_qa_focus: Any) -> Optional[list[str]]:
    if medicine_qa_focus is None:
        return None
    if isinstance(medicine_qa_focus, str):
        text = medicine_qa_focus.strip()
        return [text] if text else None
    if isinstance(medicine_qa_focus, (list, tuple)):
        out = [str(x).strip() for x in medicine_qa_focus if str(x).strip()]
        return out[:8] or None
    return None


def build_jev_router_state(
    user_text: Any,
    session: Any,
    sid: Optional[str],
    *,
    triage_result: Any = None,
    medicine_qa_focus: Any = None,
) -> dict[str, Any]:
    """Jev 送信用 allowlist state。baseline_triage_hint は絶対に含めない。

    triage_result は受け取るが category 等は送信しない（Phase1 minimal）。
    """
    del triage_result  # 明示的に未使用 — baseline_triage_hint 禁止

    channel = "web"
    try:
        from src.services.concierge_channel import resolve_concierge_channel

        channel = resolve_concierge_channel(sid) or "web"
    except Exception:
        channel = "web"

    last_primary, last_sub = _last_routes(session)
    medicines = _medicine_names(session, sid)
    focus = _normalize_focus(medicine_qa_focus)

    meta: dict[str, Any] = {}
    if last_primary:
        meta["last_primary_route"] = last_primary
    if last_sub is not None:
        meta["last_sub_route"] = last_sub
    if medicines:
        meta["last_recommended_medicines"] = medicines
    # Do not send active_symptoms / diagnosis / medical_profile dumps.
    if focus:
        meta["medicine_qa_focus"] = focus

    turns = _extract_recent_turns(session, sid)
    state: dict[str, Any] = {
        "channel": channel if channel in ("web", "line") else "web",
        "user_input": _sanitize_user_text(user_text),
        # Contract name + pilot-eval alias (scripts/eval used recent_context).
        "recent_turns": turns,
        "recent_context": turns,
        "meta": meta,
        "app_context": _APP_CONTEXT,
    }

    # 契約: 禁止キー検査は assert ではなく明示 raise（python -O でも有効）
    validate_jev_state_contract(state)
    unknown = [k for k in state.keys() if k not in _ALLOWED_TOP_LEVEL_KEYS]
    if unknown:
        logger.error("jev_router unexpected top-level keys: %s", unknown)
        raise ForbiddenJevStateError([f"unexpected:{k}" for k in unknown])

    return state


def _decision_to_payload(decision: Any) -> Any:
    if decision is None:
        return None
    if isinstance(decision, Mapping):
        return dict(decision)
    try:
        from src.services.jev_decisions import JevShadowDecision, to_route_dict

        if isinstance(decision, JevShadowDecision):
            payload = to_route_dict(decision)
            payload["noul"] = dict(decision.noul or {})
            payload["risk_flags"] = list(decision.risk_flags or [])
            return payload
    except Exception:
        pass
    if hasattr(decision, "to_dialogue_routing_dict"):
        try:
            return decision.to_dialogue_routing_dict()
        except Exception:
            pass
    return decision


def _classify_failure(exc: BaseException) -> tuple[str, str]:
    name = type(exc).__name__
    msg = str(exc).lower()
    if isinstance(exc, TimeoutError) or "timeout" in name.lower() or "timeout" in msg:
        return "timeout", name
    if "429" in msg:
        return "http_429_exhausted", name
    if any(code in msg for code in ("500", "502", "503", "504")):
        return "http_5xx_exhausted", name
    if any(code in msg for code in ("400", "401", "403", "404")):
        return "http_4xx", name
    if "schema" in msg or "invalid" in msg:
        return "invalid_schema", name
    if "network" in msg or "connection" in msg:
        return "network_error", name
    return "network_error", name


def _shadow_worker(
    *,
    state: dict[str, Any],
    legacy_decision: Any,
    correlation_id: Optional[str],
    deterministic_signals: Any,
    sid_for_hash: Optional[str],
) -> None:
    from src.services.jev_metrics import (
        build_state_shape,
        lookup_executed_decision,
        record_shadow_event,
        trace_hash_for_sid,
    )

    started = time.monotonic()
    model = _jev_model()
    retry_count = 0
    usage = None
    jev_decision = None
    fallback_reason = None
    error_class = None
    succeeded = False

    try:
        try:
            from src.services.jev_client import evaluate_system_one
            from src.services.jev_decisions import INTENT_ROUTER_QUESTIONS, parse_jev_answers
        except ImportError as exc:
            fallback_reason = "not_eligible"
            error_class = type(exc).__name__
            record_shadow_event(
                correlation_id=correlation_id,
                legacy_decision=_decision_to_payload(legacy_decision),
                jev_decision=None,
                executed_decision=lookup_executed_decision(correlation_id)
                or _decision_to_payload(legacy_decision),
                model=model,
                attempted=False,
                succeeded=False,
                retry_count=0,
                fallback_reason=fallback_reason,
                error_class=error_class,
                latency_ms=round((time.monotonic() - started) * 1000.0, 3),
                legacy_saved_calls=0,
                state_shape=build_state_shape(state),
                trace_hash=trace_hash_for_sid(sid_for_hash),
            )
            return

        immutable = copy.deepcopy(state)
        scrub_forbidden_jev_state_keys(immutable)
        _sync_recent_aliases(immutable)

        result = evaluate_system_one(
            state=immutable,
            questions=INTENT_ROUTER_QUESTIONS,
            model=model,
        )
        usage = getattr(result, "usage", None)
        if usage is None and isinstance(result, Mapping):
            usage = result.get("usage")
        retry_count = int(getattr(result, "retry_count", 0) or 0)
        result_model = getattr(result, "model", None)
        if result_model:
            model = str(result_model)

        ok_attr = getattr(result, "ok", None)
        if ok_attr is None and isinstance(result, Mapping) and "ok" in result:
            ok_attr = result.get("ok")
        if ok_attr is None:
            # mocks / partial results may omit ok; treat error_class as failure signal
            err_probe = getattr(result, "error_class", None)
            if err_probe is None and isinstance(result, Mapping):
                err_probe = result.get("error_class")
            ok = err_probe is None
        else:
            ok = bool(ok_attr)
        if not ok:
            fallback_reason = getattr(result, "error_class", None) or (
                result.get("error_class") if isinstance(result, Mapping) else None
            )
            error_class = fallback_reason or "network_error"
            succeeded = False
        else:
            answers = getattr(result, "answers", None)
            if answers is None and isinstance(result, Mapping):
                answers = result.get("answers")

            try:
                from config.routing_config import jev_noul_threshold

                threshold = float(jev_noul_threshold())
            except Exception:
                threshold = 0.75

            jev_decision = parse_jev_answers(
                answers if isinstance(answers, dict) else {},
                deterministic_signals=deterministic_signals,
                noul_threshold=threshold,
            )
            if getattr(jev_decision, "valid", True):
                succeeded = True
            else:
                succeeded = False
                fallback_reason = "invalid_schema"
                error_class = getattr(jev_decision, "invalid_reason", None) or "invalid_schema"
    except Exception as exc:
        fallback_reason, error_class = _classify_failure(exc)
        # Never attach exc_info — exception chains must not reach logs.
        logger.debug("jev shadow worker failed: %s", error_class)
        succeeded = False

    try:
        from src.dialogue.routing.jev_shadow_guards import get_shadow_guards

        guards = get_shadow_guards()
        if succeeded:
            tok = 0
            try:
                if usage is not None:
                    tok = int(
                        getattr(usage, "total_tokens", None)
                        or getattr(usage, "input_tokens", None)
                        or (usage.get("total_tokens") if isinstance(usage, Mapping) else 0)
                        or 0
                    )
            except Exception:
                tok = 0
            guards.record_success(tokens=tok)
        else:
            guards.record_failure()
    except Exception:
        pass

    try:
        latency_ms = round((time.monotonic() - started) * 1000.0, 3)
        executed = lookup_executed_decision(correlation_id) or _decision_to_payload(
            legacy_decision
        )
        record_shadow_event(
            correlation_id=correlation_id,
            legacy_decision=_decision_to_payload(legacy_decision),
            jev_decision=_decision_to_payload(jev_decision),
            executed_decision=executed,
            model=model,
            attempted=True,
            succeeded=succeeded,
            retry_count=retry_count,
            fallback_reason=fallback_reason,
            error_class=error_class,
            latency_ms=latency_ms,
            usage=usage,
            legacy_saved_calls=0,
            state_shape=build_state_shape(state),
            trace_hash=trace_hash_for_sid(sid_for_hash),
            risk_flags=getattr(jev_decision, "risk_flags", None)
            if jev_decision is not None
            else None,
            eligible=True,
            skip_reason=None,
            prompt_hash=_obs_hashes(model).get("prompt_hash"),
            config_hash=_obs_hashes(model).get("config_hash"),
            sre=_sre_bundle(),
        )
    except Exception:
        # Log write failure must not reach the request path (sync) or crash workers.
        logger.debug("jev shadow metrics emit failed")


def schedule_jev_shadow(
    *,
    state: Mapping[str, Any],
    legacy_decision: Any,
    correlation_id: Optional[str],
    deterministic_signals: Any = None,
    sync: bool = False,
    sid: Optional[str] = None,
    force: bool = False,
) -> bool:
    """Jev shadow を schedule。True=投入/同期実行、False=スキップ。

    session は受け取らない（mutate 禁止）。flags OFF 時はスキップ。
    Eligibility v1: SessionOps / deterministic high-risk / policy block は
    Jev API を呼ばず not-attempted として記録する（production/eval 共通契約）。
    queue full / submit 失敗時は本線をブロックしない。
    False を返すと呼び出し側（router）は correlation stash を行わない
    （`_jev_shadow_correlation_id` lifecycle は Supervisor 所有の router/dispatcher）。
    """
    global _pending_count

    try:
        if not force and (not _is_jev_enabled() or not _is_jev_intent_router_shadow_enabled()):
            return False

        snapshot = copy.deepcopy(dict(state))
        scrub_forbidden_jev_state_keys(snapshot)
        _sync_recent_aliases(snapshot)

        user_text = ""
        try:
            user_text = str(snapshot.get("user_input") or snapshot.get("user_text") or "")
        except Exception:
            user_text = ""

        try:
            from src.dialogue.routing.pre_route_signals import collect_pre_route_signals
            from src.services.jev_eligibility import decide_jev_intent_eligibility

            signals = collect_pre_route_signals(
                user_text,
                deterministic_signals=deterministic_signals,
            )
            eligibility = decide_jev_intent_eligibility(signals)
        except Exception:
            # AE6-H2: fail closed for Jev API — do not call when eligibility cannot be decided.
            eligibility = None
            _record_eligibility_skip(
                correlation_id=correlation_id,
                legacy_decision=legacy_decision,
                snapshot=snapshot,
                sid=sid,
                eligibility=type(
                    "E",
                    (),
                    {
                        "reason": "signal_evaluation_error",
                        "sessionops_fast_path_suppressed": False,
                    },
                )(),
            )
            return False

        if eligibility is not None and not eligibility.eligible and not force:
            _record_eligibility_skip(
                correlation_id=correlation_id,
                legacy_decision=legacy_decision,
                snapshot=snapshot,
                sid=sid,
                eligibility=eligibility,
            )
            return False

        kwargs = {
            "state": snapshot,
            "legacy_decision": legacy_decision,
            "correlation_id": correlation_id,
            "deterministic_signals": deterministic_signals,
            "sid_for_hash": sid,
        }

        # R19: circuit / rate / cost admit (fail-open for user path; skip shadow only)
        try:
            from src.dialogue.routing.jev_shadow_guards import get_shadow_guards

            guards = get_shadow_guards()
            with _pending_lock:
                pending_now = _pending_count
            soft_cap = _effective_max_pending()
            # Align admit queue check with module soft-cap (tests patch _MAX_PENDING_SHADOW).
            admit_pending = pending_now
            if soft_cap <= pending_now or soft_cap == 0:
                admit_pending = max(pending_now, guards.config.max_pending)
            est_tokens = max(1, len(user_text) // 2)
            admit = guards.check_admit(
                pending_count=admit_pending, est_tokens=est_tokens
            )
            if not admit.allow:
                _record_schedule_skip(
                    correlation_id=correlation_id,
                    legacy_decision=legacy_decision,
                    snapshot=snapshot,
                    sid=sid,
                    error_class=admit.reason,
                )
                logger.debug(
                    "jev shadow skipped: guard=%s circuit=%s",
                    admit.reason,
                    admit.circuit_state,
                )
                return False
        except Exception:
            logger.debug("jev shadow guard check failed; continuing fail-open to queue")

        if sync:
            try:
                from src.dialogue.routing.jev_shadow_guards import get_shadow_guards

                get_shadow_guards().record_scheduled()
            except Exception:
                pass
            try:
                _shadow_worker(**kwargs)
            except Exception:
                logger.debug("jev shadow sync failed")
            return True

        with _pending_lock:
            if _pending_count >= _effective_max_pending():
                _record_schedule_skip(
                    correlation_id=correlation_id,
                    legacy_decision=legacy_decision,
                    snapshot=snapshot,
                    sid=sid,
                    error_class="queue_full",
                )
                logger.debug("jev shadow skipped: queue full")
                return False
            _pending_count += 1

        def _wrapped() -> None:
            global _pending_count
            try:
                _shadow_worker(**kwargs)
            except Exception:
                logger.debug("jev shadow async failed")
            finally:
                with _pending_lock:
                    _pending_count = max(0, _pending_count - 1)

        try:
            from src.dialogue.routing.jev_shadow_guards import get_shadow_guards

            get_shadow_guards().record_scheduled()
        except Exception:
            pass

        try:
            _get_executor().submit(_wrapped)
        except Exception:
            with _pending_lock:
                _pending_count = max(0, _pending_count - 1)
            _record_schedule_skip(
                correlation_id=correlation_id,
                legacy_decision=legacy_decision,
                snapshot=snapshot,
                sid=sid,
                error_class="submit_failed",
            )
            logger.debug("jev shadow submit failed")
            return False
        return True
    except Exception:
        logger.debug("schedule_jev_shadow failed")
        return False


def _record_eligibility_skip(
    *,
    correlation_id: Optional[str],
    legacy_decision: Any,
    snapshot: Mapping[str, Any],
    sid: Optional[str],
    eligibility: Any,
) -> None:
    """Record intentional non-attempt (SessionOps / high-risk / policy). Never raises."""
    try:
        from src.services.jev_metrics import build_state_shape, record_shadow_event

        reason = getattr(eligibility, "reason", None) or "not_eligible"
        hashes = _obs_hashes()
        record_shadow_event(
            correlation_id=correlation_id,
            legacy_decision=_decision_to_payload(legacy_decision),
            jev_decision=None,
            executed_decision=_decision_to_payload(legacy_decision),
            model=_jev_model(),
            attempted=False,
            succeeded=False,
            retry_count=0,
            fallback_reason="not_eligible",
            error_class=str(reason),
            latency_ms=0.0,
            legacy_saved_calls=0,
            state_shape=build_state_shape(snapshot),
            sid=sid,
            eligible=False,
            skip_reason=str(reason),
            prompt_hash=hashes.get("prompt_hash"),
            config_hash=hashes.get("config_hash"),
            sre=_sre_bundle(),
            extra={
                "jev_eligible": False,
                "jev_eligibility_reason": str(reason),
                "jev_attempted": False,
                "sessionops_fast_path_suppressed": bool(
                    getattr(eligibility, "sessionops_fast_path_suppressed", False)
                ),
                "eligibility_contract_version": getattr(
                    eligibility, "eligibility_contract_version", None
                )
                or "jev-intent-eligibility-v1",
            },
        )
    except Exception:
        logger.debug("jev eligibility_skip metric failed")


# NOTE: original schedule_jev_shadow body replaced above — keep helpers below.


def run_jev_shadow_sync(
    *,
    state: Mapping[str, Any],
    legacy_decision: Any,
    correlation_id: Optional[str] = None,
    deterministic_signals: Any = None,
    sid: Optional[str] = None,
    force: bool = True,
) -> bool:
    """テスト用同期エントリ。"""
    return schedule_jev_shadow(
        state=state,
        legacy_decision=legacy_decision,
        correlation_id=correlation_id,
        deterministic_signals=deterministic_signals,
        sync=True,
        sid=sid,
        force=force,
    )


__all__ = [
    "ForbiddenJevStateError",
    "build_jev_router_state",
    "run_jev_shadow_sync",
    "schedule_jev_shadow",
    "scrub_forbidden_jev_state_keys",
    "validate_jev_state_contract",
]
