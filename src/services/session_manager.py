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
    EMPTY_SESSION_TIMEOUT,
    SESSION_REUSE_WINDOW,
)

logger = logging.getLogger(__name__)

# フォールバック用のメモリ変数
_all_sessions = {}
_user_counter = 1
_last_cleanup_time = 0
_db_persist_enabled = None  # None=未判定, True/False=キャッシュ
_memory_fallback_logged = False
_last_db_persist_at: dict[str, float] = {}
_ACTIVITY_PERSIST_INTERVAL_SEC = 30

# new_session で削除した sid（クライアントの restore が履歴を復活させないようにする）
_recently_deleted_sids: dict[str, float] = {}
_DELETED_SID_TTL_SEC = 3600

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


def _db_usable(db) -> bool:
    """接続プールの存在だけでなく、利用可能かを判定する（壊れたプールでの再接続待ちを防ぐ）。"""
    if not db:
        return False
    if getattr(db, "startup_skip_reason", None) in ("connect_failed", "no_url", "no_driver"):
        return False
    return bool(db.is_available())


# --- セッションDB操作 ---

def get_session_from_db(session_id):
    """セッションをDBから取得、失敗時はフォールバック"""
    mem = _all_sessions.get(session_id)
    try:
        from src.handlers.line.line_session import is_line_session_id
    except ImportError:
        is_line_session_id = lambda _sid: False  # type: ignore[misc, assignment]

    # LINE 応答経路: 読込はメモリのみ（DB 不良時の getconn/再接続で数十秒ブロックしない）
    if session_id and is_line_session_id(session_id):
        return mem

    global _db_persist_enabled
    if _db_persist_enabled is False:
        return mem

    db = get_database()
    if _db_usable(db):
        session_data = db.get_session(session_id)
        if session_data:
            touch_session_in_memory(session_id, session_data)
            return session_data
    return mem


def get_session_from_memory(session_id):
    """メモリフォールバックからセッションを取得（DB失敗時の最新データ）"""
    return _all_sessions.get(session_id)


def is_db_persist_enabled() -> bool:
    """PostgreSQL へのセッション永続化が有効か（起動時接続プールの有無）。"""
    global _db_persist_enabled
    if _db_persist_enabled is not None:
        return _db_persist_enabled
    db = get_database()
    _db_persist_enabled = bool(db and db.connection_pool)
    return _db_persist_enabled


def touch_session_in_memory(session_id, data):
    """メモリ上のセッション辞書を更新（DB 未使用時・間引き時）。"""
    _all_sessions[session_id] = data


def _log_memory_fallback_once(*, db_save_failed: bool = False):
    """DB 未使用・保存失敗時の案内を初回のみ出力する。"""
    global _memory_fallback_logged
    if _memory_fallback_logged:
        return
    _memory_fallback_logged = True
    db = get_database()
    reason = getattr(db, 'startup_skip_reason', None) if db else 'no_url'
    if db_save_failed:
        logger.warning(
            'DB へのセッション保存に失敗したためメモリに保持します（以降この警告は抑制）。'
            ' DATABASE_URL・ネットワークを確認してください。'
        )
        return
    if reason == 'no_url':
        logger.info(
            'セッションはメモリに保存します（DATABASE_URL 未設定）。'
            ' 永続化する場合は .env に DATABASE_URL を設定してください。'
        )
    elif reason == 'no_driver':
        logger.info(
            'セッションはメモリに保存します（psycopg2 未インストール）。'
            ' `pip install psycopg2-binary` で DB 永続化を有効化できます。'
        )
    else:
        logger.info(
            'セッションはメモリに保存します（DB 接続不可）。'
            ' DATABASE_URL・SSL 設定を確認してください。'
        )


def save_session_to_db(session_id, data):
    """セッションをDBに保存、失敗時はメモリに保存"""
    global _db_persist_enabled
    db = get_database()
    if db and db.is_available():
        success = db.save_session(session_id, data)
        if success:
            _db_persist_enabled = True
            touch_session_in_memory(session_id, data)
            return True
        _db_persist_enabled = False
        touch_session_in_memory(session_id, data)
        _log_memory_fallback_once(db_save_failed=True)
        return True
    touch_session_in_memory(session_id, data)
    _log_memory_fallback_once()
    return True


