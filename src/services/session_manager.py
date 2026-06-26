"""
セッション管理モジュール

DB・メモリへのセッション保存・取得、グローバル状態の管理を行う。
"""
import time
import logging
from datetime import datetime

from src.utils.jst_datetime import now_jst_iso
from src.utils.allergen_attributes import merge_chat_user_attributes

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
_ai_auto_reply_pending = False
_admin_mode = False
_admin_mode_pending = False
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
    try:
        from src.handlers.line.line_session import is_line_session_id, normalize_line_session_id
    except ImportError:
        is_line_session_id = lambda _sid: False  # type: ignore[misc, assignment]
        normalize_line_session_id = lambda s: s  # type: ignore[misc, assignment]

    if session_id and is_line_session_id(session_id):
        session_id = normalize_line_session_id(session_id) or session_id

    mem = _all_sessions.get(session_id)

    # LINE: prime 済みなら DB 読込をスキップ（永続化は persist 時のみ）
    if session_id and is_line_session_id(session_id):
        if mem is not None:
            merged = dict(mem)
            from src.services.session_lifecycle import ensure_line_session_archive

            ensure_line_session_archive(merged)
            return merged
        global _db_persist_enabled
        db = get_database()
        db_data = None
        if _db_usable(db):
            db_data = db.get_session(session_id)
        if db_data:
            touch_session_in_memory(session_id, db_data)
        return _merge_line_session_sources(db_data, mem)

    global _db_persist_enabled
    db = get_database()
    db_data = None
    if _db_usable(db):
        db_data = db.get_session(session_id)

    if _db_persist_enabled is False:
        return mem
    if db_data:
        touch_session_in_memory(session_id, db_data)
        return db_data
    return mem


def _merge_line_session_sources(db_data: dict | None, mem: dict | None) -> dict | None:
    """LINE セッションの DB とメモリを統合（管理画面用アーカイブを欠落させない）。"""
    from src.services.session_lifecycle import ensure_line_session_archive, merge_messages_into_archive

    if not db_data and not mem:
        return None
    merged: dict = {}
    if db_data:
        merged.update(db_data)
    if mem:
        for key, val in mem.items():
            if val is not None:
                merged[key] = val
    if db_data and mem:
        # DB（古い履歴）を先にアーカイブへ入れ、メモリ側の新着を後からマージする
        if db_data.get("messages"):
            merge_messages_into_archive(merged, db_data.get("messages") or [])
        if mem.get("messages"):
            merge_messages_into_archive(merged, mem.get("messages") or [])
    ensure_line_session_archive(merged)
    return merged


def get_line_session_admin_snapshot(session_id: str) -> dict | None:
    """管理画面用: LINE セッションの DB アーカイブとメモリ live を必ず統合する。"""
    try:
        from src.handlers.line.line_session import is_line_session_id, normalize_line_session_id
    except ImportError:
        return None
    if not session_id or not is_line_session_id(session_id):
        return None
    session_id = normalize_line_session_id(session_id) or session_id
    mem = _all_sessions.get(session_id)
    db_data = None
    db = get_database()
    if _db_usable(db):
        db_data = db.get_session(session_id)
    return _merge_line_session_sources(db_data, mem)


def get_session_from_memory(session_id):
    """メモリフォールバックからセッションを取得（DB失敗時の最新データ）"""
    return _all_sessions.get(session_id)


