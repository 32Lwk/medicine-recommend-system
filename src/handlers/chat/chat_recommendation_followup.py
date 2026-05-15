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


def _escalation_response(
    session: Any,
    sid: Optional[str],
    *,
    escalation_msg: str,
    medicine_type: str,
    algorithm: str,
    original_user_message: str,
) -> ResponseTuple:
    from src.services.html_formatter import format_escalation_display

    escalation_content = format_escalation_display(
        doctor_consultation=escalation_msg,
        medicine_type=medicine_type,
        algorithm=algorithm,
        user_message=original_user_message,
        include_feedback_buttons=True,
    )
    bot_response = {
        "type": "bot",
        "content": escalation_content,
        "diagnosis": {"doctor_consultation": escalation_msg, "escalation": True},
        "timestamp": datetime.now().isoformat(),
    }
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

                ans = _safe_format_html(chat_response_followup.get("answer", "回答を取得できませんでした"))
                med_det = _safe_format_html(chat_response_followup.get("medicine_details", ""))
                inter = _safe_format_html(chat_response_followup.get("interactions", ""))
                doping = _safe_format_html(chat_response_followup.get("doping_check", ""))
                side_eff = _safe_format_html(chat_response_followup.get("side_effects", ""))
                consult = _safe_format_html(chat_response_followup.get("consultation_advice", ""))
                full_html = f"""
<div class="chat-response">
<h4>💬 医薬品相談回答</h4>
<p><strong>回答:</strong><br>{ans}</p>
{f'<div style="margin-top: 15px; padding: 10px; background: #e3f2fd; border-radius: 5px;"><strong>💊 医薬品の詳細:</strong><br>{med_det}</div>' if med_det else ''}
{f'<div style="margin-top: 15px; padding: 10px; background: #fff3e0; border-radius: 5px;"><strong>⚠️ 相互作用の注意:</strong><br>{inter}</div>' if inter else ''}
{f'<div style="margin-top: 15px; padding: 10px; background: #ffebee; border-radius: 5px;"><strong>🏃 ドーピングチェック:</strong><br>{doping}</div>' if doping else ''}
{f'<div style="margin-top: 15px; padding: 10px; background: #fce4ec; border-radius: 5px;"><strong>⚕️ 副作用情報:</strong><br>{side_eff}</div>' if side_eff else ''}
{f'<div style="margin-top: 15px; padding: 10px; background: #f1f8e9; border-radius: 5px;"><strong>🩺 相談アドバイス:</strong><br>{consult}</div>' if consult else ''}
</div>"""
                full_html = full_html.replace("</div>", "</div>").replace("<div", "<div").replace("<div", "<div")
                mid = f"msg_{int(time.time() * 1000)}_{random.randint(1000, 9999)}"
                bot_content_followup = full_html + f"""
<div class="feedback-buttons" style="margin-top: 20px; padding: 15px; background: #f8f9fa; border-radius: 8px; border: 1px solid #dee2e6;">
<p style="margin: 0 0 10px 0; font-weight: bold; color: #495057;">この回答はいかがでしたか？</p>
<button class="feedback-btn-positive" onclick="handlePositiveFeedback('{mid}')" style="background: #28a745; color: white; border: none; padding: 8px 16px; margin-right: 10px; border-radius: 4px; cursor: pointer; font-size: 14px; min-width: 80px;">適切</button>
<button class="feedback-btn-negative" onclick="handleNegativeFeedback('{mid}')" style="background: #dc3545; color: white; border: none; padding: 8px 16px; border-radius: 4px; cursor: pointer; font-size: 14px; min-width: 80px;">不適切</button>
</div>"""
                bot_response_followup = {
                    "type": "bot",
                    "content": bot_content_followup,
                    "message_id": mid,
                    "diagnosis": {"chat_response": chat_response_followup, "is_question": True},
                    "timestamp": datetime.now().isoformat(),
                }
                session["messages"].append(bot_response_followup)
                _mark_session_modified(session)
                msg_count = len(session.get("messages", []))
                if sid:
                    sd2 = get_session_from_db(sid)
                    if sd2 and "messages" in sd2:
                        sd2["messages"].append(bot_response_followup)
                        sd2["last_activity"] = datetime.now()
                        save_session_to_db(sid, sd2)
                        msg_count = len(sd2["messages"])
                if "messages" in session:
                    del session["messages"]
                    _mark_session_modified(session)
                logger.info("✅ 医薬品質問フォローアップ応答完了（Other）: %s...", sanitized_message[:50])
                return FollowupResult(response=({"status": "ok", "message_count": msg_count}, 200))
            except Exception as e_followup:
                logger.warning("⚠️ 医薬品質問フォローアップでエラー: %s", e_followup)
                traceback.print_exc()

    return FollowupResult()
