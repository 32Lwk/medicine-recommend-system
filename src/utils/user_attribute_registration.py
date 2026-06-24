"""
ユーザー属性登録モジュール（軽量・正規表現 + 非同期 LLM）

全リクエストで実行するユーザー属性抽出・登録の責務を持つ。
年齢・性別・妊娠・授乳は正規表現で即時抽出し、
アレルギー・既往症・服用薬は非同期 LLM 抽出を主とする。
"""
import logging
from datetime import datetime
from typing import Dict, Optional, Tuple, Any

from src.utils.attribute_extraction_patterns import extract_regex_attributes

logger = logging.getLogger(__name__)


def _normalize_value(key: str, value: Any, existing: Any) -> Any:
    """既存値とマージする際の正規化"""
    if key in ('allergies', 'current_medications', 'medical_history'):
        if isinstance(value, list):
            return value
        if isinstance(value, str) and value.strip():
            return [x.strip() for x in value.replace('、', ',').split(',') if x.strip()]
    return value


def register_user_attributes_from_message(
    session: dict,
    sid: Optional[str],
    message: str,
    save_to_db_fn=None,
    get_session_from_db_fn=None,
    schedule_async_extraction: bool = True,
) -> Tuple[bool, dict]:
    """
    メッセージからユーザー属性を抽出し、セッションに登録・永続化する。
    スカラー属性は正規表現で即時反映し、リスト属性は非同期 LLM を主とする。

    Args:
        session: Flaskセッション
        sid: セッションID
        message: ユーザーメッセージ
        save_to_db_fn: save_session_to_db(sid, data) の呼び出し可能オブジェクト
        get_session_from_db_fn: get_session_from_db(sid) の呼び出し可能オブジェクト
        schedule_async_extraction: Trueの場合、非同期LLM抽出をスケジュール（デフォルトTrue）

    Returns:
        (更新有無, 抽出した属性辞書)
    """
    if not message or not message.strip():
        return False, {}

    extracted = extract_regex_attributes(message)
    from src.utils.allergen_attributes import extract_environmental_allergens_from_message

    env_extracted = extract_environmental_allergens_from_message(message)
    if env_extracted:
        extracted = {**(extracted or {}), **env_extracted}

    if 'user_attributes' not in session:
        session['user_attributes'] = {
            'age': None,
            'gender': None,
            'pregnant': None,
            'breastfeeding': None,
            'current_medications': [],
            'allergies': [],
            'medical_history': [],
            'symptom_duration_days': None,
            'other_info': None
        }

    ua = session['user_attributes']
    updated = False

    for key, value in (extracted or {}).items():
        norm_val = _normalize_value(key, value, ua.get(key))
        if key in ('allergies', 'current_medications', 'medical_history'):
            existing = list(ua.get(key) or [])
            incoming = norm_val if isinstance(norm_val, list) else [norm_val] if norm_val else []
            combined = existing[:]
            for item in incoming:
                text = str(item).strip()
                if text and text not in combined:
                    combined.append(text)
            norm_val = combined
        if ua.get(key) != norm_val:
            ua[key] = norm_val
            updated = True
            logger.info(f"📝 ユーザー属性を登録（全フロー共通）: {key}={norm_val}")

    if updated:
        from src.utils.allergen_attributes import normalize_environmental_allergens

        ua = normalize_environmental_allergens(ua)
        session['user_attributes'] = ua
        if hasattr(session, 'modified'):
            session.modified = True

        if sid and save_to_db_fn and get_session_from_db_fn:
            try:
                session_data = get_session_from_db_fn(sid)
                if session_data:
                    session_data['user_attributes'] = dict(ua)
                    session_data['last_activity'] = datetime.now()
                    save_to_db_fn(sid, session_data)
            except Exception as e:
                logger.warning(f"⚠️ ユーザー属性のDB保存でエラー: {e}")

    if schedule_async_extraction and sid and get_session_from_db_fn and save_to_db_fn and message.strip():
        try:
            from src.services.input_routing import is_greeting_only_message

            if is_greeting_only_message(message.strip()):
                logger.debug("挨拶のみのため非同期属性抽出をスキップ")
            else:
                _schedule_async(sid, message, get_session_from_db_fn, save_to_db_fn)
        except Exception:
            _schedule_async(sid, message, get_session_from_db_fn, save_to_db_fn)

    session["_latest_attr_registration"] = {
        "updated": updated,
        "extracted": dict(extracted or {}),
        "message": (message or "")[:500],
    }

    return updated, extracted