def resolve_session_snapshot(session_id: str | None) -> dict | None:
    """LINE は prime 済みメモリのみ、Web は get_session_from_db。"""
    if not session_id:
        return None
    try:
        from src.handlers.line.line_session import is_line_session_id
    except ImportError:
        is_line_session_id = lambda _sid: False  # type: ignore[misc, assignment]
    if is_line_session_id(session_id):
        return get_session_from_memory(session_id)
    return get_session_from_db(session_id)


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
    try:
        from src.handlers.line.line_session import is_line_session_id, normalize_line_session_id
    except ImportError:
        is_line_session_id = lambda _sid: False  # type: ignore[misc, assignment]
        normalize_line_session_id = lambda s: s  # type: ignore[misc, assignment]

    if session_id and is_line_session_id(session_id):
        session_id = normalize_line_session_id(session_id) or session_id
        if isinstance(data, dict):
            data["session_id"] = session_id

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
    try:
        from src.handlers.line.line_session import is_line_session_id
    except ImportError:
        is_line_session_id = lambda _sid: False  # type: ignore[misc, assignment]

    db = get_database()
    if _db_usable(db):
        sessions = db.get_all_sessions()
        if sessions is not None:
            result = {s['session_id']: s for s in sessions}
            for sid, mem in _all_sessions.items():
                if sid in result:
                    if is_line_session_id(sid):
                        merged = _merge_line_session_sources(result[sid], mem)
                        if merged:
                            result[sid] = merged
                else:
                    result[sid] = mem
            return result
    return _all_sessions


# --- グローバル状態 ---

def _coerce_bool(value, default: bool) -> bool:
    """global_state の JSONB 値を bool に正規化する。"""
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in ('true', '1', 'yes', 'on', 'auto'):
            return True
        if normalized in ('false', '0', 'no', 'off', 'manual'):
            return False
    return bool(value)


def _try_persist_global_bool(key: str, value: bool, pending_flag: str) -> bool:
    """DB へ bool グローバル状態を保存し、成功時に pending フラグを解除する。"""
    db = get_database()
    if not _db_usable(db):
        return False
    if db.set_global_state(key, value):
        globals()[pending_flag] = False
        return True
    return False


def get_ai_auto_reply_in_memory() -> bool:
    """DB を参照せずモジュール内キャッシュの AI 自動応答設定を返す（LINE ホットパス用）。"""
    return _coerce_bool(_ai_auto_reply, True)


def get_ai_auto_reply():
    """AI自動応答設定をDBから取得（不可時はメモリキャッシュ）。"""
    global _ai_auto_reply, _ai_auto_reply_pending
    if _ai_auto_reply_pending:
        _try_persist_global_bool(
            'AI_AUTO_REPLY', _coerce_bool(_ai_auto_reply, True), '_ai_auto_reply_pending'
        )
        return _coerce_bool(_ai_auto_reply, True)
    if not is_db_persist_enabled():
        return _coerce_bool(_ai_auto_reply, True)
    db = get_database()
    if not _db_usable(db):
        return _coerce_bool(_ai_auto_reply, True)
    try:
        value = db.get_global_state('AI_AUTO_REPLY', default_value=True)
        coerced = _coerce_bool(value, True)
        _ai_auto_reply = coerced
        return coerced
    except Exception as exc:
        logger.warning("get_ai_auto_reply: DB read failed (%s); using in-memory value", exc)
        return _coerce_bool(_ai_auto_reply, True)


def set_ai_auto_reply(value):
    """AI自動応答設定をDBに保存"""
    global _ai_auto_reply, _ai_auto_reply_pending
    coerced = _coerce_bool(value, True)
    _ai_auto_reply = coerced
    if _try_persist_global_bool('AI_AUTO_REPLY', coerced, '_ai_auto_reply_pending'):
        return
    _ai_auto_reply_pending = True
    if _db_usable(get_database()):
        logger.warning(
            "set_ai_auto_reply: DB write failed; keeping in-memory value=%s until retry",
            coerced,
        )