def maybe_persist_session_activity(session_id, data, min_interval_sec=None):
    """
    last_activity 更新など軽量な同期用。
    DB 未使用時はメモリのみ。DB 利用時は min_interval_sec ごとに永続化する。
    """
    interval = (
        _ACTIVITY_PERSIST_INTERVAL_SEC
        if min_interval_sec is None
        else min_interval_sec
    )
    touch_session_in_memory(session_id, data)
    if not is_db_persist_enabled():
        return
    now = time.time()
    last = _last_db_persist_at.get(session_id, 0)
    if now - last < interval:
        return
    save_session_to_db(session_id, data)
    _last_db_persist_at[session_id] = now


def persist_session_attributes_only(sid, session_data: dict) -> None:
    """
    属性-only 更新の永続化。
    LINE セッションは throttle、Web は即時 save。
    """
    if not sid:
        return
    try:
        from src.handlers.line.line_session import is_line_session_id
    except ImportError:
        is_line_session_id = lambda _: False  # type: ignore[misc, assignment]
    if is_line_session_id(sid):
        maybe_persist_session_activity(sid, session_data)
    else:
        save_session_to_db(sid, session_data)


def get_all_sessions_from_db():
    """全セッションをDBから取得、失敗時はフォールバック"""
    db = get_database()
    if _db_usable(db):
        sessions = db.get_all_sessions()
        if sessions is not None:
            return {s['session_id']: s for s in sessions}
    return _all_sessions


# --- グローバル状態 ---

def get_ai_auto_reply_in_memory() -> bool:
    """DB を参照せずモジュール内キャッシュの AI 自動応答設定を返す（LINE ホットパス用）。"""
    return _ai_auto_reply


def get_ai_auto_reply():
    """AI自動応答設定をDBから取得（不可時はメモリキャッシュ）。"""
    global _ai_auto_reply
    if not is_db_persist_enabled():
        return _ai_auto_reply
    db = get_database()
    if not _db_usable(db):
        return _ai_auto_reply
    try:
        value = db.get_global_state('AI_AUTO_REPLY', default_value=True)
        _ai_auto_reply = value
        return value
    except Exception as exc:
        logger.warning("get_ai_auto_reply: DB read failed (%s); using in-memory value", exc)
        return _ai_auto_reply


def set_ai_auto_reply(value):
    """AI自動応答設定をDBに保存"""
    global _ai_auto_reply
    db = get_database()
    if _db_usable(db):
        db.set_global_state('AI_AUTO_REPLY', value)
    _ai_auto_reply = value


def get_admin_mode():
    """管理者モード設定をDBから取得"""
    db = get_database()
    if _db_usable(db):
        return db.get_global_state('ADMIN_MODE', default_value=False)
    return _admin_mode


def set_admin_mode(value):
    """管理者モード設定をDBに保存"""
    global _admin_mode
    db = get_database()
    if _db_usable(db):
        db.set_global_state('ADMIN_MODE', value)
    _admin_mode = value


def get_manual_reply_queue():
    """手動返信キューをDBから取得"""
    db = get_database()
    if _db_usable(db):
        return db.get_global_state('MANUAL_REPLY_QUEUE', default_value=[])
    return _manual_reply_queue


def set_manual_reply_queue(value):
    """手動返信キューをDBに保存"""
    global _manual_reply_queue
    db = get_database()
    if _db_usable(db):
        db.set_global_state('MANUAL_REPLY_QUEUE', value)
    _manual_reply_queue = value


def get_manual_reply_message():
    """手動返信時の自動メッセージを取得"""
    global _manual_reply_message_cache
    if _manual_reply_message_cache is not None:
        return _manual_reply_message_cache
    db = get_database()
    if _db_usable(db):
        db_value = db.get_global_state('MANUAL_REPLY_MESSAGE', default_value=None)
        if db_value is not None:
            _manual_reply_message_cache = db_value
            return db_value
    return DEFAULT_MANUAL_REPLY_MESSAGE


