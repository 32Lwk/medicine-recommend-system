"""
推奨重複抑制 + 終了意図検出（p3-correction-sessionops 4d, UX_RECO_DEDUP）。

同一薬リストの再推奨を抑え、終了意図時は sage_reco を出さず締め応答へ。
"""
from __future__ import annotations

import logging
import re
from datetime import datetime
from typing import Any, Optional, Tuple

from src.services.session_manager import get_session_from_db, save_session_to_db

logger = logging.getLogger(__name__)

ResponseTuple = Tuple[dict, int]

_ATTR_KEYWORDS = (
    "歳", "才", "男性", "女性", "女です", "男です", "妊娠", "授乳",
    "アレルギー", "服用", "飲んで", "持病", "既往", "続い", "日前から", "昨日から",
)
_QUESTION_PATTERNS = (
    "か？", "ですか", "でしょうか", "教えて", "できますか", "使えますか",
    "利用できますか", "よいですか", "大丈夫ですか", "？",
)
_KAMPO_KEYWORDS = (
    "漢方はいや", "漢方いや", "漢方薬はいや", "漢方は嫌", "漢方嫌",
    "漢方以外", "西洋薬がいい", "西洋薬希望",
    "漢方がいい", "漢方の方が", "漢方希望", "漢方薬がいい", "漢方で",
)
_MEDICINE_QUESTION_BLOCKERS = (
    "飲んでも", "飲めます", "服用", "使えます", "使用して", "利用して", "摂取",
    "ドーピング", "禁止物質",
)
_SYMPTOM_MARKERS = ("痛", "熱", "咳", "鼻", "頭", "吐", "下痢", "痒", "めまい", "寒気", "倦怠")

_END_PATTERNS = (
    re.compile(r"^(ありがとう|どうもありがとう|感謝)"),
    re.compile(r"(これで(終わり|十分|結構)|もう大丈夫|もういい|結構です)"),
    re.compile(r"^(終わり|おわり|終了)"),
    re.compile(r"(お大事に|気をつけます|助かりました|受診します|病院に行きます)"),
    re.compile(r"^(大丈夫です|十分です)[。!！]?$"),
)


def find_last_recommendation(session: Any, sid: Optional[str]) -> Optional[dict]:
    messages = session.get("messages") or []
    if sid:
        sd = get_session_from_db(sid)
        if sd and len(sd.get("messages") or []) >= len(messages):
            messages = sd.get("messages") or messages
    for msg in reversed(messages):
        if msg.get("type") != "bot":
            continue
        diag = msg.get("diagnosis") or {}
        meds = diag.get("recommended_medicines") or []
        if meds:
            return diag
        if diag.get("render") == "sage_reco" and diag.get("symptoms"):
            return diag
    return None


def medicine_list_signature(medicines: list) -> tuple[str, ...]:
    names: list[str] = []
    for m in medicines or []:
        if not isinstance(m, dict):
            continue
        name = str(
            m.get("product_name") or m.get("name") or m.get("製品名") or ""
        ).strip().lower()
        if name:
            names.append(name)
    return tuple(sorted(names))


def message_adds_reco_context(user_text: str) -> bool:
    text = (user_text or "").strip()
    if not text:
        return False
    if any(k in text for k in _ATTR_KEYWORDS):
        return True
    if any(p in text for p in _QUESTION_PATTERNS):
        return True
    if any(k in text for k in _KAMPO_KEYWORDS):
        return True
    return False


def is_recommendation_end_intent(user_text: str) -> bool:
    text = (user_text or "").strip()
    if not text or len(text) > 120:
        return False
    if any(b in text for b in _MEDICINE_QUESTION_BLOCKERS):
        return False
    if any(p in text for p in _QUESTION_PATTERNS) and not re.search(
        r"^(ありがとう|どうも)", text
    ):
        return False
    if any(m in text for m in _SYMPTOM_MARKERS):
        if not re.search(r"(これで(終わり|十分)|もう大丈夫|おわり|終わり)", text):
            return False
    return any(p.search(text) for p in _END_PATTERNS)


def _mark_session_modified(session: Any) -> None:
    if hasattr(session, "modified"):
        session.modified = True


def _persist_messages(session: Any, sid: Optional[str]) -> None:
    if not sid:
        return
    sd = get_session_from_db(sid) or {"session_id": sid, "messages": []}
    sd["messages"] = list(session.get("messages") or [])
    sd["last_activity"] = datetime.now()
    save_session_to_db(sid, sd)