def get_admin_mode():
    """管理者モード設定をDBから取得"""
    global _admin_mode, _admin_mode_pending
    if _admin_mode_pending:
        _try_persist_global_bool(
            'ADMIN_MODE', _coerce_bool(_admin_mode, False), '_admin_mode_pending'
        )
        return _coerce_bool(_admin_mode, False)
    if not is_db_persist_enabled():
        return _coerce_bool(_admin_mode, False)
    db = get_database()
    if not _db_usable(db):
        return _coerce_bool(_admin_mode, False)
    try:
        value = db.get_global_state('ADMIN_MODE', default_value=False)
        coerced = _coerce_bool(value, False)
        _admin_mode = coerced
        return coerced
    except Exception as exc:
        logger.warning("get_admin_mode: DB read failed (%s); using in-memory value", exc)
        return _coerce_bool(_admin_mode, False)


def set_admin_mode(value):
    """管理者モード設定をDBに保存"""
    global _admin_mode, _admin_mode_pending
    coerced = _coerce_bool(value, False)
    _admin_mode = coerced
    if _try_persist_global_bool('ADMIN_MODE', coerced, '_admin_mode_pending'):
        return
    _admin_mode_pending = True
    if _db_usable(get_database()):
        logger.warning(
            "set_admin_mode: DB write failed; keeping in-memory value=%s until retry",
            coerced,
        )


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


def clear_admin_request_state(session_id: str, session_data: dict | None = None) -> None:
    """薬剤師要請フラグと手動返信キュー登録を解除する。"""
    if session_data is not None:
        session_data.pop("admin_request", None)
        if session_data.get("ai_auto_reply") is False:
            session_data["ai_auto_reply"] = True
    if not session_id:
        return
    queue = get_manual_reply_queue()
    filtered = [item for item in queue if str(item.get("session_id")) != str(session_id)]
    if len(filtered) != len(queue):
        set_manual_reply_queue(filtered)


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
        username = info.get('username') or ''
        if not isinstance(username, str):
            username = str(username)
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
            from src.utils.admin_timestamp import parse_admin_timestamp

            parsed = parse_admin_timestamp(last_activity)
            if parsed is not None:
                return parsed.timestamp()
        except Exception:
            pass
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
        try:
            from src.handlers.line.line_session import is_line_session_id
        except ImportError:
            is_line_session_id = lambda _sid: False  # type: ignore[misc, assignment]
        if is_line_session_id(str(sid)):
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
    session_data['last_activity'] = now_jst_iso()
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
        session_data['last_activity'] = now_jst_iso()
        maybe_persist_session_activity(sid, session_data)


def was_last_user_message(session, content: str) -> bool:
    """直前のメッセージが同一内容のユーザー発言か（同一リクエスト内の二重追加防止用）。"""
    messages = session.get('messages') or []
    if not messages:
        return False
    last = messages[-1]
    return last.get('type') == 'user' and last.get('content') == content


def should_skip_duplicate_user_append(session, content: str) -> bool:
    """ユーザー情報通知 bot 等を挟んでも、同一ターン内の user 二重追加を防ぐ。"""
    messages = session.get('messages') or []
    for msg in reversed(messages):
        if msg.get('type') == 'user':
            return msg.get('content') == content
        if msg.get('type') == 'bot':
            if msg.get('user_info_notification'):
                continue
            if is_diagnosis_notice_bot_message(msg):
                continue
            return False
    return False


def is_diagnosis_notice_bot_message(msg: dict) -> bool:
    """診断名カウンセリング・Physical ブロック bot（user 重複判定用）。"""
    if not msg or msg.get('type') != 'bot':
        return False
    if msg.get('diagnosis_type') or msg.get('diagnosis_physical_blocked'):
        return True
    kind = (msg.get('diagnosis') or {}).get('kind')
    return kind in ('diagnosis_detected', 'diagnosis_physical_blocked')


def has_diagnosis_notice_for_user(session, user_content: str) -> bool:
    """同一 user 文言に対する診断名通知 bot が既にセッションにあるか。"""
    messages = session.get('messages') or []
    for i in range(len(messages) - 1, -1, -1):
        msg = messages[i]
        if msg.get('type') != 'bot' or not is_diagnosis_notice_bot_message(msg):
            continue
        for j in range(i - 1, -1, -1):
            prev = messages[j]
            if prev.get('type') == 'user':
                return prev.get('content') == user_content
            if (
                prev.get('type') == 'bot'
                and not prev.get('user_info_notification')
                and not is_diagnosis_notice_bot_message(prev)
            ):
                break
        return False
    return False


