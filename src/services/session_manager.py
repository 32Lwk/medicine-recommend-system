"""
セッション管理モジュール

DB・メモリへのセッション保存・取得、グローバル状態の管理を行う。
"""
import time
import logging
from datetime import datetime

from config.settings import (
    SESSION_TIMEOUT,
    CHAT_END_TIMEOUT,
    CLEANUP_INTERVAL,
    MAX_CLEANUP_DELAY,
    MAX_SESSIONS,
)

logger = logging.getLogger(__name__)

# フォールバック用のメモリ変数
_all_sessions = {}
_user_counter = 1
_last_cleanup_time = 0

# グローバル状態（モジュール変数で管理、globals()は使用しない）
_ai_auto_reply = True
_admin_mode = False
_manual_reply_queue = []
_manual_reply_message_cache = None
_admin_sessions = {}  # 管理者用詳細診断キャッシュ {sid: {'detailed_diagnosis': ..., 'last_updated': ...}}

DEFAULT_MANUAL_REPLY_MESSAGE = (
    '申し訳ございません。現在、AI自動応答が一時停止されています。'
    '担当者が確認次第、回答いたします。'
)


def get_database():
    """遅延インポートで循環参照を回避"""
    from src.services.database import get_database as _get_db
    return _get_db()


# --- セッションDB操作 ---

def get_session_from_db(session_id):
    """セッションをDBから取得、失敗時はフォールバック"""
    db = get_database()
    if db and (db.connection or db.connection_pool):
        session_data = db.get_session(session_id)
        if session_data:
            return session_data
    return _all_sessions.get(session_id)


def get_session_from_memory(session_id):
    """メモリフォールバックからセッションを取得（DB失敗時の最新データ）"""
    return _all_sessions.get(session_id)


def save_session_to_db(session_id, data):
    """セッションをDBに保存、失敗時はメモリに保存"""
    db = get_database()
    if db and (db.connection or db.connection_pool):
        success = db.save_session(session_id, data)
        if success:
            return True
    _all_sessions[session_id] = data
    logger.warning(f"⚠️ DB save failed, using memory fallback for session {session_id}")
    return True


def get_all_sessions_from_db():
    """全セッションをDBから取得、失敗時はフォールバック"""
    db = get_database()
    if db and (db.connection or db.connection_pool):
        sessions = db.get_all_sessions()
        if sessions is not None:
            return {s['session_id']: s for s in sessions}
    return _all_sessions


# --- グローバル状態 ---

def get_ai_auto_reply():
    """AI自動応答設定をDBから取得"""
    db = get_database()
    if db and (db.connection or db.connection_pool):
        return db.get_global_state('AI_AUTO_REPLY', default_value=True)
    return _ai_auto_reply


def set_ai_auto_reply(value):
    """AI自動応答設定をDBに保存"""
    global _ai_auto_reply
    db = get_database()
    if db and (db.connection or db.connection_pool):
        db.set_global_state('AI_AUTO_REPLY', value)
    _ai_auto_reply = value


def get_admin_mode():
    """管理者モード設定をDBから取得"""
    db = get_database()
    if db and (db.connection or db.connection_pool):
        return db.get_global_state('ADMIN_MODE', default_value=False)
    return _admin_mode


def set_admin_mode(value):
    """管理者モード設定をDBに保存"""
    global _admin_mode
    db = get_database()
    if db and (db.connection or db.connection_pool):
        db.set_global_state('ADMIN_MODE', value)
    _admin_mode = value


def get_manual_reply_queue():
    """手動返信キューをDBから取得"""
    db = get_database()
    if db and (db.connection or db.connection_pool):
        return db.get_global_state('MANUAL_REPLY_QUEUE', default_value=[])
    return _manual_reply_queue


def set_manual_reply_queue(value):
    """手動返信キューをDBに保存"""
    global _manual_reply_queue
    db = get_database()
    if db and (db.connection or db.connection_pool):
        db.set_global_state('MANUAL_REPLY_QUEUE', value)
    _manual_reply_queue = value


def get_manual_reply_message():
    """手動返信時の自動メッセージを取得"""
    global _manual_reply_message_cache
    if _manual_reply_message_cache is not None:
        return _manual_reply_message_cache
    db = get_database()
    if db and (db.connection or db.connection_pool):
        db_value = db.get_global_state('MANUAL_REPLY_MESSAGE', default_value=None)
        if db_value is not None:
            _manual_reply_message_cache = db_value
            return db_value
    return DEFAULT_MANUAL_REPLY_MESSAGE


def set_manual_reply_message(value):
    """手動返信時の自動メッセージを保存"""
    global _manual_reply_message_cache
    db = get_database()
    if db and (db.connection or db.connection_pool):
        db.set_global_state('MANUAL_REPLY_MESSAGE', value)
    _manual_reply_message_cache = value


def get_admin_sessions():
    """管理者用詳細診断キャッシュを取得（mutate可能な辞書を返す）"""
    return _admin_sessions


# --- セッション管理ヘルパー ---

def get_next_user_number():
    """次のユーザー番号を取得（既存の番号を再利用）"""
    global _user_counter
    used_numbers = set()
    all_sessions = get_all_sessions_from_db()
    for info in all_sessions.values():
        username = info.get('username', '')
        if username.startswith('ユーザー'):
            try:
                number = int(username.replace('ユーザー', ''))
                used_numbers.add(number)
            except ValueError:
                pass
    next_number = 1
    while next_number in used_numbers:
        next_number += 1
    _user_counter = max(_user_counter, next_number + 1)
    return next_number


