"""LINE 長期記憶の非同期ジョブ（メインリクエストをブロックしない）。

ライフサイクル: docs/ops/LINE_LONG_TERM_MEMORY.md §4
"""
from __future__ import annotations

import logging
import threading
from typing import Any

logger = logging.getLogger(__name__)


def _run_daemon(name: str, fn) -> None:
    thread = threading.Thread(target=fn, daemon=True, name=name)
    thread.start()


def schedule_profile_persist(line_sid: str, user_attributes: dict[str, Any] | None) -> None:
    if not line_sid or not user_attributes:
        return

    def _run() -> None:
        try:
            from src.agents.profile_memory_agent import run_profile_memory_agent

            run_profile_memory_agent(line_sid, user_attributes)
        except Exception:
            logger.warning("profile persist job failed line_sid=%s", line_sid, exc_info=True)

    _run_daemon("line-profile-persist", _run)


def schedule_episode_summary(
    line_sid: str,
    messages: list,
    *,
    trigger: str = "unspecified",
    episode_id: str | None = None,
) -> None:
    if not line_sid or not messages:
        return

    def _run() -> None:
        try:
            from src.agents.episode_summary_agent import run_episode_summary_agent

            run_episode_summary_agent(
                line_sid,
                messages,
                trigger=trigger,
                episode_id=episode_id,
            )
        except Exception:
            logger.warning(
                "episode summary job failed line_sid=%s trigger=%s",
                line_sid,
                trigger,
                exc_info=True,
            )

    _run_daemon("line-episode-summary", _run)


def schedule_handoff_profile_writeback(
    handoff_sid: str,
    user_attributes: dict[str, Any] | None,
) -> None:
    """Web 引き継ぎセッションの属性更新を line:{userId} へ非同期反映。"""
    if not handoff_sid or not user_attributes:
        return

    def _run() -> None:
        try:
            from src.services.line_user_memory import resolve_memory_owner_sid
            from src.services.session_manager import get_session_from_db

            session_data = get_session_from_db(handoff_sid) or {}
            owner = resolve_memory_owner_sid(handoff_sid, session_data)
            if not owner:
                return
            schedule_profile_persist(owner, user_attributes)
        except Exception:
            logger.warning("handoff profile writeback failed sid=%s", handoff_sid, exc_info=True)

    _run_daemon("line-handoff-writeback", _run)


def maybe_schedule_line_episode_summary(
    session: Any,
    sid: str | None,
    bot_response: dict[str, Any] | None,
) -> None:
    """推奨完了時にエピソード要約を非同期生成。"""
    from src.services.line_user_memory import is_line_memory_session, resolve_memory_owner_sid

    if not bot_response or not is_line_memory_session(sid, session):
        return
    diagnosis = bot_response.get("diagnosis")
    if not isinstance(diagnosis, dict):
        return
    meds = diagnosis.get("recommended_medicines") or []
    if not meds and diagnosis.get("render") not in ("sage_reco", None):
        if diagnosis.get("status") != "success":
            return
    if not meds:
        return
    owner = resolve_memory_owner_sid(sid, session)
    if not owner:
        return
    messages = list(session.get("messages") or []) if session else []
    if not messages:
        return
    from src.services.line_user_memory import get_current_episode_id

    schedule_episode_summary(
        owner,
        messages,
        trigger="recommendation_complete",
        episode_id=get_current_episode_id(owner),
    )