def set_manual_reply_message(value):
    """手動返信時の自動メッセージを保存"""
    global _manual_reply_message_cache
    db = get_database()
    if _db_usable(db):
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


def _session_last_activity_ts(info) -> float:
    last_activity = info.get('last_activity')
    if isinstance(last_activity, datetime):
        return last_activity.timestamp()
    if isinstance(last_activity, str):
        try:
            return datetime.fromisoformat(
                last_activity.replace('Z', '+00:00')
            ).timestamp()
        except Exception:
            return 0.0
    if isinstance(last_activity, (int, float)):
        return float(last_activity)
    return 0.0


def get_manual_reply_session_ids():
    """手動返信キューに載っている session_id の集合。"""
    ids = set()
    for item in get_manual_reply_queue():
        sid = item.get('session_id')
        if sid:
            ids.add(str(sid))
    return ids


def get_cleanup_exclude_session_ids(extra_ids=None):
    """クリーンアップ・purge から除外する session_id 一覧。"""
    exclude = set(get_manual_reply_session_ids())
    if extra_ids:
        for sid in extra_ids:
            if sid:
                exclude.add(str(sid))
    all_sessions = get_all_sessions_from_db()
    for sid, info in all_sessions.items():
        if not isinstance(info, dict):
            continue
        if info.get('crisis_detected'):
            exclude.add(str(sid))
    return list(exclude)


def purge_empty_sessions_on_startup():
    """起動時: 空セッションを一括削除（キュー・危機フラグは除外）。"""
    db = get_database()
    if not _db_usable(db):
        return 0
    exclude = get_cleanup_exclude_session_ids()
    if hasattr(db, 'purge_all_empty_sessions'):
        return db.purge_all_empty_sessions(exclude_session_ids=exclude)
    return 0


def find_existing_session(client_ip, user_agent):
    """既存のセッションを検索（同じ人からのアクセスのみ）"""
    if not client_ip and not user_agent:
        return None
    current_time = time.time()
    all_sessions = get_all_sessions_from_db()
    for existing_sid, info in all_sessions.items():
        if not isinstance(info, dict):
            continue
        messages = info.get('messages') or []
        if not messages:
            continue
        if (info.get('client_ip') == client_ip and
                info.get('user_agent') == user_agent and
                current_time - _session_last_activity_ts(info) < SESSION_REUSE_WINDOW):
            return existing_sid
    return None


def ensure_session_persisted(sid, data, request=None):
    """意味のあるイベント時にのみ DB へセッションを保存する。"""
    if not sid:
        return
    session_data = get_session_from_db(sid) or {}
    client_ip = ''
    user_agent = ''
    if request is not None:
        client_ip = request.client.host if getattr(request, 'client', None) else ''
        user_agent = request.headers.get('User-Agent', '') or ''

    if isinstance(data, dict):
        for key, value in data.items():
            if value is not None:
                session_data[key] = value

    session_data['session_id'] = sid
    session_data.setdefault('messages', session_data.get('messages') or [])
    session_data['last_activity'] = datetime.now()
    session_data.setdefault('session_active', True)
    if client_ip:
        session_data['client_ip'] = client_ip
    if user_agent:
        session_data['user_agent'] = user_agent
    if not session_data.get('username'):
        session_data['username'] = f'ユーザー{get_next_user_number()}'

    save_session_to_db(sid, session_data)


def update_session_activity(sid):
    """セッションの最終アクティビティを更新"""
    if not sid:
        return
    session_data = get_session_from_db(sid)
    if session_data:
        session_data['last_activity'] = datetime.now()
        maybe_persist_session_activity(sid, session_data)


def was_last_user_message(session, content: str) -> bool:
    """直前のメッセージが同一内容のユーザー発言か（同一リクエスト内の二重追加防止用）。"""
    messages = session.get('messages') or []
    if not messages:
        return False
    last = messages[-1]
    return last.get('type') == 'user' and last.get('content') == content


