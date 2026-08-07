"""
初回の薬探索（推奨フロー）と追質問 Q&A の切り分け。

トリアージ（Physical / Ask）と推奨履歴の有無を主軸にし、
キーワードはトリアージが Ask のときの補助のみに使う。
"""
from __future__ import annotations

from typing import Any, Optional

from src.services.session_manager import get_session_from_db

_SPORTS_CONTEXT_KEYWORDS = (
    "競技",
    "陸上",
    "マラソン",
    "ドーピング",
    "大会",
    "レース",
    "試合",
    "アンチドーピング",
    "水泳",
    "泳ぐ",
    "プール",
    "競泳",
)
_DISCOVERY_KEYWORDS = (
    "教えて",
    "おすすめ",
    "お勧め",
    "オススメ",
    "風邪薬",
    "薬を",
    "どの薬",
    "何の薬",
    "使える",
    "飲める",
    "ありますか",
    "探して",
    "知りたい",
    "市販薬",
)
_INFORMATIONAL_ONLY_KEYWORDS = (
    "副作用",
    "飲み方",
    "用法",
    "用量",
    "併用",
    "飲み合わせ",
    "相互作用",
)


def session_has_recommended_medicines(session: Any, sid: Optional[str]) -> bool:
    """bot メッセージの diagnosis.recommended_medicines のみを見る（雑談・挨拶は無視）。"""

    def _scan(messages: list) -> bool:
        for msg in reversed(messages or []):
            if msg.get("type") != "bot":
                continue
            diag = msg.get("diagnosis") or {}
            if diag.get("recommended_medicines"):
                return True
        return False

    if sid:
        db_messages = (get_session_from_db(sid) or {}).get("messages") or []
        if _scan(db_messages):
            return True
    return _scan(session.get("messages") or [])


def session_has_medicine_qa_context(session: Any, sid: Optional[str]) -> bool:
    """推奨履歴または過去の医薬品相談 Q&A 応答があるか。"""
    if session_has_recommended_medicines(session, sid):
        return True
    for source in (session.get("messages") or [],):
        for msg in reversed(source):
            if msg.get("type") != "bot":
                continue
            diag = msg.get("diagnosis") or {}
            if diag.get("is_question") or diag.get("chat_response"):
                return True
    if sid:
        db_messages = (get_session_from_db(sid) or {}).get("messages") or []
        for msg in reversed(db_messages):
            if msg.get("type") != "bot":
                continue
            diag = msg.get("diagnosis") or {}
            if diag.get("is_question") or diag.get("chat_response"):
                return True
    return False


def session_is_medical_cold_start(session: Any, sid: Optional[str]) -> bool:
    """医療系コンテキスト（推奨・Q&A）がまだないセッション。"""
    return not session_has_medicine_qa_context(session, sid)


def has_medicine_discovery_intent(user_message: str) -> bool:
    """推奨・候補の探索意図（副作用・飲み方などの情報質問のみは除く）。"""
    msg = (user_message or "").strip()
    if not msg:
        return False
    strong_discovery = (
        "おすすめ",
        "お勧め",
        "オススメ",
        "ありますか",
        "どの薬",
        "何の薬",
        "市販薬",
        "風邪薬",
        "薬を",
        "使える",
        "飲める",
        "探して",
        "知りたい",
    )
    if any(k in msg for k in _INFORMATIONAL_ONLY_KEYWORDS):
        if not any(k in msg for k in strong_discovery):
            return False
    return any(k in msg for k in _DISCOVERY_KEYWORDS) or any(
        k in msg for k in strong_discovery
    )


def has_sports_medicine_context(user_message: str) -> bool:
    return any(k in (user_message or "") for k in _SPORTS_CONTEXT_KEYWORDS)


def cold_start_needs_recommendation_flow(user_message: str) -> bool:
    """初回セッションで推奨フローに回すべき入力か（症状・薬探索）。"""
    msg = (user_message or "").strip()
    if not msg:
        return False
    if has_medicine_discovery_intent(msg):
        return True
    symptom_hints = (
        "痛", "熱", "咳", "鼻水", "頭痛", "風邪", "のど", "喉", "発熱",
        "だる", "寒気", "くしゃみ", "鼻づま",
    )
    if any(k in msg for k in symptom_hints):
        return True
    return any(k in msg for k in ("薬", "医薬品", "市販", "OTC", "感冒"))


def apply_cold_start_triage_override(
    session: Any,
    triage_result: Optional[dict],
    user_message: str,
    *,
    sid: Optional[str] = None,
) -> dict:
    """
    初回セッションでトリアージが Ask でも、薬探索・症状なら Physical に矯正。
    オーケストレーターが推奨フローへ進めるようにする。
    """
    triage = dict(triage_result or {})
    if not session_is_medical_cold_start(session, sid):
        return triage
    if triage.get("category") != "Ask":
        return triage
    if not cold_start_needs_recommendation_flow(user_message):
        return triage
    triage["category"] = "Physical"
    triage["subcategory"] = "medicine_discovery"
    prev = (triage.get("reasoning") or "").strip()
    triage["reasoning"] = (
        f"{prev} [初回セッション: Ask→Physical へ矯正]"
        if prev
        else "初回セッションの薬探索・症状入力のため Physical に矯正"
    )
    session["last_triage_result"] = triage
    if sid:
        session["_last_triage_result"] = triage
    return triage


def try_rule_based_symptom_triage(
    session: Any,
    user_message: str,
    *,
    sid: Optional[str] = None,
    sanitized_message: Optional[str] = None,
) -> Optional[dict]:
    """
    初回・短文の明示症状 → LLM triage をスキップして Physical を返す。
    greeting 誤ルートと triage レイテンシを同時に抑える。
    """
    if not session_is_medical_cold_start(session, sid):
        return None
    msg = (sanitized_message or user_message or "").strip()
    if not msg or len(msg) > 80:
        return None
    try:
        from src.services.concierge_intent import classify_concierge_intent

        if classify_concierge_intent(msg) in ("greeting", "thanks", "chitchat"):
            return None
    except ImportError:
        pass
    try:
        from src.utils.input_helpers import has_explicit_symptom_signal
    except ImportError:
        return None
    if not has_explicit_symptom_signal(msg):
        return None
    triage = {
        "category": "Physical",
        "subcategory": "explicit_symptom_short",
        "confidence": 0.92,
        "reasoning": "rule_based short symptom (skip llm_triage)",
    }
    session["last_triage_result"] = triage
    if sid:
        session["_last_triage_result"] = triage
    return triage


def should_route_medicine_discovery_to_recommendation(
    session: Any,
    sid: Optional[str],
    user_message: str,
    *,
    triage_category: Optional[str] = None,
) -> bool:
    """
    推奨フローへ回すか。

    - 推奨履歴あり → False（追質問は Q&A）
    - トリアージ Physical → True（オーケストレーターと同じ判断）
    - トリアージ Ask かつ探索意図 → True
    - トリアージ Ask かつ競技文脈＋薬の探索 → True（キーワード補助）
    """
    if session_has_medicine_qa_context(session, sid):
        return False

    cat = (triage_category or "").strip()
    if cat == "Physical":
        return True

    if not has_medicine_discovery_intent(user_message):
        if cat == "Ask" and has_sports_medicine_context(user_message):
            return any(k in user_message for k in ("薬", "風邪", "市販"))
        return False

    if cat in ("", "Ask", "Other"):
        return True

    return False
