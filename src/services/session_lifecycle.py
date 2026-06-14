"""セッション履歴の削除・トリム・クリアの監査ログ。"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

LIFECYCLE_LOG_MAX = 80

ACTION_LABELS_JA = {
    "message_trim": "メッセージ件数上限で古い履歴を切り捨て",
    "history_cleared": "会話履歴をクリア",
    "session_marked_inactive": "チャット終了（セッション非アクティブ化）",
    "memory_deleted": "メモリ上のセッションを削除（期限切れクリーンアップ）",
    "db_expired_deleted": "DBからセッションを削除（期限切れクリーンアップ）",
    "profile_fetched": "LINEプロフィールを取得",
    "profile_fetch_failed": "LINEプロフィール取得に失敗",
}


def append_lifecycle_event(
    target: Any,
    action: str,
    *,
    detail: Optional[str] = None,
    source: Optional[str] = None,
    messages_before: Optional[int] = None,
    messages_after: Optional[int] = None,
    extra: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """セッション dict または RequestSafeSession に lifecycle イベントを追記する。"""
    if target is None:
        return {}
    if not hasattr(target, "get"):
        return {}

    entry: dict[str, Any] = {
        "at": datetime.now().isoformat(),
        "action": action,
        "label": ACTION_LABELS_JA.get(action, action),
    }
    if detail:
        entry["detail"] = detail
    if source:
        entry["source"] = source
    if messages_before is not None:
        entry["messages_before"] = messages_before
    if messages_after is not None:
        entry["messages_after"] = messages_after
    if extra:
        entry.update(extra)

    log = list(target.get("lifecycle_log") or [])
    log.append(entry)
    if len(log) > LIFECYCLE_LOG_MAX:
        log = log[-LIFECYCLE_LOG_MAX:]
    target["lifecycle_log"] = log
    return entry


def merge_messages_into_archive(session_data: dict, messages: list) -> int:
    """message_archive にメッセージを重複排除でマージ。新規追加分の件数を返す。"""
    if not session_data or not messages:
        return 0
    from src.services.session_manager import _message_merge_key

    archive = list(session_data.get("message_archive") or [])
    seen = {_message_merge_key(m, i) for i, m in enumerate(archive)}
    added = 0
    base = len(archive)
    for j, msg in enumerate(messages):
        if not isinstance(msg, dict):
            continue
        key = _message_merge_key(msg, base + j)
        if key in seen:
            continue
        seen.add(key)
        archive.append(msg)
        added += 1
    if added:
        session_data["message_archive"] = archive
    return added


def admin_messages_for_session(info: dict) -> list:
    """管理画面表示用: アーカイブと現行 messages を統合した全履歴。"""
    if not isinstance(info, dict):
        return []
    combined: dict = {"message_archive": list(info.get("message_archive") or [])}
    live = info.get("messages") or []
    if live:
        merge_messages_into_archive(combined, live)
    archive = combined.get("message_archive")
    if isinstance(archive, list) and archive:
        return archive
    return list(live)


def ensure_line_session_archive(info: dict) -> bool:
    """LINE セッションの message_archive を messages から補完。変更があれば True。"""
    if not isinstance(info, dict):
        return False
    live = info.get("messages") or []
    if not live:
        return False
    before = len(info.get("message_archive") or [])
    added = merge_messages_into_archive(info, live)
    after = len(info.get("message_archive") or [])
    return added > 0 or (before == 0 and after > 0)
