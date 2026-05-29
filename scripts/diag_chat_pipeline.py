#!/usr/bin/env python3
"""
チャット POST パイプラインのオフライン診断 CLI（サーバー不要）。

使い方:
  python scripts/diag_chat_pipeline.py full          # handle_chat_post 全体（LLM モック）
  python scripts/diag_chat_pipeline.py pipeline     # run_chat_post_pipeline のみ
  python scripts/diag_chat_pipeline.py steps        # パイプラインを段階実行して停止位置を特定
  python scripts/diag_chat_pipeline.py safety       # SafetyGate（pre / full）
  python scripts/diag_chat_pipeline.py safety-parts # 診断名・不適切入力ハンドラのみ
"""
from __future__ import annotations

import argparse
import os
import sys
import time
import traceback
from contextlib import ExitStack
from typing import Any, Callable
from unittest.mock import MagicMock, patch

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

os.environ.setdefault("LLM_AGENT_ENABLED", "true")

DEFAULT_MESSAGE = "頭が痛い"
DEFAULT_TRIAGE = {
    "category": "Physical",
    "confidence": 0.9,
    "subcategory": "headache",
    "requires_immediate_action": False,
}
DEFAULT_RB = {
    "status": "success",
    "recommended_medicines": [
        {
            "product_name": "テスト薬",
            "manufacturer": "A社",
            "efficacy": "頭痛",
            "score": 80,
            "explanation": "テスト",
        }
    ],
    "nlu_result": {
        "symptoms": [{"name": "頭痛", "severity": "中等度"}],
        "confidence_score": 0.8,
        "gender_detected": {"detected": False},
        "pregnancy_possible": {"detected": False},
    },
    "usage_notes": "用法注意",
    "doctor_consultation": "",
}


def _log(msg: str) -> None:
    print(msg, flush=True)


def _step(name: str, fn: Callable[[], Any]) -> Any:
    t0 = time.perf_counter()
    _log(f"[STEP] {name} ...")
    try:
        out = fn()
        _log(f"[OK]   {name} ({time.perf_counter() - t0:.2f}s)")
        return out
    except Exception as exc:
        _log(f"[FAIL] {name} ({time.perf_counter() - t0:.2f}s): {exc}")
        traceback.print_exc()
        raise


def _make_session() -> Any:
    from src.utils.request_safe_session import RequestSafeSession

    session = RequestSafeSession()
    session["messages"] = []
    session["user_attributes"] = {}
    return session


def _make_client() -> Any:
    from src.utils.chat_http_context import ChatClientInfo

    return ChatClientInfo(client_ip="127.0.0.1", user_agent="diag-chat-pipeline")


def _common_patches(stack: ExitStack, *, triage: dict | None = None) -> None:
    """DB・処理状況・トリアージ・オーケストレータをモック。"""
    triage = triage or DEFAULT_TRIAGE
    rb = DEFAULT_RB
    fake_json = (
        '{"category":"Physical","confidence":0.9,"subcategory":"headache",'
        '"requires_immediate_action":false,"reasoning":"test"}'
    )
    fake_completion = MagicMock()
    fake_completion.choices = [MagicMock(message=MagicMock(content=fake_json))]

    for target, kwargs in (
        ("src.agents.triage_agent.run_triage_agent", {"return_value": triage}),
        ("src.services.llm_triage.llm_triage", {"return_value": triage}),
        ("src.core.llm_client.chat_completion_create", {"return_value": fake_completion}),
        ("src.core.llm_client.chat_completion_stream", {"return_value": "テストアドバイス"}),
        ("src.core.rule_based_recommendation.hybrid_nlu_extraction", {"return_value": rb["nlu_result"]}),
        (
            "src.core.rule_based_recommendation.rule_based_medicine_recommendation",
            {"return_value": rb},
        ),
        ("src.handlers.chat.nlu_resolve.resolve_nlu_for_recommendation", {"return_value": rb["nlu_result"]}),
        ("src.services.database.get_database", {"return_value": None}),
        ("src.services.processing_status._flush_to_db", {}),
        (
            "src.handlers.chat_orchestrator.try_orchestrator_route",
            {"return_value": ({"status": "ok", "message_count": 1}, 200)},
        ),
        ("src.services.chat_inflight.try_begin_chat_job", {"return_value": True}),
        ("src.services.chat_inflight.end_chat_job", {}),
    ):
        stack.enter_context(patch(target, **kwargs))