def build_recommendation_closing_response(
    session: Any,
    sid: Optional[str],
    *,
    user_message: str,
) -> ResponseTuple:
    from src.services.sage_bot_response import build_bot_response
    from src.services.status_diagnosis_builder import build_notice_status

    message = (
        "お役に立てて何よりです。お大事になさってください。"
        "ほかにご不明な点があれば、いつでもお尋ねください。"
    )
    sage_diag = build_notice_status(
        message,
        title="ご利用ありがとうございました",
        kind="recommendation_closing",
    ).to_client_dict()
    bot = build_bot_response(session, sid, sage_diagnosis=sage_diag, legacy_content=message)
    session.setdefault("messages", []).append(
        {"type": "user", "content": user_message, "timestamp": datetime.now().isoformat()}
    )
    session["messages"].append(bot)
    _mark_session_modified(session)
    _persist_messages(session, sid)
    return {"status": "ok", "message_count": len(session.get("messages", []))}, 200


def build_recommendation_summary_response(
    session: Any,
    sid: Optional[str],
    *,
    user_message: str,
) -> ResponseTuple:
    from src.services.sage_bot_response import build_bot_response
    from src.services.status_diagnosis_builder import build_notice_status

    diag = find_last_recommendation(session, sid) or {}
    meds = diag.get("recommended_medicines") or []
    names = [
        str(m.get("product_name") or m.get("name") or "").strip()
        for m in meds[:3]
        if isinstance(m, dict)
    ]
    names = [n for n in names if n]
    symptoms = diag.get("symptoms") or []
    symptom_text = "、".join(symptoms[:3]) if symptoms else "ご相談の症状"
    if names:
        med_text = "、".join(names)
        message = (
            f"先ほどのご相談（{symptom_text}）では、{med_text} などをご案内しました。"
            "用法用量や飲み合わせについて、ほかに知りたいことはありますか？"
        )
    else:
        message = (
            "先ほどの市販薬のご案内を踏まえ、ほかに知りたいことや気になる点はありますか？"
        )
    sage_diag = build_notice_status(
        message,
        title="推奨の確認",
        kind="recommendation_summary",
    ).to_client_dict()
    bot = build_bot_response(session, sid, sage_diagnosis=sage_diag, legacy_content=message)
    session.setdefault("messages", []).append(
        {"type": "user", "content": user_message, "timestamp": datetime.now().isoformat()}
    )
    session["messages"].append(bot)
    _mark_session_modified(session)
    _persist_messages(session, sid)
    return {"status": "ok", "message_count": len(session.get("messages", []))}, 200


def try_reco_flow_entry_short_circuit(
    session: Any,
    sid: Optional[str],
    user_message: str,
) -> Optional[ResponseTuple]:
    """推奨フロー入口: 終了意図または新コンテキストなしの繰り返しを短絡。"""
    from config.llm_flags import is_ux_reco_dedup_enabled

    if not is_ux_reco_dedup_enabled():
        return None
    if not find_last_recommendation(session, sid):
        return None
    text = (user_message or "").strip()
    if is_recommendation_end_intent(text):
        logger.info("UX_RECO_DEDUP: 終了意図を検出 — 推奨ループを停止")
        return build_recommendation_closing_response(session, sid, user_message=text)
    if not message_adds_reco_context(text):
        logger.info("UX_RECO_DEDUP: 新コンテキストなし — 要約応答へ")
        return build_recommendation_summary_response(session, sid, user_message=text)
    return None


def try_skip_duplicate_medicine_list(
    session: Any,
    sid: Optional[str],
    recommended_medicines: list,
    *,
    user_message: str,
) -> Optional[ResponseTuple]:
    """スコアリング後: 前ターンと同一薬リストなら再推奨をスキップ。"""
    from config.llm_flags import is_ux_reco_dedup_enabled

    if not is_ux_reco_dedup_enabled():
        return None
    last = find_last_recommendation(session, sid)
    if not last:
        return None
    prev_sig = medicine_list_signature(last.get("recommended_medicines") or [])
    new_sig = medicine_list_signature(recommended_medicines)
    if not prev_sig or prev_sig != new_sig:
        return None
    logger.info("UX_RECO_DEDUP: 同一薬リスト — 再推奨をスキップ")
    return build_recommendation_summary_response(
        session, sid, user_message=(user_message or "").strip()
    )


def try_reco_followup_short_circuit(
    session: Any,
    sid: Optional[str],
    user_message: str,
    sanitized_message: str,
) -> Optional[ResponseTuple]:
    """フォローアップ経路向けの入口短絡（run_recommendation_followups 用）。"""
    return try_reco_flow_entry_short_circuit(
        session, sid, user_message or sanitized_message
    )