def has_recent_counseling_reply_for_user(session, user_content: str) -> bool:
    """直前が同一内容 user へのカウンセリング bot 返信なら True（並列 POST 防止）。

    呼び出し前に user を追記済みの場合、意図的な再送では末尾が user になるため False。
    """
    messages = session.get("messages") or []
    if len(messages) < 2:
        return False
    last = messages[-1]
    prev = messages[-2]
    if last.get("type") != "bot":
        return False
    if not (last.get("counseling") or last.get("inappropriate_request")):
        return False
    return prev.get("type") == "user" and prev.get("content") == user_content


def has_recent_concierge_reply_for_user(session, user_content: str) -> bool:
    """直前が同一内容 user への Concierge bot 返信なら True（並列 POST 防止）。

    パイプラインで user が先に追記済みの場合、末尾は user のままなので False（応答生成を続行）。
    """
    messages = session.get("messages") or []
    if len(messages) < 2:
        return False
    last = messages[-1]
    prev = messages[-2]
    if last.get("type") != "bot":
        return False
    if not last.get("concierge"):
        return False
    return prev.get("type") == "user" and prev.get("content") == user_content


def append_user_message(session, content: str) -> dict:
    """セッションにユーザーメッセージを追加する（同一文言の再送も別メッセージとして保持）。"""
    import uuid

    if 'messages' not in session:
        session['messages'] = []
    user_msg = {
        'type': 'user',
        'content': content,
        'timestamp': datetime.now().isoformat(),
        'uuid': str(uuid.uuid4()),
    }
    session['messages'].append(user_msg)
    if hasattr(session, 'modified'):
        session.modified = True
    return user_msg


def remove_duplicate_user_messages_after_ai_response(sid):
    """後方互換のため残置。文言ベースの重複削除は行わない（同一内容の再送を保持）。"""
    return False


def _message_merge_key(msg: dict, index: int = 0) -> str:
    uid = msg.get('uuid') or msg.get('message_id')
    if uid:
        return f'id:{uid}'
    ts = msg.get('timestamp') or ''
    content = (msg.get('content') or '')[:200]
    return f'c:{msg.get("type")}:{ts}:{content}'


def normalize_session_messages(messages):
    """連続する同一カウンセリング bot（並列 POST の残骸）を除去。user は保持。"""
    items = list(messages or [])
    if not items:
        return []
    out = []
    for msg in items:
        if (
            out
            and msg.get("type") == "bot"
            and out[-1].get("type") == "bot"
            and (msg.get("counseling") or msg.get("inappropriate_request"))
            and (out[-1].get("counseling") or out[-1].get("inappropriate_request"))
            and (msg.get("content") or "").strip() == (out[-1].get("content") or "").strip()
        ):
            continue
        out.append(msg)
    return out


def merge_session_messages(server_messages, client_messages):
    """サーバー・クライアント双方のメッセージを uuid 等で重複排除しつつマージする。"""
    server = list(server_messages or [])
    client = list(client_messages or [])
    if not client:
        return server
    if not server:
        return client
    seen = set()
    merged = []
    for i, msg in enumerate(server):
        key = _message_merge_key(msg, i)
        if key in seen:
            continue
        seen.add(key)
        merged.append(msg)
    base = len(merged)
    for j, msg in enumerate(client):
        key = _message_merge_key(msg, base + j)
        if key in seen:
            continue
        seen.add(key)
        merged.append(msg)
    return merged


def persist_session_from_chat_state(sid, session, request=None, *, force_persist: bool = True):
    """チャット POST 終了時にセッション状態（メッセージ含む）を永続化する。"""
    if not sid:
        return
    session_data = get_session_from_db(sid) or {}
    messages = session.get('messages')
    if messages is None:
        messages = session_data.get('messages') or []
    payload = {
        'messages': messages,
        'user_attributes': session.get('user_attributes')
        or session_data.get('user_attributes')
        or {},
        'session_active': True,
    }
    username = session.get('username')
    if username:
        payload['username'] = username
    for flag_key in (
        'medical_emergency_otc_locked',
        'otc_lock_released',
        'store_incident_soft_banner',
        'store_incident_otc_opt_in',
        'emergency_subtype',
        'emergency_detected',
        'store_incident_emergency',
        'crisis_detected',
        'concierge_state',
        'counseling_mode',
        'last_triage_result',
        '_last_triage_result',
    ):
        if flag_key in session:
            payload[flag_key] = session[flag_key]

    try:
        from src.handlers.line.line_session import is_line_session_id
    except ImportError:
        is_line_session_id = lambda _: False  # type: ignore[misc, assignment]

    if is_line_session_id(sid) and not force_persist:
        merged = dict(session_data)
        merged.update(payload)
        maybe_persist_session_activity(sid, merged)
        return

    ensure_session_persisted(sid, payload, request)


