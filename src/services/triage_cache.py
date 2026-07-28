"""
プロセス内 LRU トリアージキャッシュ（canonical 正規化 + sha256 キー + skip 行列）

フェーズ1: 単一プロセス前提。複数ワーカーではヒットが分断される（docs 参照）。
"""
from __future__ import annotations

import hashlib
import logging
import os
import re
import time
from collections import OrderedDict
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger(__name__)

_DEFAULT_MAX = 256
_DEFAULT_TTL_SEC = 120
_DEFAULT_MIN_CHARS = 8
_DEFAULT_MIN_CONFIDENCE = 0.6

# トリアージキャッシュに混ぜる user_attributes 許可フィールド
_ATTR_KEYS = frozenset({
    "age",
    "gender",
    "pregnant",
    "breastfeeding",
    "symptoms",
    "symptom_duration_days",
})

_metrics = {"hit": 0, "miss": 0, "skip_lookup": 0, "skip_write": 0}


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except ValueError:
        return default


def max_entries() -> int:
    return max(32, _env_int("TRIAGE_CACHE_MAX_ENTRIES", _DEFAULT_MAX))


def ttl_sec() -> int:
    return max(60, _env_int("TRIAGE_CACHE_TTL_SEC", _DEFAULT_TTL_SEC))


def min_chars() -> int:
    return max(1, _env_int("TRIAGE_CACHE_MIN_CHARS", _DEFAULT_MIN_CHARS))


def min_confidence() -> float:
    return _env_float("TRIAGE_CACHE_MIN_CONFIDENCE", _DEFAULT_MIN_CONFIDENCE)


def cache_disabled() -> bool:
    return os.getenv("TRIAGE_CACHE_DISABLED", "").strip().lower() in ("1", "true", "yes", "on")


def normalize_triage_text(text: str) -> str:
    t = (text or "").strip().lower()
    t = re.sub(r"\s+", " ", t)
    return t


def attrs_digest(user_attributes: Optional[Dict[str, Any]]) -> str:
    if not user_attributes:
        return ""
    parts = []
    for key in sorted(_ATTR_KEYS):
        if key not in user_attributes:
            continue
        val = user_attributes.get(key)
        if val is None or val == "" or val is False:
            continue
        parts.append(f"{key}={val}")
    raw = "|".join(parts)
    if not raw:
        return ""
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def build_cache_key(
    text: str,
    user_attributes: Optional[Dict[str, Any]] = None,
    *,
    history_digest: str = "",
    memory_digest: str = "",
) -> str:
    """sha256(canonical_text + attrs_digest + history_digest + memory_digest) — 生本文はキーに含めない。"""
    norm = normalize_triage_text(text)
    digest = attrs_digest(user_attributes)
    hist = (history_digest or "").strip()
    mem = (memory_digest or "").strip()
    raw = f"{norm}|{digest}|{hist}|{mem}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def should_skip_cache_lookup(
    *,
    text: str,
    triage_result: Optional[Dict[str, Any]] = None,
    moderation_label: Optional[str] = None,
) -> Optional[str]:
    """
    キャッシュ lookup をスキップする理由。None なら lookup 可。
    """
    if cache_disabled():
        return "disabled_flag"
    norm = normalize_triage_text(text)
    if len(norm) < min_chars():
        return "min_chars"
    triage = triage_result or {}
    if triage.get("category") == "Emergency" or triage.get("requires_immediate_action"):
        return "emergency"
    mod = (moderation_label or triage.get("_moderation_label") or "").lower()
    if mod in ("crisis", "inappropriate"):
        return f"moderation_{mod}"
    return None


def should_skip_cache_write(
    *,
    text: str,
    result: Dict[str, Any],
    moderation_label: Optional[str] = None,
    attrs_changed: bool = False,
) -> Optional[str]:
    """キャッシュ書き込みをスキップする理由。"""
    skip = should_skip_cache_lookup(
        text=text,
        triage_result=result,
        moderation_label=moderation_label,
    )
    if skip:
        return skip
    if float(result.get("confidence") or 0) < min_confidence():
        return "low_confidence"
    if attrs_changed:
        return "attrs_changed"
    return None


def record_cache_event(event: str, *, reason: str = "") -> None:
    """hit / miss / skip_lookup / skip_write — PII なし。"""
    if event in _metrics:
        _metrics[event] += 1
    logger.debug("triage_cache event=%s reason=%s stats=%s", event, reason, dict(_metrics))


def get_cache_metrics() -> Dict[str, int]:
    return dict(_metrics)


class TriageCache:
    def __init__(self) -> None:
        self._store: OrderedDict[str, Tuple[float, Dict[str, Any]]] = OrderedDict()

    def get(self, key: str) -> Optional[Dict[str, Any]]:
        redis_key = f"triage:{key}"
        try:
            from src.services.redis_cache import cache_get_json

            hit = cache_get_json(redis_key)
            if isinstance(hit, dict):
                record_cache_event("hit", reason="redis")
                return hit
        except Exception:
            pass
        entry = self._store.get(key)
        if not entry:
            return None
        ts, result = entry
        if time.time() - ts > ttl_sec():
            self._store.pop(key, None)
            return None
        self._store.move_to_end(key)
        record_cache_event("hit", reason="local")
        return dict(result)

    def set(self, key: str, result: Dict[str, Any]) -> None:
        self._store[key] = (time.time(), dict(result))
        self._store.move_to_end(key)
        while len(self._store) > max_entries():
            self._store.popitem(last=False)
        try:
            from src.services.redis_cache import cache_set_json

            cache_set_json(f"triage:{key}", result, ttl_sec=ttl_sec())
        except Exception:
            pass


_cache = TriageCache()


def get_triage_cache() -> TriageCache:
    return _cache


def invalidate_cache_key(cache_key: str) -> None:
    """再トリアージ・緊急・確認質問後など、当該ターンのキャッシュを破棄。"""
    if not cache_key:
        return
    get_triage_cache()._store.pop(cache_key, None)
    record_cache_event("skip_lookup", reason="invalidated")


def invalidate_triage_for_turn(
    user_text: str,
    user_attributes: Optional[Dict[str, Any]] = None,
    *,
    history_digest: str = "",
    memory_digest: str = "",
) -> str:
    """現在ターン用キーを無効化し、キー文字列を返す（ログ用）。"""
    key = build_cache_key(
        user_text,
        user_attributes,
        history_digest=history_digest,
        memory_digest=memory_digest,
    )
    invalidate_cache_key(key)
    return key
