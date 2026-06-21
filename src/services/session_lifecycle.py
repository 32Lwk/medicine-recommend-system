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
    "line_memory_deleted": "長期記憶（プロファイル・要約・アーカイブ）を削除",
    "line_memory_backfilled": "message_archive から長期記憶をバックフィル",
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


def _message_text_value(msg: dict) -> str:
    if not isinstance(msg, dict):
        return ""
    for key in ("content", "message", "text", "user_message"):
        val = msg.get(key)
        if val is not None and str(val).strip():
            return str(val).strip()
    return ""


def _prefer_richer_message(existing: dict, incoming: dict) -> dict:
    """同一キーの重複時、本文が長い（または空でない）方を優先する。"""
    if not isinstance(existing, dict):
        return dict(incoming)
    if not isinstance(incoming, dict):
        return existing
    existing_text = _message_text_value(existing)
    incoming_text = _message_text_value(incoming)
    if len(incoming_text) > len(existing_text):
        merged = dict(existing)
        merged.update(incoming)
        merged["content"] = incoming_text
        return merged
    if not existing_text and incoming_text:
        merged = dict(existing)
        merged.update(incoming)
        merged["content"] = incoming_text
        return merged
    return existing


def _parse_message_timestamp(msg: dict) -> float | None:
    if not isinstance(msg, dict):
        return None
    raw = msg.get("timestamp")
    if raw is None or raw == "":
        return None
    if isinstance(raw, (int, float)):
        value = float(raw)
        if value >= 1e12:
            return value / 1000.0
        return value
    text = str(raw).strip()
    if not text:
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).timestamp()
    except ValueError:
        pass
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
        try:
            return datetime.strptime(text, fmt).timestamp()
        except ValueError:
            continue
    return None


def sort_messages_chronologically(messages: list) -> list:
    """管理画面表示用に時系列（古い→新しい）へ並べ替え。"""
    if not isinstance(messages, list) or len(messages) <= 1:
        return list(messages or [])

    items = [(i, m) for i, m in enumerate(messages) if isinstance(m, dict)]
    if len(items) <= 1:
        return [m for _, m in items]

    n = len(items)
    sort_times: list[float | None] = [_parse_message_timestamp(msg) for _, msg in items]
    filled = list(sort_times)

    for i in range(n):
        if filled[i] is not None:
            continue
        prev_i = next((j for j in range(i - 1, -1, -1) if filled[j] is not None), None)
        next_i = next((j for j in range(i + 1, n) if filled[j] is not None), None)
        if prev_i is not None and next_i is not None:
            prev_ts = filled[prev_i]
            next_ts = filled[next_i]
            if prev_ts is not None and next_ts is not None:
                if next_ts > prev_ts:
                    frac = (i - prev_i) / (next_i - prev_i)
                    filled[i] = prev_ts + (next_ts - prev_ts) * frac
                else:
                    filled[i] = prev_ts + 0.001 * (i - prev_i)
                continue
        if prev_i is not None and filled[prev_i] is not None:
            filled[i] = filled[prev_i] + 0.001 * (i - prev_i)
        elif next_i is not None and filled[next_i] is not None:
            filled[i] = filled[next_i] - 0.001 * (next_i - i)
        else:
            filled[i] = float(items[i][0])

    indexed_sorted = sorted(
        zip(filled, [orig for orig, _ in items], [msg for _, msg in items]),
        key=lambda row: (row[0], row[1]),
    )
    return [msg for _, _, msg in indexed_sorted]


def merge_messages_into_archive(session_data: dict, messages: list) -> int:
    """message_archive にメッセージを重複排除でマージ。新規追加分の件数を返す。"""
    if not session_data or not messages:
        return 0
    from src.services.session_manager import _message_merge_key

    archive = list(session_data.get("message_archive") or [])
    key_to_index: dict[str, int] = {}
    for i, existing in enumerate(archive):
        if isinstance(existing, dict):
            key_to_index[_message_merge_key(existing, i)] = i
    added = 0
    base = len(archive)
    for j, msg in enumerate(messages):
        if not isinstance(msg, dict):
            continue
        key = _message_merge_key(msg, base + j)
        if key in key_to_index:
            idx = key_to_index[key]
            upgraded = _prefer_richer_message(archive[idx], msg)
            if upgraded is not archive[idx]:
                archive[idx] = upgraded
            continue
        key_to_index[key] = len(archive)
        archive.append(msg)
        added += 1
    if added or archive != list(session_data.get("message_archive") or []):
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
        return sort_messages_chronologically(archive)
    return sort_messages_chronologically(list(live))


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