def cleanup_old_sessions(
    force=False,
    exclude_current_session=True,
    current_sid=None,
    skip_empty_sessions=False,
):
    """
    古いセッションをクリーンアップ（メモリ最適化）

    Args:
        force: Trueの場合、間隔を無視して強制実行
        exclude_current_session: Trueの場合、現在のセッションを削除から除外
        current_sid: 現在のセッションID（除外用、exclude_current_sessionがTrueの場合）。
            Webリクエストハンドラーから呼ぶ場合は、
            current_sid=session.get('_id') if has_request_context() else None を渡すこと。
        skip_empty_sessions: True のときメッセージ0件セッションは削除しない
    """
    global _last_cleanup_time
    current_time = time.time()

    if not force:
        if (current_time - _last_cleanup_time) < CLEANUP_INTERVAL:
            return
        if (current_time - _last_cleanup_time) < MAX_CLEANUP_DELAY:
            return

    db = get_database()
    extra = [current_sid] if exclude_current_session and current_sid else []
    exclude_session_ids = get_cleanup_exclude_session_ids(extra)

    if _db_usable(db) and hasattr(db, 'cleanup_expired_sessions'):
        try:
            deleted_count = db.cleanup_expired_sessions(
                SESSION_TIMEOUT,
                exclude_session_ids=exclude_session_ids if exclude_session_ids else None,
                chat_end_timeout_seconds=CHAT_END_TIMEOUT,
                empty_session_timeout_seconds=EMPTY_SESSION_TIMEOUT,
                skip_empty_sessions=skip_empty_sessions,
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
        if sid in exclude_session_ids:
            continue
        if not isinstance(session_info, dict):
            continue
        messages = session_info.get('messages') or []
        last_ts = _session_last_activity_ts(session_info)
        if not messages:
            if not skip_empty_sessions and current_time - last_ts > EMPTY_SESSION_TIMEOUT:
                sessions_to_remove.append(sid)
            continue
        if current_time - last_ts > SESSION_TIMEOUT:
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
        if sid not in exclude_session_ids:
            if _db_usable(db):
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


def mark_session_deleted(session_id: str) -> None:
    """明示的に終了したセッション（new_session 等）を restore 対象外にする。"""
    if not session_id:
        return
    _purge_stale_deleted_sids()
    _recently_deleted_sids[str(session_id)] = time.time()


def is_session_recently_deleted(session_id: str) -> bool:
    if not session_id:
        return False
    _purge_stale_deleted_sids()
    return str(session_id) in _recently_deleted_sids


def _purge_stale_deleted_sids() -> None:
    now = time.time()
    stale = [
        sid
        for sid, ts in _recently_deleted_sids.items()
        if now - ts > _DELETED_SID_TTL_SEC
    ]
    for sid in stale:
        _recently_deleted_sids.pop(sid, None)


def delete_session_by_id(session_id: str) -> bool:
    """DB とメモリの両方からセッションを削除（一覧 API と同じデータソース）。"""
    if not session_id:
        return False
    deleted = False
    db = get_database()
    if db and db.is_available():
        try:
            if db.delete_session(session_id):
                deleted = True
        except Exception as e:
            logger.warning("DB delete_session failed for %s: %s", session_id, e)
    if session_id in _all_sessions:
        del _all_sessions[session_id]
        deleted = True
    queue = get_manual_reply_queue()
    filtered = [item for item in queue if str(item.get("session_id")) != str(session_id)]
    if len(filtered) != len(queue):
        set_manual_reply_queue(filtered)
        deleted = True
    return deleted
