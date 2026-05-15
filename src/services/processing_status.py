"""
チャット処理進捗（インメモリ即時更新 + デバウンス非同期 DB 書き込み）
"""
from __future__ import annotations

import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_DEBOUNCE_SEC = 0.4
_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="proc_status")

PROCESSING_STEPS: List[Dict[str, Any]] = [
    {"id": "validate", "label": "入力を確認しています", "weight": 5},
    {"id": "triage", "label": "症状の種類を分析しています", "weight": 8},
    {"id": "diagnosis", "label": "診断名を確認しています", "weight": 6},
    {"id": "emergency", "label": "緊急度を確認しています", "weight": 7},
    {"id": "dialect", "label": "言葉遣いを整えています", "weight": 5},
    {"id": "store", "label": "店舗案内か確認しています", "weight": 5},
    {"id": "counseling", "label": "お話を整理しています", "weight": 10},
    {"id": "attributes", "label": "お客様情報を確認しています", "weight": 7},
    {"id": "symptom_analysis", "label": "症状を詳しく分析しています", "weight": 12},
    {"id": "medicine_select", "label": "お薬を選定しています", "weight": 15},
    {"id": "safety", "label": "安全性を確認しています", "weight": 8},
    {"id": "usage_notes", "label": "使用上の注意を作成しています", "weight": 10},
    {"id": "translate", "label": "回答を整えています", "weight": 7},
    {"id": "finalize", "label": "回答を仕上げています", "weight": 5},
]

_STEP_BY_ID = {s["id"]: s for s in PROCESSING_STEPS}
_STEP_ORDER = {s["id"]: i for i, s in enumerate(PROCESSING_STEPS)}
_TOTAL_WEIGHT = sum(s["weight"] for s in PROCESSING_STEPS)
_TOTAL_STEPS = len(PROCESSING_STEPS)

_lock = threading.Lock()
_cache: Dict[str, Dict[str, Any]] = {}
_advice_preview: Dict[str, str] = {}
_last_step: Dict[str, str] = {}
_last_flush_at: Dict[str, float] = {}
_pending_flush: Dict[str, bool] = {}
_session_lang: Dict[str, str] = {}
_VALID_LANGS = frozenset({"ja", "en", "ko", "zh"})


def _payload_for_step(step_id: str, max_reached_index: int) -> Dict[str, Any]:
    step = _STEP_BY_ID.get(step_id, PROCESSING_STEPS[0])
    order = _STEP_ORDER.get(step_id, 0)
    if order > max_reached_index:
        max_reached_index = order
    reached_weight = sum(
        PROCESSING_STEPS[i]["weight"]
        for i in range(max_reached_index + 1)
    )
    percent = min(100, int(round(100 * reached_weight / _TOTAL_WEIGHT)))
    return {
        "active": True,
        "step_id": step_id,
        "label": step["label"],
        "step": max_reached_index + 1,
        "total": _TOTAL_STEPS,
        "percent": percent,
        "updated_at": time.time(),
    }


def _inactive_payload() -> Dict[str, Any]:
    return {
        "active": False,
        "step_id": None,
        "label": None,
        "step": 0,
        "total": _TOTAL_STEPS,
        "percent": 0,
        "language": None,
    }


def set_processing_language(session_id: Optional[str], language: Optional[str]) -> None:
    """処理中表示の言語（ユーザー入力言語）を設定。"""
    if not session_id or not language or language not in _VALID_LANGS:
        return
    with _lock:
        _session_lang[session_id] = language
        cached = _cache.get(session_id)
        if cached and cached.get("active"):
            cached["language"] = language