def find_existing_session(client_ip, user_agent):
    """既存のセッションを検索（同じ人からのアクセスのみ）"""
    current_time = time.time()
    all_sessions = get_all_sessions_from_db()
    for existing_sid, info in all_sessions.items():
        last_activity = info.get('last_activity')
        if isinstance(last_activity, datetime):
            last_activity = last_activity.timestamp()
        elif isinstance(last_activity, str):
            try:
                last_activity = datetime.fromisoformat(
                    last_activity.replace('Z', '+00:00')
                ).timestamp()
            except Exception:
                last_activity = 0
        if (info.get('client_ip') == client_ip and
                info.get('user_agent') == user_agent and
                current_time - (last_activity or 0) < 1800):  # 30分以内
            return existing_sid
    return None


def update_session_activity(sid):
    """セッションの最終アクティビティを更新"""
    if not sid:
        return
    session_data = get_session_from_db(sid)
    if session_data:
        session_data['last_activity'] = datetime.now()
        save_session_to_db(sid, session_data)


def remove_duplicate_user_messages_after_ai_response(sid):
    """AI応答後に重複するユーザーメッセージを削除"""
    if not sid:
        return False
    session_data = get_session_from_db(sid)
    if not session_data:
        return False
    messages = session_data.get('messages', [])
    original_count = len(messages)
    seen_contents = set()
    unique_messages = []
    for msg in messages:
        if msg.get('type') == 'user':
            content = msg.get('content', '')
            if content not in seen_contents:
                seen_contents.add(content)
                unique_messages.append(msg)
            else:
                logger.info(f"⏭️ 重複ユーザーメッセージを削除: {content[:50]}...")
        else:
            unique_messages.append(msg)
    if len(unique_messages) < original_count:
        session_data['messages'] = unique_messages
        save_session_to_db(sid, session_data)
        logger.info(f"✅ 重複削除完了: {original_count} → {len(unique_messages)} messages")
        return True
    return False


def cleanup_old_sessions(force=False, exclude_current_session=True, current_sid=None):
    """
    古いセッションをクリーンアップ（メモリ最適化）

    Args:
        force: Trueの場合、間隔を無視して強制実行
        exclude_current_session: Trueの場合、現在のセッションを削除から除外
        current_sid: 現在のセッションID（除外用、exclude_current_sessionがTrueの場合）。
            Webリクエストハンドラーから呼ぶ場合は、
            current_sid=session.get('_id') if has_request_context() else None を渡すこと。
    """
    global _last_cleanup_time
    current_time = time.time()

    if not force:
        if (current_time - _last_cleanup_time) < CLEANUP_INTERVAL:
            return
        if (current_time - _last_cleanup_time) < MAX_CLEANUP_DELAY:
            return

    db = get_database()
    exclude_session_ids = []
    if exclude_current_session and current_sid:
        exclude_session_ids.append(current_sid)

    if db and (db.connection or db.connection_pool) and hasattr(db, 'cleanup_expired_sessions'):
        try:
            deleted_count = db.cleanup_expired_sessions(
                SESSION_TIMEOUT,
                exclude_session_ids=exclude_session_ids if exclude_session_ids else None,
                chat_end_timeout_seconds=CHAT_END_TIMEOUT
            )
            if isinstance(deleted_count, int) and deleted_count > 0:
                logger.info(f"🧹 セッションクリーンアップ完了: {deleted_count}件削除")
            _last_cleanup_time = current_time
            return
        except AttributeError as e:
            logger.warning(f"⚠️ cleanup_expired_sessions メソッドが利用できません: {e}")
        except Exception as e:
            logger.error(f"❌ セッションクリーンアップ中にエラー: {e}")

    # フォールバック: メモリベースのクリーンアップ
    sessions_to_remove = []
    all_sessions = get_all_sessions_from_db()
    for sid, session_info in all_sessions.items():
        if sid == current_sid:
            continue
        last_activity = session_info.get('last_activity', 0)
        if isinstance(last_activity, datetime):
            last_activity = last_activity.timestamp()
        elif isinstance(last_activity, str):
            try:
                last_activity = datetime.fromisoformat(
                    last_activity.replace('Z', '+00:00')
                ).timestamp()
            except (ValueError, AttributeError):
                last_activity = 0
        if current_time - last_activity > SESSION_TIMEOUT:
            sessions_to_remove.append(sid)

    all_sessions = get_all_sessions_from_db()
    if len(all_sessions) > MAX_SESSIONS:
        other_sessions = {k: v for k, v in all_sessions.items() if k != current_sid}
        if other_sessions:
            sorted_sessions = sorted(
                other_sessions.items(),
                key=lambda x: x[1].get('last_activity', 0)
            )
            excess_count = len(all_sessions) - MAX_SESSIONS
            for i in range(min(excess_count, len(sorted_sessions))):
                sessions_to_remove.append(sorted_sessions[i][0])

    for sid in sessions_to_remove:
        if sid != current_sid:
            if db and (db.connection or db.connection_pool):
                db.delete_session(sid)
            elif sid in _all_sessions:
                del _all_sessions[sid]
            logger.info(f"🗑️ 古いセッションを削除: {sid}")

    if sessions_to_remove:
        remaining = len(get_all_sessions_from_db())
        logger.info(f"🧹 セッションクリーンアップ完了: {len(sessions_to_remove)}件削除, 残り: {remaining}件")

    _last_cleanup_time = current_time


def get_all_sessions_store():
    """フォールバック用のALL_SESSIONS辞書への参照を返す（後方互換）"""
    return _all_sessions


def clear_sessions_fallback():
    """フォールバック用メモリのセッションをクリア（管理者用）"""
    global _all_sessions
    _all_sessions.clear()
