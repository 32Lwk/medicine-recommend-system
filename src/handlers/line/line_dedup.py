"""LINE Webhook / 配信の去重（プロセス内 + Gunicorn ワーカー間ファイル）。"""
from __future__ import annotations

import logging
import os
import sys
import tempfile
import time
from typing import Any

logger = logging.getLogger(__name__)

_TTL_SEC = 120.0
_seen: dict[str, float] = {}


def _lock_dir() -> str:
    return os.environ.get("LINE_LOCK_DIR", tempfile.gettempdir())


def _purge_expired(now: float) -> None:
    expired = [k for k, ts in _seen.items() if now - ts > _TTL_SEC]
    for key in expired:
        del _seen[key]


def _safe_key(key: str) -> str:
    return key.replace(":", "_").replace("/", "_")[:200]


def _marker_path(prefix: str, key: str) -> str:
    return os.path.join(_lock_dir(), f"line-{prefix}-{_safe_key(key)}.marker")


def _read_marker_ts(path: str) -> float | None:
    try:
        with open(path, encoding="utf-8") as fh:
            return float(fh.read().strip())
    except (OSError, ValueError):
        return None


def _try_create_marker(path: str, ts: float) -> bool:
    """O_EXCL でマーカーを作成。成功なら初回。"""
    try:
        os.makedirs(_lock_dir(), exist_ok=True)
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
        try:
            os.write(fd, str(ts).encode("utf-8"))
        finally:
            os.close(fd)
        return True
    except FileExistsError:
        return False


def _is_marker_active(path: str, now: float) -> bool:
    ts = _read_marker_ts(path)
    if ts is None:
        return False
    if now - ts >= _TTL_SEC:
        try:
            os.remove(path)
        except OSError:
            pass
        return False
    return True


def _claim_cross_process(prefix: str, key: str) -> bool:
    """
    ワーカー間で初回 claim なら True、重複なら False。
    Windows / ロック取得失敗時はプロセス内キャッシュのみにフォールバック。
    """
    if sys.platform == "win32":
        return True

    now = time.time()
    path = _marker_path(prefix, key)
    if _is_marker_active(path, now):
        return False
    if _try_create_marker(path, now):
        return True
    return not _is_marker_active(path, now)


def extract_webhook_dedup_key(event: dict[str, Any]) -> str | None:
    """Webhook イベントから安定した去重キーを生成する。"""
    event_id = event.get("webhookEventId")
    if event_id:
        return f"wev:{event_id}"

    message = event.get("message")
    if isinstance(message, dict) and message.get("id"):
        user_id = (event.get("source") or {}).get("userId") or ""
        return f"msg:{user_id}:{message['id']}"

    reply_token = event.get("replyToken")
    if reply_token:
        return f"rt:{reply_token}"
    return None


def mark_webhook_event_seen(dedup_key: str | None) -> bool:
    """
    Webhook イベントを記録する。

    Returns:
        True  if duplicate (already seen within TTL)
        False if newly recorded
    """
    if not dedup_key:
        return False

    now = time.time()
    _purge_expired(now)
    if dedup_key in _seen:
        return True

    if not _claim_cross_process("wh", dedup_key):
        _seen[dedup_key] = now
        logger.info("LINE duplicate webhook event skipped key=%s", dedup_key[:80])
        return True

    _seen[dedup_key] = now
    return False


def reset_dedup_cache_for_tests() -> None:
    """テスト用にプロセス内キャッシュをクリア。"""
    _seen.clear()