def try_early_attribute_registration_ui(
    session: dict,
    sid: Optional[str],
    user_message: str,
    *,
    save_to_db_fn=None,
    get_session_from_db_fn=None,
    client_info: Any = None,
) -> bool:
    """
    トリアージ前 — ユーザーメッセージ直後に属性通知を挿入し DB へ即時反映する。
    """
    reg = session.get("_latest_attr_registration") or {}
    if not reg.get("extracted"):
        return False
    if session.get("_user_attr_notice_appended"):
        return False

    from src.services.session_manager import append_user_message, should_skip_append_user_message

    text = (user_message or "").strip()
    if text and not should_skip_append_user_message(session, text):
        append_user_message(session, text)

    if not append_user_attribute_registration_notice(session, sid):
        return False

    session["_user_attr_notice_appended"] = True
    if hasattr(session, "modified"):
        session.modified = True

    if sid and save_to_db_fn and get_session_from_db_fn:
        try:
            session_data = get_session_from_db_fn(sid)
            if session_data:
                session_data["messages"] = list(session.get("messages") or [])
                session_data["user_attributes"] = dict(session.get("user_attributes") or {})
                session_data["last_activity"] = datetime.now()
                save_to_db_fn(sid, session_data)
            elif client_info is not None:
                save_to_db_fn(
                    sid,
                    {
                        "session_id": sid,
                        "username": session.get("username", "Unknown"),
                        "messages": list(session.get("messages") or []),
                        "session_active": True,
                        "last_activity": datetime.now(),
                        "client_ip": getattr(client_info, "client_ip", None),
                        "user_agent": getattr(client_info, "user_agent", None),
                        "user_attributes": dict(session.get("user_attributes") or {}),
                    },
                )
        except Exception as e:
            logger.warning("⚠️ 初期属性通知のDB保存でエラー: %s", e)

    logger.info("📢 ユーザー属性登録通知（初期段階）")
    return True


def _schedule_async(sid: str, message: str, get_session_fn, save_session_fn) -> None:
    """非同期LLM抽出をスケジュール（メイン処理をブロックしない）"""
    try:
        from src.services.async_attribute_extractor import schedule_async_attribute_extraction
        schedule_async_attribute_extraction(sid, message, get_session_fn, save_session_fn)
    except Exception as e:
        logger.debug(f"非同期属性抽出のスケジュールをスキップ: {e}")


def build_registration_notice_items(
    user_attributes: dict,
    extracted: dict,
    *,
    was_updated: bool,
) -> list[str]:
    """チャット UI 向けのユーザー情報登録通知行を組み立てる。"""
    ua = user_attributes or {}
    items: list[str] = []
    for key, value in (extracted or {}).items():
        if key == "allergies":
            labels = value if isinstance(value, list) else [value]
            current = ua.get("allergies") or []
            display = ", ".join(str(x) for x in current if str(x).strip())
            if not display:
                display = ", ".join(str(x) for x in labels if str(x).strip())
            if display:
                suffix = "" if was_updated else "（既に登録済み）"
                items.append(f"アレルギー: {display}{suffix}")
        elif key == "medical_history":
            from src.utils.allergen_attributes import filter_display_medical_history

            current = filter_display_medical_history(ua.get("medical_history") or [])
            if current:
                suffix = "" if was_updated else "（既に登録済み）"
                items.append(f"既往症: {', '.join(current)}{suffix}")
        elif key == "current_medications":
            current = ua.get("current_medications") or []
            if current:
                suffix = "" if was_updated else "（既に登録済み）"
                items.append(f"服用中の薬: {', '.join(str(x) for x in current)}{suffix}")
        elif key == "gender" and ua.get("gender"):
            suffix = "" if was_updated else "（既に登録済み）"
            items.append(f"性別: {ua.get('gender')}{suffix}")
        elif key == "age" and ua.get("age") is not None:
            suffix = "" if was_updated else "（既に登録済み）"
            items.append(f"年齢: {ua.get('age')}歳{suffix}")
        elif key == "pregnant" and ua.get("pregnant") is not None:
            label = "妊娠中" if ua.get("pregnant") else "妊娠していない"
            suffix = "" if was_updated else "（既に登録済み）"
            items.append(f"妊娠状態: {label}{suffix}")
        elif key == "breastfeeding" and ua.get("breastfeeding") is not None:
            label = "授乳中" if ua.get("breastfeeding") else "授乳していない"
            suffix = "" if was_updated else "（既に登録済み）"
            items.append(f"授乳状態: {label}{suffix}")
    return items


def append_user_attribute_registration_notice(
    session: dict,
    sid: Optional[str],
) -> bool:
    """
    直前の register_user_attributes_from_message 結果に基づき、
    ユーザーメッセージ直後に Sage ユーザー情報カードを挿入する。
    """
    reg = session.get("_latest_attr_registration") or {}
    extracted = reg.get("extracted") or {}
    if not extracted:
        return False

    ua = session.get("user_attributes") or {}
    items = build_registration_notice_items(
        ua,
        extracted,
        was_updated=bool(reg.get("updated")),
    )
    if not items:
        return False

    import html

    from src.services.sage_bot_response import build_bot_response
    from src.services.status_diagnosis_builder import build_user_info_registration_status

    info_message = "💡 以下の情報を登録しました：\n" + "\n".join(f"・{item}" for item in items)
    escaped = html.escape(info_message).replace("\n", "<br>")
    legacy_content = (
        f'<div class="chat-response user-info-notification">'
        f'<p>{escaped}</p>'
        f'<button class="edit-info-btn" onclick="editUserInfo()">情報を修正</button></div>'
    )
    sage_diag = build_user_info_registration_status(items).to_client_dict()
    info_bot = build_bot_response(
        session,
        sid or session.get("_id"),
        sage_diagnosis=sage_diag,
        legacy_content=legacy_content,
        user_info_notification=True,
    )

    messages = session.setdefault("messages", [])
    user_msg_index = -1
    for i in range(len(messages) - 1, -1, -1):
        if messages[i].get("type") == "user":
            user_msg_index = i
            break

    if user_msg_index >= 0:
        messages.insert(user_msg_index + 1, info_bot)
    else:
        messages.append(info_bot)

    if hasattr(session, "modified"):
        session.modified = True

    logger.info("📢 ユーザー属性登録通知を追加: %s", items)
    return True
