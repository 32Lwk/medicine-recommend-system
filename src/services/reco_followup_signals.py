"""
推奨後フォローアップの構造シグナル（要約短絡・重複スキップの gate 共用）。

テスト個別対応ではなく、症状追加・訂正・指示語・旅行文脈など
「新しい文脈がある」入力を一般化して検出する。
"""
from __future__ import annotations

import re
from typing import Any, Optional

_SYMPTOM_MARKERS = (
    "痛", "熱", "咳", "鼻", "頭", "吐", "下痢", "痒", "めまい", "寒気", "倦怠",
    "だる", "風邪", "のど", "喉", "発熱", "便秘", "通じ", "下痢",
)
_WELLNESS_ALTERNATIVE_RE = re.compile(
    r"サプリ|supplement|食物繊維|ファイバー|fiber|"
    r"自然由来|マグネシウム|magnesium|"
    r"腸に優し|やさしい成分|健食|健康食品",
    re.IGNORECASE,
)
_TRAVEL_FOLLOWUP_RE = re.compile(
    r"気をつけ|注意(?:点|事)|他に|教えて|確認|書類|診断書|申告|規制|持参|"
    r"持ち込|空港|止められ|量|どれくらい|何個|何錠|必要",
    re.IGNORECASE,
)
_BOT_ECHO_SYMPTOM_ASK_RE = re.compile(
    r"どんな症状|具体的に.{0,12}教えて|症状.{0,8}(?:教えて|聞)",
    re.IGNORECASE,
)


def is_wellness_alternative_topic(text: str) -> bool:
    """OTC 候補比較ではなくサプリ・自然由来等の話題か。"""
    return bool(_WELLNESS_ALTERNATIVE_RE.search(text or ""))


def is_travel_thread_followup(
    text: str,
    *,
    conversation_history: list[dict[str, Any]] | None = None,
) -> bool:
    """旅行・持ち込みスレッドの続き（症状語なしの注意点質問等）。"""
    t = (text or "").strip()
    if not t or not conversation_history:
        return False
    try:
        from src.services.medicine_qa_routing import is_travel_import_context
    except ImportError:
        return False
    blob = " ".join(
        str(m.get("content") or m.get("message") or "")
        for m in conversation_history[-10:]
        if isinstance(m, dict)
    )
    if not is_travel_import_context(blob) and not re.search(
        r"ロキソニン|バファリン|カロナール|タイレノール|イブ|パブロン|持ち込|海外|旅行|空港",
        blob,
    ):
        return False
    if is_travel_import_context(t):
        return True
    return bool(_TRAVEL_FOLLOWUP_RE.search(t))


def is_bot_echo_symptom_interview(text: str) -> bool:
    """ユーザーが症状ヒアリングを返す bot 風発話（競技プロンプト誤爆抑止）。"""
    t = (text or "").strip()
    if not t:
        return False
    try:
        from src.services.medicine_discovery_routing import has_sports_medicine_context
    except ImportError:
        has_sports_medicine_context = lambda _m: False  # type: ignore[assignment]
    if has_sports_medicine_context(t):
        return False
    return bool(_BOT_ECHO_SYMPTOM_ASK_RE.search(t))


def _prior_symptom_blob(
    conversation_history: list[dict[str, Any]] | None,
) -> str:
    parts: list[str] = []
    for msg in (conversation_history or [])[-8:]:
        if not isinstance(msg, dict) or msg.get("type") != "bot":
            continue
        diag = msg.get("diagnosis") or {}
        for s in diag.get("symptoms") or []:
            parts.append(str(s))
    return " ".join(parts)


def _symptoms_materially_changed(
    text: str,
    *,
    conversation_history: list[dict[str, Any]] | None = None,
) -> bool:
    """推奨済み症状と比べて新しい症状シグナルがあるか。"""
    t = (text or "").strip()
    if not t:
        return False
    try:
        from src.utils.input_helpers import has_explicit_symptom_signal
    except ImportError:
        has_explicit_symptom_signal = lambda _x: False  # type: ignore[assignment]

    markers_in_text = [m for m in _SYMPTOM_MARKERS if m in t]
    if not markers_in_text and not has_explicit_symptom_signal(t):
        return False

    prior = _prior_symptom_blob(conversation_history)
    if not prior:
        return bool(markers_in_text) or has_explicit_symptom_signal(t)

    for m in _SYMPTOM_MARKERS:
        if m in t and m not in prior:
            return True
    return False


def message_warrants_reco_rescore(
    user_text: str,
    *,
    conversation_history: list[dict[str, Any]] | None = None,
    recommended_medicines: list[dict[str, Any]] | None = None,
) -> bool:
    """
    直近推奨後も再スコアリング・再推奨・Q&A へ進めるべき入力か。
    False のときのみ recommendation_summary / 同一リスト短絡を許可。
    """
    text = (user_text or "").strip()
    if not text:
        return False

    from src.handlers.chat.reco_dedup import message_adds_reco_context

    if message_adds_reco_context(text):
        return True

    try:
        from src.utils.input_helpers import (
            detect_correction_intent,
            has_explicit_symptom_signal,
        )
    except ImportError:
        detect_correction_intent = lambda _t: False  # type: ignore[assignment]
        has_explicit_symptom_signal = lambda _t: False  # type: ignore[assignment]

    if detect_correction_intent(text):
        return True

    if _symptoms_materially_changed(
        text,
        conversation_history=conversation_history,
    ):
        return True

    try:
        from src.services.medicine_discovery_routing import has_medicine_discovery_intent

        if has_medicine_discovery_intent(text):
            return True
    except ImportError:
        pass

    try:
        from src.services.medicine_qa_routing import (
            _is_anaphoric_reference,
            is_symptom_pivot_followup,
            is_symptom_recommendation_followup,
        )

        if _is_anaphoric_reference(text):
            return True
        if is_symptom_pivot_followup(
            text,
            conversation_history=conversation_history,
            recommended_medicines=recommended_medicines,
        ):
            return True
        if is_symptom_recommendation_followup(
            text,
            conversation_history=conversation_history,
            recommended_medicines=recommended_medicines,
        ):
            return True
    except ImportError:
        pass

    if is_wellness_alternative_topic(text):
        return True
    if is_travel_thread_followup(text, conversation_history=conversation_history):
        return True
    if is_bot_echo_symptom_interview(text):
        return True

    return False


def should_reroute_failed_medicine_type_to_qa(
    user_message: str,
    *,
    session: Any = None,
    sid: Optional[str] = None,
) -> bool:
    """Physical 推奨で種類判定失敗時、medicine_qa / フォローアップへ委譲すべきか。"""
    msg = (user_message or "").strip()
    if not msg:
        return False

    history = (session.get("messages") if session else None) or []
    recs: list[dict[str, Any]] | None = None
    try:
        from src.handlers.chat.reco_dedup import find_last_recommendation

        last = find_last_recommendation(session, sid) if session else None
        if last:
            recs = last.get("recommended_medicines")
    except ImportError:
        pass

    if message_warrants_reco_rescore(
        msg,
        conversation_history=history,
        recommended_medicines=recs,
    ):
        return True

    try:
        from src.services.medicine_discovery_routing import session_has_medicine_qa_context

        if session and session_has_medicine_qa_context(session, sid):
            if is_travel_thread_followup(msg, conversation_history=history):
                return True
    except ImportError:
        pass

    return False
