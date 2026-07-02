"""
推奨フローへのフォローアップ（漢方希望/忌避・属性回答・医薬品質問）

店舗案内でない Other カテゴリ時に chat_handler から委譲。
"""
from __future__ import annotations

import html as html_mod
import logging
import os
import random
import time
import traceback
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional, Tuple

from openai import OpenAI

from src.core.medicine_logic import chat_with_medicine_context
from src.handlers.chat.chat_recommendation_flow import run_recommendation_flow
from src.services.session_manager import (
    get_next_user_number,
    get_session_from_db,
    get_session_from_memory,
    save_session_to_db,
)

logger = logging.getLogger(__name__)

ResponseTuple = Tuple[dict, int]

PREFERS_NOT_KAMPO_KEYWORDS = [
    "漢方はいや", "漢方いや", "漢方薬はいや", "漢方は嫌", "漢方嫌",
    "漢方以外", "西洋薬がいい", "西洋薬希望",
]
PREFERS_KAMPO_KEYWORDS = [
    "漢方がいい", "漢方の方が", "漢方希望", "漢方薬がいい", "漢方で",
]
ATTR_KEYWORDS = [
    "歳", "才", "男性", "女性", "女です", "男です", "妊娠", "授乳",
    "アレルギー", "服用", "飲んで", "持病", "既往", "続い", "日前から", "昨日から",
]
QUESTION_PATTERNS = (
    "か？", "ですか", "でしょうか", "教えて", "できますか", "使えますか",
    "利用できますか", "よいですか", "大丈夫ですか", "？",
)


@dataclass
class FollowupResult:
    """フォローアップ処理結果（早期 return またはメッセージ差し替え）"""

    response: Optional[ResponseTuple] = None
    sanitized_message: Optional[str] = None
    user_message: Optional[str] = None
    processed_message: Optional[str] = None


def _mark_session_modified(session: Any) -> None:
    if hasattr(session, "modified"):
        session.modified = True


def _find_last_recommendation(session: Any, sid: Optional[str]) -> Optional[dict]:
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


def _should_use_recommendation_summary_mode(session: Any, sanitized_message: str) -> bool:
    """直近推奨直後の曖昧な症状繰り返しは再スコアリングせず要約モードへ。"""
    text = (sanitized_message or "").strip()
    if not text or len(text) > 40:
        return False
    if any(k in text for k in ATTR_KEYWORDS):
        return False
    if any(p in text for p in QUESTION_PATTERNS):
        return False
    if any(k in text for k in PREFERS_KAMPO_KEYWORDS + PREFERS_NOT_KAMPO_KEYWORDS):
        return False
    return _find_last_recommendation(session, None) is not None


def _build_recommendation_summary_response(
    session: Any,
    sid: Optional[str],
    *,
    user_message: str,
) -> ResponseTuple:
    from src.services.sage_bot_response import build_bot_response
    from src.services.status_diagnosis_builder import build_notice_status

    diag = _find_last_recommendation(session, sid) or {}
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
    if sid:
        sd = get_session_from_db(sid) or {"session_id": sid, "messages": []}
        sd["messages"] = list(session.get("messages") or [])
        sd["last_activity"] = datetime.now()
        save_session_to_db(sid, sd)
    return {"status": "ok", "message_count": len(session.get("messages", []))}, 200


def _escalation_response(
    session: Any,
    sid: Optional[str],
    *,
    escalation_msg: str,
    medicine_type: str,
    algorithm: str,
    original_user_message: str,
) -> ResponseTuple:
    from legacy.html_formatter import format_escalation_display
    from src.services.sage_bot_response import build_bot_response
    from src.services.status_diagnosis_builder import build_escalation_status

    feedback_ctx = {
        "user_message": original_user_message,
        "ai_response": escalation_msg,
    }
    legacy_content = format_escalation_display(
        doctor_consultation=escalation_msg,
        medicine_type=medicine_type,
        algorithm=algorithm,
        user_message=original_user_message,
        include_feedback_buttons=True,
    )
    sage_diag = build_escalation_status(
        escalation_msg,
        medicine_type=medicine_type,
        feedback_context=feedback_ctx,
    ).to_client_dict()
    legacy_diagnosis = {"doctor_consultation": escalation_msg, "escalation": True}
    bot_response = build_bot_response(
        session,
        sid,
        sage_diagnosis=sage_diag,
        legacy_content=legacy_content,
        legacy_diagnosis=legacy_diagnosis,
    )
    session.setdefault("messages", []).append(bot_response)
    _mark_session_modified(session)
    if sid:
        session_data = get_session_from_db(sid)
        if session_data:
            session_data["messages"] = session.get("messages", [])
            session_data["last_activity"] = datetime.now()
            save_session_to_db(sid, session_data)
    return ({"status": "ok", "message_count": len(session.get("messages", []))}, 200)