def should_skip_append_user_message(session, content: str) -> bool:
    """user メッセージ追記をスキップすべきか（末尾一致 + 通知挟み込み）。"""
    return was_last_user_message(session, content) or should_skip_duplicate_user_append(
        session, content
    )


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


def append_user_message(session, content: str, *, timestamp: str | None = None) -> dict:
    """セッションにユーザーメッセージを追加する（同一文言の再送も別メッセージとして保持）。"""
    import uuid

    if timestamp is None:
        try:
            from src.handlers.line.line_session import is_line_session_id

            sid = session.get("_id") if hasattr(session, "get") else None
            if sid and is_line_session_id(str(sid)):
                from src.handlers.line.line_timestamp import resolve_inbound_message_timestamp

                timestamp = resolve_inbound_message_timestamp()
            else:
                from src.utils.jst_datetime import now_jst_iso

                timestamp = now_jst_iso()
        except ImportError:
            from src.utils.jst_datetime import now_jst_iso

            timestamp = now_jst_iso()

    if 'messages' not in session:
        session['messages'] = []
    user_msg = {
        'type': 'user',
        'content': content,
        'timestamp': timestamp,
        'uuid': str(uuid.uuid4()),
    }
    session['messages'].append(user_msg)
    if hasattr(session, 'modified'):
        session.modified = True
    return user_msg


def remove_duplicate_user_messages_after_ai_response(sid):
    """後方互換のため残置。文言ベースの重複削除は行わない（同一内容の再送を保持）。"""
    return False


def _message_content_for_merge_key(msg: dict) -> str:
    content = (msg.get("content") or "").strip()
    if content:
        return content[:200]
    for field in ("message", "text", "user_message"):
        alt = (msg.get(field) or "").strip()
        if alt:
            return alt[:200]
    return ""


def _message_merge_key(msg: dict, index: int = 0) -> str:
    uid = msg.get('uuid') or msg.get('message_id')
    if uid:
        return f'id:{uid}'
    ts = msg.get('timestamp') or ''
    content = _message_content_for_merge_key(msg)
    return f'c:{msg.get("type")}:{ts}:{content}'


def _message_merge_keys(msg: dict, index: int = 0) -> set[str]:
    """管理画面から送られたキーと DB 上の生メッセージを突合するための候補キー集合。"""
    keys = {_message_merge_key(msg, index)}
    uid = msg.get("uuid") or msg.get("message_id")
    if uid:
        keys.add(f"id:{uid}")
    msg_type = msg.get("type") or ""
    raw_ts = msg.get("timestamp") or ""
    content = _message_content_for_merge_key(msg)
    try:
        from src.utils.admin_timestamp import format_admin_timestamp_iso

        norm_ts = format_admin_timestamp_iso(raw_ts)
    except Exception:
        norm_ts = None
    for ts in {raw_ts, norm_ts or ""}:
        if ts == "" and raw_ts != "":
            continue
        keys.add(f"c:{msg_type}:{ts}:{content}")
    return keys


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


