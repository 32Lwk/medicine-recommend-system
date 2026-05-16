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
    {"id": "medicine_qa", "label": "医薬品の質問に回答しています", "weight": 14},
    {"id": "safety", "label": "安全性を確認しています", "weight": 8},
    {"id": "usage_notes", "label": "使用上の注意を作成しています", "weight": 10},
    {"id": "translate", "label": "回答を整えています", "weight": 7},
    {"id": "finalize", "label": "回答を仕上げています", "weight": 5},
]

_STEP_BY_ID = {s["id"]: s for s in PROCESSING_STEPS}
_STEP_ORDER = {s["id"]: i for i, s in enumerate(PROCESSING_STEPS)}
_TOTAL_WEIGHT = sum(s["weight"] for s in PROCESSING_STEPS)
_TOTAL_STEPS = len(PROCESSING_STEPS)

_lock = threading.RLock()
_cache: Dict[str, Dict[str, Any]] = {}
_flow_context: Dict[str, str] = {}
_advice_preview: Dict[str, str] = {}
_last_step: Dict[str, str] = {}
_last_flush_at: Dict[str, float] = {}
_pending_flush: Dict[str, bool] = {}
_session_lang: Dict[str, str] = {}
_VALID_LANGS = frozenset({"ja", "en", "ko", "zh"})

# step_id -> detail_code -> 表示ラベル（サーバー既定。クライアント I18N とキーを揃える）
STEP_DETAILS: Dict[str, Dict[str, Dict[str, str]]] = {
    "emergency": {
        "crisis_language": {
            "ja": "クライシス対応を準備しています",
            "en": "Preparing crisis support response",
            "ko": "위기 대응을 준비하고 있습니다",
            "zh": "正在准备危机支援回复",
        },
        "medical_self": {
            "ja": "医療緊急の案内を準備しています",
            "en": "Preparing medical emergency guidance",
            "ko": "의료 응급 안내를 준비하고 있습니다",
            "zh": "正在准备医疗紧急指引",
        },
        "store_incident": {
            "ja": "店舗インシデント対応を準備しています",
            "en": "Preparing store incident response",
            "ko": "매장 인시던트 대응을 준비하고 있습니다",
            "zh": "正在准备店内事件应对",
        },
        "emergency_dispatch": {
            "ja": "緊急応答を準備しています",
            "en": "Preparing emergency response",
            "ko": "응급 응답을 준비하고 있습니다",
            "zh": "正在准备紧急回复",
        },
    },
    "medicine_select": {
        "explanation": {
            "ja": "推奨理由を作成しています",
            "en": "Generating recommendation reasons",
            "ko": "추천 이유를 작성하고 있습니다",
            "zh": "正在生成推荐理由",
        },
    },
    "attributes": {
        "nlu": {
            "ja": "症状と属性を整理しています",
            "en": "Analyzing symptoms and profile",
            "ko": "증상과 정보를 정리하고 있습니다",
            "zh": "正在整理症状与属性",
        },
    },
}


def _detail_label(step_id: str, detail_code: Optional[str], lang: Optional[str]) -> Optional[str]:
    if not detail_code:
        return None
    block = STEP_DETAILS.get(step_id, {}).get(detail_code)
    if not block:
        return None
    lng = lang if lang in _VALID_LANGS else "ja"
    return block.get(lng) or block.get("ja")


def set_processing_flow(session_id: Optional[str], flow_id: str) -> None:
    """マルチエージェントフロー文脈（挨拶 / physical / ask_qa 等）"""
    if not session_id or not flow_id:
        return
    with _lock:
        _flow_context[session_id] = flow_id
        cached = _cache.get(session_id)
        if cached and cached.get("active"):
            cached["flow_id"] = flow_id


def _payload_for_step(
    session_id: Optional[str],
    step_id: str,
    *,
    detail_code: Optional[str] = None,
    lang: Optional[str] = None,
) -> Dict[str, Any]:
    from src.services.processing_flows import (
        agent_detail_for_step,
        compute_progress,
        flow_description_ja,
        pick_label,
    )

    with _lock:
        flow_id = _flow_context.get(session_id or "", "default")
    step_num, total_steps, percent = compute_progress(flow_id, step_id)
    label = pick_label(flow_id, step_id, session_id, detail_code=detail_code)
    detail_label = _detail_label(step_id, detail_code, lang)
    agent_name, agent_role, flow_hint = agent_detail_for_step(step_id, detail_code, flow_id)
    agent_desc = ""
    if agent_name:
        from src.services.processing_flows import AGENT_META

        agent_desc = (AGENT_META.get(agent_name) or {}).get("desc_ja", "")

    payload: Dict[str, Any] = {
        "active": True,
        "flow_id": flow_id,
        "flow_description": flow_description_ja(flow_id),
        "step_id": step_id,
        "label": label,
        "step": step_num,
        "total": total_steps,
        "percent": percent,
        "updated_at": time.time(),
    }
    if detail_code:
        payload["detail_code"] = detail_code
    if detail_label:
        payload["detail_label"] = detail_label
    if agent_name:
        payload["agent_name"] = agent_name
        payload["agent_role"] = agent_role
        payload["agent_description"] = agent_desc
    if flow_hint:
        payload["flow_hint"] = flow_hint
    return payload


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
    for key in (
        "detail_code",
        "detail_label",
        "flow_id",
        "flow_description",
        "flow_hint",
        "agent_name",
        "agent_role",
        "agent_description",
    ):
        if payload.get(key) is not None:
            out[key] = payload[key]
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


def mark_processing_step(
    session_id: Optional[str],
    step_id: str,
    *,
    detail_code: Optional[str] = None,
) -> None:
    if not session_id or step_id not in _STEP_BY_ID:
        return
    with _lock:
        last = _last_step.get(session_id)
        last_detail = (_cache.get(session_id) or {}).get("detail_code")
        if last == step_id and last_detail == detail_code:
            return
        lang = _session_lang.get(session_id)
        payload = _payload_for_step(
            session_id, step_id, detail_code=detail_code, lang=lang
        )
        if lang:
            payload["language"] = lang
        _cache[session_id] = payload
        _last_step[session_id] = step_id
    _schedule_flush(session_id, payload)
    try:
        from src.services.sse_emit import emit_sse_event, is_session_stream_active

        if is_session_stream_active(session_id):
            sse_payload: Dict[str, Any] = {
                "step_id": payload.get("step_id"),
                "label": payload.get("label"),
                "step": payload.get("step"),
                "total": payload.get("total"),
                "percent": payload.get("percent"),
                "language": payload.get("language"),
            }
            if payload.get("detail_code"):
                sse_payload["detail_code"] = payload["detail_code"]
            if payload.get("detail_label"):
                sse_payload["detail_label"] = payload["detail_label"]
            for extra in (
                "flow_id",
                "flow_description",
                "flow_hint",
                "agent_name",
                "agent_role",
                "agent_description",
            ):
                if payload.get(extra):
                    sse_payload[extra] = payload[extra]
            emit_sse_event("status", sse_payload, session_id=session_id)
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
        _flow_context.pop(session_id, None)
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