def cmd_full(message: str) -> int:
    from src.handlers.chat_handler import handle_chat_post

    session = _make_session()
    client = _make_client()
    monitor = MagicMock()
    sid = f"diag-full-{int(time.time())}"

    with ExitStack() as stack:
        _common_patches(stack)
        body, code = _step(
            "handle_chat_post (mocked)",
            lambda: handle_chat_post(session, client, message, sid, monitor),
        )
        bot_count = len([m for m in session.get("messages", []) if m.get("type") == "bot"])
        _log(f"result: status={code} body={body}")
        _log(f"bot messages: {bot_count}")
    return 0


def cmd_pipeline(message: str) -> int:
    from src.handlers.chat.chat_post_pipeline import run_chat_post_pipeline

    session = _make_session()
    client = _make_client()
    monitor = MagicMock()
    sid = f"diag-pipeline-{int(time.time())}"

    with ExitStack() as stack:
        _common_patches(stack)
        t0 = time.perf_counter()
        body, code = run_chat_post_pipeline(session, client, message, sid, monitor)
        elapsed = time.perf_counter() - t0
        _log(f"done status={code} elapsed={elapsed:.2f}s msgs={len(session.get('messages', []))}")
        _log(f"body={body}")
    return 0


def cmd_steps(message: str) -> int:
    from src.handlers.chat.chat_llm_gate import check_llm_budget_block, setup_llm_request
    from src.handlers.chat.chat_post_init import parse_incoming_message
    from src.handlers.chat.chat_post_pipeline import ChatPostContext, run_chat_post_pipeline
    from src.handlers.chat.chat_triage import run_triage
    from src.agents.safety_gate import run_safety_gate, run_safety_gate_pre

    session = _make_session()
    client = _make_client()
    monitor = MagicMock()
    sid = f"diag-steps-{int(time.time())}"

    with ExitStack() as stack:
        stack.enter_context(patch("src.services.database.get_database", return_value=None))
        stack.enter_context(patch("src.services.processing_status._flush_to_db"))
        stack.enter_context(
            patch(
                "src.handlers.chat_orchestrator.try_orchestrator_route",
                return_value=({"status": "ok", "message_count": 1}, 200),
            )
        )
        stack.enter_context(patch("src.agents.triage_agent.run_triage_agent", return_value=DEFAULT_TRIAGE))
        stack.enter_context(
            patch("src.handlers.chat.emergency_dispatch.dispatch_emergency", return_value=None)
        )
        stack.enter_context(
            patch("src.handlers.chat.chat_counseling_flow.run_counseling_flow", return_value=(None, DEFAULT_TRIAGE))
        )

        ctx = ChatPostContext(
            session=session,
            client_info=client,
            sid=sid,
            monitor=monitor,
            user_agent=client.user_agent,
            client_ip=client.client_ip,
            trace_id="diag-steps",
        )
        ctx.user_message = _step("parse_incoming_message", lambda: parse_incoming_message(session, message))
        _step("setup_llm_request", lambda: setup_llm_request(session, sid) or True)
        budget = _step("check_llm_budget_block", lambda: check_llm_budget_block(session, sid))
        if budget is not None:
            _log(f"budget blocked: {budget}")
            return 0

        pre, ctx.sanitized_message = _step(
            "run_safety_gate_pre",
            lambda: run_safety_gate_pre(
                session, client, sid, ctx.user_message, ctx.user_message,
                recommendation_client=ctx.recommendation_client,
            ),
        )
        if pre.blocked:
            _log(f"safety pre blocked: {pre.response}")
            return 0

        early, ctx.triage_result = _step(
            "run_triage",
            lambda: run_triage(
                session, client, sid, ctx.user_message, ctx.sanitized_message, ctx.recommendation_client,
            ),
        )
        if early is not None:
            _log(f"triage early return: {early}")
            return 0

        post = _step(
            "run_safety_gate (full)",
            lambda: run_safety_gate(
                session, client, sid, ctx.user_message, ctx.sanitized_message,
                triage_result=ctx.triage_result,
                recommendation_client=ctx.recommendation_client,
                phase="full",
            ),
        )
        if post.blocked:
            _log(f"safety full blocked: {post.response}")
            return 0

        body, code = _step(
            "run_chat_post_pipeline",
            lambda: run_chat_post_pipeline(session, client, message, sid, monitor),
        )
        _log(f"DONE status={code} body={body}")
    return 0