def _active_response(session_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    lang = payload.get("language") or _session_lang.get(session_id)
    out = {
        "active": True,
        "step_id": payload.get("step_id"),
        "label": payload.get("label"),
        "step": payload.get("step", 0),
        "total": payload.get("total", _TOTAL_STEPS),
        "percent": payload.get("percent", 0),
        "language": lang,
    }
    preview = payload.get("advice_preview")
    if preview is None:
        with _lock:
            preview = _advice_preview.get(session_id)
    if preview:
        out["advice_preview"] = preview
    return out


def append_advice_preview(session_id: Optional[str], chunk: str) -> None:
    """ストリーミング中のアドバイス本文プレビュー（admin/ポーリング用）"""
    if not session_id or not chunk:
        return
    with _lock:
        prev = _advice_preview.get(session_id, "")
        _advice_preview[session_id] = prev + chunk
        cached = _cache.get(session_id)
        if cached:
            cached["advice_preview"] = _advice_preview[session_id]


def _schedule_flush(session_id: str, payload: Dict[str, Any]) -> None:
    now = time.time()
    with _lock:
        last = _last_flush_at.get(session_id, 0.0)
        if now - last >= _DEBOUNCE_SEC:
            _last_flush_at[session_id] = now
            _pending_flush.pop(session_id, None)
            _executor.submit(_flush_to_db, session_id, dict(payload))
            return
        if _pending_flush.get(session_id):
            return
        _pending_flush[session_id] = True

    delay = _DEBOUNCE_SEC - (now - last)

    def _delayed() -> None:
        time.sleep(max(0.05, delay))
        with _lock:
            current = _cache.get(session_id)
            _pending_flush.pop(session_id, None)
            if not current or not current.get("active"):
                return
            _last_flush_at[session_id] = time.time()
        _flush_to_db(session_id, dict(current))

    _executor.submit(_delayed)


def _flush_to_db(session_id: str, payload: Dict[str, Any]) -> None:
    try:
        from src.services.database import get_database

        db = get_database()
        if db and (db.connection or db.connection_pool):
            db.update_processing_status_only(session_id, payload)
    except Exception as exc:
        logger.debug("processing_status flush skipped: %s", exc)


def mark_processing_step(session_id: Optional[str], step_id: str) -> None:
    if not session_id or step_id not in _STEP_BY_ID:
        return
    with _lock:
        if _last_step.get(session_id) == step_id:
            return
        prev_index = _STEP_ORDER.get(_last_step.get(session_id, ""), -1)
        new_index = _STEP_ORDER[step_id]
        max_index = max(prev_index, new_index)
        payload = _payload_for_step(step_id, max_index)
        lang = _session_lang.get(session_id)
        if lang:
            payload["language"] = lang
        _cache[session_id] = payload
        _last_step[session_id] = step_id
    _schedule_flush(session_id, payload)
    try:
        from src.services.sse_emit import emit_sse_event, is_session_stream_active

        if is_session_stream_active(session_id):
            emit_sse_event(
                "status",
                {
                    "step_id": payload.get("step_id"),
                    "label": payload.get("label"),
                    "step": payload.get("step"),
                    "total": payload.get("total"),
                    "percent": payload.get("percent"),
                    "language": payload.get("language"),
                },
                session_id=session_id,
            )
    except Exception as exc:
        logger.debug("processing_status sse emit skipped: %s", exc)


def clear_processing_status(session_id: Optional[str]) -> None:
    if not session_id:
        return
    with _lock:
        _cache.pop(session_id, None)
        _last_step.pop(session_id, None)
        _last_flush_at.pop(session_id, None)
        _pending_flush.pop(session_id, None)
        _session_lang.pop(session_id, None)
        _advice_preview.pop(session_id, None)
    try:
        from src.services.database import get_database

        db = get_database()
        if db and (db.connection or db.connection_pool):
            db.update_processing_status_only(session_id, None)
    except Exception as exc:
        logger.debug("processing_status clear skipped: %s", exc)


def get_processing_status(session_id: Optional[str]) -> Dict[str, Any]:
    if not session_id:
        return _inactive_payload()
    with _lock:
        cached = _cache.get(session_id)
    if cached and cached.get("active"):
        return _active_response(session_id, cached)
    try:
        from src.services.database import get_database

        db = get_database()
        if db and (db.connection or db.connection_pool):
            raw = db.get_processing_status_only(session_id)
            if raw and raw.get("active"):
                return _active_response(session_id, raw)
    except Exception as exc:
        logger.debug("processing_status read skipped: %s", exc)
    return _inactive_payload()