def persist_session_from_chat_state(sid, session, request=None, *, force_persist: bool = True, session_data: dict | None = None):
    """チャット POST 終了時にセッション状態（メッセージ含む）を永続化する。"""
    if not sid:
        return
    if session_data is None:
        session_data = get_session_from_db(sid) or {}
    messages = session.get('messages')
    if messages is None:
        messages = session_data.get('messages') or []
    payload = {
        'messages': messages,
        'user_attributes': merge_chat_user_attributes(
            session_data.get('user_attributes'),
            session.get('user_attributes'),
        ),
        'session_active': True,
    }
    username = session.get('username')
    if username:
        payload['username'] = username
    if session.get('line_profile'):
        payload['line_profile'] = session.get('line_profile')
    if session_data.get('message_archive'):
        payload['message_archive'] = session_data.get('message_archive')
    if session_data.get('lifecycle_log'):
        payload['lifecycle_log'] = session_data.get('lifecycle_log')
    elif session.get('lifecycle_log'):
        payload['lifecycle_log'] = session.get('lifecycle_log')
    for flag_key in (
        "detected_language",
        "language",
        "medical_emergency_otc_locked",
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
        'pending_memory_delete',
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
    _schedule_line_memory_side_effects(sid, session, payload)


def _schedule_line_memory_side_effects(sid, session, payload: dict) -> None:
    try:
        from src.services.line_memory_jobs import schedule_profile_persist
        from src.services.line_user_memory import merge_user_attributes, resolve_memory_owner_sid

        owner = resolve_memory_owner_sid(sid, session) or resolve_memory_owner_sid(sid, payload)
        if not owner:
            return
        attrs = dict(payload.get("user_attributes") or {})
        if session is not None and hasattr(session, "get"):
            attrs = merge_user_attributes(attrs, session.get("user_attributes"))
        schedule_profile_persist(owner, attrs)
    except Exception:
        logger.debug("line memory side effects skipped sid=%s", sid, exc_info=True)


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
        try:
            from src.handlers.line.line_session import is_line_session_id
        except ImportError:
            is_line_session_id = lambda _sid: False  # type: ignore[misc, assignment]
        if not messages:
            if is_line_session_id(str(sid)):
                continue
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
            session_info = all_sessions.get(sid) if isinstance(all_sessions, dict) else None
            if isinstance(session_info, dict):
                from src.services.session_lifecycle import append_lifecycle_event

                append_lifecycle_event(
                    session_info,
                    "memory_deleted",
                    source="session_manager.cleanup_old_sessions",
                    detail="メモリクリーンアップによりセッション全体を削除",
                    messages_before=len(session_info.get("messages") or []),
                )
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


def delete_messages_from_session(session_id: str, message_keys: list[str]) -> tuple[int, dict | None]:
    """指定キーに一致するメッセージを messages / message_archive から削除する。"""
    if not session_id or not message_keys:
        return 0, None
    keys_set = {str(k) for k in message_keys if k}
    if not keys_set:
        return 0, None

    try:
        from src.handlers.line.line_session import is_line_session_id, normalize_line_session_id
    except ImportError:
        is_line_session_id = lambda _sid: False  # type: ignore[misc, assignment]
        normalize_line_session_id = lambda s: s  # type: ignore[misc, assignment]

    session_id = normalize_line_session_id(session_id) or session_id
    if is_line_session_id(session_id):
        session_data = get_line_session_admin_snapshot(session_id)
    else:
        session_data = get_session_from_db(session_id)
    if not session_data:
        return 0, None

    deleted = 0

    def _filter_messages(msgs: list) -> list:
        nonlocal deleted
        if not msgs:
            return []
        kept: list = []
        for i, msg in enumerate(msgs):
            if not isinstance(msg, dict):
                kept.append(msg)
                continue
            if _message_merge_keys(msg, i) & keys_set:
                deleted += 1
            else:
                kept.append(msg)
        return kept

    for field in ("messages", "message_archive"):
        if session_data.get(field):
            session_data[field] = _filter_messages(session_data.get(field) or [])

    if deleted == 0:
        return 0, session_data

    from src.utils.admin_timestamp import sync_last_activity_from_messages
    from src.handlers.line.line_session import is_line_session_id

    sync_last_activity_from_messages(
        session_data,
        naive_as_utc=is_line_session_id(str(session_id)),
    )
    save_session_to_db(session_id, session_data)
    return deleted, session_data


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