def _safe_format_html(t: Any) -> str:
    if not t:
        return ""
    if isinstance(t, list):
        lines = []
        for item in t:
            if isinstance(item, dict):
                name = item.get("製品名") or item.get("name") or ""
                comp = item.get("主成分") or item.get("成分") or ""
                use = item.get("用途") or item.get("efficacy") or ""
                summary = " / ".join(s for s in [name, comp, use] if s)
                if summary:
                    lines.append(summary)
            else:
                lines.append(str(item))
        t = "\n".join(lines)
    elif isinstance(t, dict):
        t = "\n".join(f"{k}: {v}" for k, v in t.items())
    else:
        t = str(t)
    return html_mod.escape(t).replace("\n", "<br>")


def run_recommendation_followups(
    session: Any,
    client_info: Any,
    sid: Optional[str],
    monitor: Any,
    *,
    triage_result: Dict[str, Any],
    sanitized_message: str,
    user_message: str,
    processed_message: str,
    original_user_message: str,
    recommendation_client: OpenAI,
) -> FollowupResult:
    """
    Other かつ店舗案内でない場合の再推奨・医薬品質問フォローアップ。
    早期応答時は response を、漢方フォロー時はメッセージ差し替えを返す。
    """
    try:
        from src.handlers.chat.reco_dedup import try_reco_followup_short_circuit

        reco_early = try_reco_followup_short_circuit(
            session, sid, user_message, sanitized_message
        )
        if reco_early is not None:
            return FollowupResult(response=reco_early)
    except ImportError:
        pass

    if _should_use_recommendation_summary_mode(session, sanitized_message):
        logger.info("推奨要約モード: 直近推奨後の曖昧入力のため再スコアリングをスキップ")
        return FollowupResult(
            response=_build_recommendation_summary_response(
                session,
                sid,
                user_message=original_user_message or user_message,
            )
        )

    is_kampo_preference_refinement = False
    has_kampo_pref = any(
        kw in sanitized_message
        for kw in PREFERS_NOT_KAMPO_KEYWORDS + PREFERS_KAMPO_KEYWORDS
    )

    if has_kampo_pref and sid:
        session_data_for_kampo = get_session_from_db(sid)
        messages_from_db = (session_data_for_kampo or {}).get("messages", [])
        memory_data = get_session_from_memory(sid)
        messages_from_memory = (memory_data or {}).get("messages", [])
        messages_for_kampo = (
            messages_from_db
            if len(messages_from_db) >= len(messages_from_memory)
            else messages_from_memory
        )
        messages_for_kampo = messages_for_kampo or session.get("messages", [])
        logger.info(
            "🔍 漢方フォローアップ: messages_count=%s, db=%s, memory=%s",
            len(messages_for_kampo),
            len(messages_from_db),
            len(messages_from_memory),
        )
        found_recommendation = False
        prev_user_msg = None
        for msg in reversed(messages_for_kampo[-8:]):
            if msg.get("type") == "user":
                if found_recommendation and prev_user_msg is None:
                    prev_user_msg = msg.get("content", "").strip()
                    break
            elif msg.get("type") == "bot" and msg.get("diagnosis"):
                diag = msg.get("diagnosis", {})
                rec = diag.get("recommended_medicines")
                if not rec and isinstance(diag.get("recommendation"), dict):
                    rec = diag.get("recommendation", {}).get("recommended_medicines", [])
                if rec and len(rec) > 0:
                    found_recommendation = True

        if found_recommendation and prev_user_msg and len(prev_user_msg) >= 2:
            is_kampo_preference_refinement = True
            triage_result["category"] = "Physical"
            triage_result["subcategory"] = "headache"
            triage_result["reasoning"] = "漢方希望/忌避のフォローアップのため再推奨フローへ"
            new_msg = prev_user_msg + "。" + sanitized_message.strip()
            logger.info(
                "🔄 漢方希望/忌避のフォローアップを検出: 再推奨フローへ（症状: %s...）",
                prev_user_msg[:30],
            )
            return FollowupResult(
                sanitized_message=new_msg,
                user_message=new_msg,
                processed_message=new_msg,
            )

    is_attribute_answer_followup = False
    attr_prev_user_msg = None
    if not is_kampo_preference_refinement and sid:
        session_data_attr = get_session_from_db(sid)
        memory_data_attr = get_session_from_memory(sid)
        messages_from_db_attr = (session_data_attr or {}).get("messages", [])
        messages_from_memory_attr = (memory_data_attr or {}).get("messages", [])
        messages_attr = (
            messages_from_db_attr
            if len(messages_from_db_attr) >= len(messages_from_memory_attr)
            else messages_from_memory_attr
        )
        messages_attr = messages_attr or session.get("messages", [])
        last_recommendation_bot = None
        for msg in reversed(messages_attr[-12:]):
            if msg.get("type") != "bot":
                continue
            diag = msg.get("diagnosis") or {}
            rec = diag.get("recommended_medicines") or (
                isinstance(diag.get("recommendation"), dict)
                and (diag.get("recommendation") or {}).get("recommended_medicines", [])
            ) or []
            addq = diag.get("additional_questions") or (
                isinstance(diag.get("recommendation"), dict)
                and (diag.get("recommendation") or {}).get("additional_questions", [])
            ) or []
            if (rec and len(rec) > 0) or (addq and len(addq) > 0):
                last_recommendation_bot = msg
                break
        if last_recommendation_bot and last_recommendation_bot in messages_attr:
            idx = messages_attr.index(last_recommendation_bot)
            for i in range(idx - 1, -1, -1):
                if messages_attr[i].get("type") == "user":
                    attr_prev_user_msg = (messages_attr[i].get("content") or "").strip()
                    break
        looks_attr = sum(1 for kw in ATTR_KEYWORDS if kw in sanitized_message) >= 2
        if attr_prev_user_msg and len(attr_prev_user_msg) >= 2 and (
            session.get("from_attribute_modal") or looks_attr
        ):
            is_attribute_answer_followup = True
            logger.info(
                "🔄 追加質問への回答を検出: 再推奨フローへ（症状: %s...）",
                attr_prev_user_msg[:40],
            )

    if is_attribute_answer_followup and attr_prev_user_msg:
        try:
            session.setdefault("messages", [])
            user_msg = {
                "type": "user",
                "content": original_user_message,
                "timestamp": datetime.now().isoformat(),
                "uuid": str(uuid.uuid4()),
            }
            if not any(
                m.get("type") == "user" and m.get("content") == original_user_message
                for m in session.get("messages", [])
            ):
                session["messages"].append(user_msg)
                _mark_session_modified(session)
            if sid:
                session_data = get_session_from_db(sid)
                if session_data:
                    session_data.setdefault("messages", [])
                    if not any(
                        m.get("type") == "user" and m.get("content") == original_user_message
                        for m in session_data.get("messages", [])
                    ):
                        session_data["messages"].append(user_msg)
                        session_data["last_activity"] = datetime.now()
                        session_data["user_attributes"] = session.get(
                            "user_attributes", session_data.get("user_attributes", {})
                        )
                        save_session_to_db(sid, session_data)
                else:
                    save_session_to_db(
                        sid,
                        {
                            "session_id": sid,
                            "username": session.get(
                                "username", f"ユーザー{get_next_user_number()}"
                            ),
                            "messages": session.get("messages", []),
                            "session_active": True,
                            "last_activity": datetime.now(),
                            "client_ip": client_info.client_ip,
                            "user_agent": client_info.user_agent,
                            "user_attributes": session.get("user_attributes", {}),
                        },
                    )
            ua = session.get("user_attributes", {}) or {}
            if ua.get("pregnant") is True:
                logger.warning("⚠️ 追加質問フォローアップ: 妊娠中のため推奨せずエスカレーションのみ返却")
                return FollowupResult(
                    response=_escalation_response(
                        session,
                        sid,
                        escalation_msg="妊娠中は医師の診断を受けてください。市販薬の使用は医師にご相談ください。",
                        medicine_type="該当なし（妊娠中のため推奨中止）",
                        algorithm="禁忌チェック（妊娠）",
                        original_user_message=original_user_message,
                    )
                )
            if ua.get("breastfeeding") is True:
                logger.warning("⚠️ 追加質問フォローアップ: 授乳中のため推奨せずエスカレーションのみ返却")
                return FollowupResult(
                    response=_escalation_response(
                        session,
                        sid,
                        escalation_msg="授乳中は医師の診断を受けてください。市販薬の使用は医師にご相談ください。",
                        medicine_type="該当なし（授乳中のため推奨中止）",
                        algorithm="禁忌チェック（授乳）",
                        original_user_message=original_user_message,
                    )
                )
            triage_result["category"] = "Physical"
            triage_result["reasoning"] = "追加質問への回答のため再推奨フローへ"
            api_key = os.getenv("OPENAI_API_KEY")
            if api_key:
                client = OpenAI(api_key=api_key)
                resp = run_recommendation_flow(
                    session,
                    client_info,
                    sid,
                    monitor,
                    attr_prev_user_msg,
                    attr_prev_user_msg,
                    triage_result,
                    client,
                    user_message=attr_prev_user_msg,
                )
                return FollowupResult(response=resp)
        except Exception as e:
            logger.warning("⚠️ 追加質問フォローアップでエラー: %s", e)
            traceback.print_exc()

    if not is_kampo_preference_refinement and not (is_attribute_answer_followup and attr_prev_user_msg):
        session_data_other = get_session_from_db(sid) if sid else {}
        messages_other = (
            (session_data_other.get("messages", []) if session_data_other else session.get("messages", []))
            or []
        )
        latest_recommended_medicines_followup: list = []
        for msg in reversed(messages_other):
            if msg.get("type") == "bot" and msg.get("diagnosis"):
                diag = msg.get("diagnosis", {})
                if diag.get("recommended_medicines"):
                    latest_recommended_medicines_followup = diag.get("recommended_medicines", [])
                    break
        looks_like_question = any(p in (sanitized_message or "") for p in QUESTION_PATTERNS)
        if latest_recommended_medicines_followup and looks_like_question:
            try:
                session.setdefault("messages", [])
                user_msg_followup = {
                    "type": "user",
                    "content": original_user_message,
                    "timestamp": datetime.now().isoformat(),
                    "uuid": str(uuid.uuid4()),
                }
                session["messages"].append(user_msg_followup)
                _mark_session_modified(session)
                if sid:
                    sd = get_session_from_db(sid)
                    if sd:
                        sd.setdefault("messages", []).append(user_msg_followup)
                        sd["last_activity"] = datetime.now()
                        save_session_to_db(sid, sd)
                    else:
                        save_session_to_db(
                            sid,
                            {
                                "session_id": sid,
                                "username": session.get(
                                    "username", f"ユーザー{get_next_user_number()}"
                                ),
                                "messages": [user_msg_followup],
                                "session_active": True,
                                "last_activity": datetime.now(),
                                "client_ip": client_info.client_ip,
                                "user_agent": client_info.user_agent,
                                "user_attributes": session.get("user_attributes", {}),
                            },
                        )
                chat_response_followup = chat_with_medicine_context(
                    sanitized_message,
                    messages_other[-10:],
                    latest_recommended_medicines_followup,
                )
                try:
                    from src.utils.structured_logger import log_medicine_question_detail

                    log_medicine_question_detail(
                        session_id=sid,
                        user_input=sanitized_message,
                        response=chat_response_followup.get("answer", ""),
                    )
                except Exception as log_err:
                    logger.warning("医薬品質疑応答ログ記録エラー: %s", log_err)

                from src.handlers.chat.chat_medicine_qa_html import finalize_medicine_qa_response

                msg_count = finalize_medicine_qa_response(
                    session,
                    client_info,
                    sid,
                    sanitized_message,
                    chat_response_followup,
                )
                logger.info("✅ 医薬品質問フォローアップ応答完了（Other）: %s...", sanitized_message[:50])
                return FollowupResult(response=({"status": "ok", "message_count": msg_count}, 200))
            except Exception as e_followup:
                logger.warning("⚠️ 医薬品質問フォローアップでエラー: %s", e_followup)
                traceback.print_exc()

    return FollowupResult()