def cmd_safety(message: str) -> int:
    from src.agents.safety_gate import run_safety_gate, run_safety_gate_pre
    from src.handlers.chat.chat_input_validator import validate_and_block_input

    session = _make_session()
    client = _make_client()
    sid = "diag-safety"

    with ExitStack() as stack:
        stack.enter_context(patch("src.services.database.get_database", return_value=None))
        stack.enter_context(patch("src.services.processing_status._flush_to_db"))

        sanitized, err = _step(
            "validate_and_block_input",
            lambda: validate_and_block_input(session, client, message, sid),
        )
        _log(f"  sanitized={sanitized!r} error={err is not None}")

        gate_pre = _step(
            "run_safety_gate (phase=pre)",
            lambda: run_safety_gate(
                session, client, sid, message, sanitized or message,
                triage_result=None, recommendation_client=MagicMock(), phase="pre",
            ),
        )
        _log(f"  blocked={gate_pre.blocked}")

        combined, san2 = _step(
            "run_safety_gate_pre",
            lambda: run_safety_gate_pre(
                session, client, sid, message, message, recommendation_client=MagicMock(),
            ),
        )
        _log(f"  blocked={combined.blocked} sanitized={san2!r}")
    return 0


def cmd_safety_parts(message: str) -> int:
    from src.handlers.chat.chat_diagnosis_handler import handle_diagnosis_if_detected
    from src.handlers.chat.chat_inappropriate_route import handle_inappropriate_message_if_detected

    session = _make_session()
    client = _make_client()
    sid = "diag-safety-parts"

    with ExitStack() as stack:
        stack.enter_context(patch("src.services.database.get_database", return_value=None))
        stack.enter_context(patch("src.services.processing_status._flush_to_db"))

        r1 = _step(
            "handle_diagnosis_if_detected",
            lambda: handle_diagnosis_if_detected(session, client, sid, message),
        )
        _log(f"  response={'yes' if r1 is not None else 'no'}")

        r2 = _step(
            "handle_inappropriate_message_if_detected",
            lambda: handle_inappropriate_message_if_detected(
                session, client, sid, message, message, MagicMock(),
            ),
        )
        _log(f"  response={'yes' if r2 is not None else 'no'}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "mode",
        choices=("full", "pipeline", "steps", "safety", "safety-parts"),
        help="診断モード",
    )
    parser.add_argument(
        "-m",
        "--message",
        default=DEFAULT_MESSAGE,
        help=f"テスト用ユーザーメッセージ (default: {DEFAULT_MESSAGE!r})",
    )
    args = parser.parse_args(argv)

    handlers = {
        "full": cmd_full,
        "pipeline": cmd_pipeline,
        "steps": cmd_steps,
        "safety": cmd_safety,
        "safety-parts": cmd_safety_parts,
    }
    try:
        return handlers[args.mode](args.message)
    except Exception:
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
