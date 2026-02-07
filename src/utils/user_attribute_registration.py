"""
ユーザー属性登録モジュール（軽量・正規表現ベース）

全リクエストで実行するユーザー属性抽出・登録の責務を持つ。
正規表現で即時抽出し、オプションで非同期LLM抽出をスケジュールする。
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
    正規表現で即時抽出し、オプションで非同期LLM抽出をスケジュールする。

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
        if ua.get(key) != norm_val:
            ua[key] = norm_val
            updated = True
            logger.info(f"📝 ユーザー属性を登録（全フロー共通）: {key}={norm_val}")

    if updated:
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
        _schedule_async(sid, message, get_session_from_db_fn, save_to_db_fn)

    return updated, extracted


def _schedule_async(sid: str, message: str, get_session_fn, save_session_fn) -> None:
    """非同期LLM抽出をスケジュール（メイン処理をブロックしない）"""
    try:
        from src.services.async_attribute_extractor import schedule_async_attribute_extraction
        schedule_async_attribute_extraction(sid, message, get_session_fn, save_session_fn)
    except Exception as e:
        logger.debug(f"非同期属性抽出のスケジュールをスキップ: {e}")
