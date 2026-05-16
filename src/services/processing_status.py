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
    {"id": "symptom_analysis", "label": "症状の内容を読み取り、該当する市販薬の種類を判定しています", "weight": 12},
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
        "candidate_search": {
            "ja": "症状に合うお薬候補を探しています",
            "en": "Searching medicine candidates for your symptoms",
            "ko": "증상에 맞는 의약품 후보를 찾고 있습니다",
            "zh": "正在查找符合症状的药品候选",
        },
        "explanation": {
            "ja": "推奨理由を作成しています",
            "en": "Generating recommendation reasons",
            "ko": "추천 이유를 작성하고 있습니다",
            "zh": "正在生成推荐理由",
        },
        "rule_match": {
            "ja": "症状に合うお薬候補を照合しています",
            "en": "Matching medicine candidates to your symptoms",
            "ko": "증상에 맞는 의약품 후보를 대조하고 있습니다",
            "zh": "正在比对符合症状的药品候选",
        },
        "scoring": {
            "ja": "候補のお薬の適合度を評価しています",
            "en": "Scoring how well each medicine fits",
            "ko": "후보 의약품의 적합도를 평가하고 있습니다",
            "zh": "正在评估候选药品的匹配度",
        },
        "ranking": {
            "ja": "おすすめ順に並べ替えています",
            "en": "Sorting recommendations",
            "ko": "추천 순으로 정렬하고 있습니다",
            "zh": "正在按推荐顺序排列",
        },
        "filter_contra": {
            "ja": "飲んではいけない組み合わせを除外しています",
            "en": "Filtering unsafe combinations",
            "ko": "복용하면 안 되는 조합을 제외하고 있습니다",
            "zh": "正在排除不宜同服的组合",
        },
    },
    "attributes": {
        "profile_register": {
            "ja": "お話から年齢・性別などを読み取っています",
            "en": "Reading age and profile from your message",
            "ko": "대화에서 나이·성별 등을 읽고 있습니다",
            "zh": "正在从对话中读取年龄与性别等信息",
        },
        "nlu": {
            "ja": "症状とお客様情報を整理しています",
            "en": "Analyzing symptoms and profile",
            "ko": "증상과 정보를 정리하고 있습니다",
            "zh": "正在整理症状与属性",
        },
    },
    "medicine_qa": {
        "context_load": {
            "ja": "これまでの推奨お薬を確認しています",
            "en": "Reviewing previously recommended medicines",
            "ko": "이전에 추천한 의약품을 확인하고 있습니다",
            "zh": "正在确认此前推荐的药品",
        },
        "history_read": {
            "ja": "会話の流れを読み取っています",
            "en": "Reading the conversation context",
            "ko": "대화 흐름을 읽고 있습니다",
            "zh": "正在读取对话内容",
        },
        "question_parse": {
            "ja": "ご質問の要点を整理しています",
            "en": "Summarizing your question",
            "ko": "질문 요점을 정리하고 있습니다",
            "zh": "正在整理您的问题要点",
        },
        "interaction_check": {
            "ja": "飲み合わせの注意を確認しています",
            "en": "Checking drug interaction cautions",
            "ko": "병용 주의를 확인하고 있습니다",
            "zh": "正在确认药物相互作用注意事项",
        },
        "doping_check": {
            "ja": "競技・検査向けの注意を確認しています",
            "en": "Checking sports and testing cautions",
            "ko": "경기·검사 관련 주의를 확인하고 있습니다",
            "zh": "正在确认竞技与检测相关注意事项",
        },
        "side_effect_check": {
            "ja": "副作用の情報を確認しています",
            "en": "Reviewing side effect information",
            "ko": "부작용 정보를 확인하고 있습니다",
            "zh": "正在确认副作用信息",
        },
        "answer_draft": {
            "ja": "回答の下書きを作成しています",
            "en": "Drafting the answer",
            "ko": "답변 초안을 작성하고 있습니다",
            "zh": "正在起草回答",
        },
        "answer_compose": {
            "ja": "わかりやすい回答文に整えています",
            "en": "Composing an easy-to-read answer",
            "ko": "이해하기 쉬운 답변으로 정리하고 있습니다",
            "zh": "正在整理为易懂的回答",
        },
        "safety_review": {
            "ja": "安全面の注意を最終確認しています",
            "en": "Final safety review",
            "ko": "안전 주의를 최종 확인하고 있습니다",
            "zh": "正在进行安全注意事项的最终确认",
        },
        "format_response": {
            "ja": "回答を見やすい形にまとめています",
            "en": "Formatting the response for display",
            "ko": "답변을 보기 쉽게 정리하고 있습니다",
            "zh": "正在将回答整理为易读格式",
        },
    },
    "symptom_analysis": {
        "llm_classify": {
            "ja": "症状から市販薬の種類を判定しています",
            "en": "Classifying symptoms and OTC medicine type with AI",
            "ko": "AI로 증상과 의약품 종류를 분류하고 있습니다",
            "zh": "正在用 AI 分类症状与药品类型",
        },
        "symptom_extract": {
            "ja": "お話から症状キーワードを抽出しています",
            "en": "Extracting symptom keywords from your message",
            "ko": "대화에서 증상 키워드를 추출하고 있습니다",
            "zh": "正在从对话中提取症状关键词",
        },
    },
    "safety": {
        "contra_check": {
            "ja": "年齢・妊娠・併用薬の安全性を確認しています",
            "en": "Checking safety for age, pregnancy, and other medicines",
            "ko": "연령·임신·병용 약의 안전성을 확인하고 있습니다",
            "zh": "正在确认年龄、妊娠与合并用药的安全性",
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
    from src.services.processing_agent_display import slow_hint_for_phase, user_agent_display

    agent_display = user_agent_display(agent_name, step_id, detail_code, flow_id)
    if agent_display:
        payload["agent_display"] = agent_display
    slow_hint = slow_hint_for_phase(flow_id, step_id, detail_code)
    if slow_hint:
        payload["slow_hint"] = slow_hint
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
        "agent_display",
        "slow_hint",
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
                "agent_display",
                "slow_hint",
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
