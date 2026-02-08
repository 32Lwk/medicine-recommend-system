"""
メイン画面・チャットルート

責務: メイン画面（index）、favicon、clear、new_session のルート定義とビュー実装
"""
import random
import time
from datetime import datetime

import pytz
from flask import Blueprint, current_app, has_request_context, jsonify, render_template, request

from src.services.analytics import log_access_analytics
from src.services.session_manager import (
    cleanup_old_sessions,
    find_existing_session,
    get_all_sessions_from_db,
    get_next_user_number,
    get_session_from_db,
    save_session_to_db,
)
from src.core.season_manager import get_current_season, get_season_images
from src.utils.performance_monitor import get_global_monitor, log_performance_metrics


def favicon():
    """favicon.icoの404エラーを防ぐ"""
    return '', 204


def index():
    """メイン画面・チャット"""
    from datetime import datetime

    session = current_app.extensions['safe_session']
    VERSION = current_app.config.get('VERSION', str(int(time.time())))

    monitor = get_global_monitor()
    monitor.start_monitoring()
    monitor.increment_request()

    current_sid = session.get('_id') if has_request_context() else None
    cleanup_old_sessions(force=False, exclude_current_session=True, current_sid=current_sid)

    current_time = time.time()
    client_ip = request.remote_addr
    user_agent = request.headers.get('User-Agent', '')

    session.setdefault('messages', [])
    session.setdefault('user_attributes', {
        'age': None,
        'gender': None,
        'pregnant': None,
        'breastfeeding': None,
        'current_medications': [],
        'allergies': [],
        'medical_history': [],
        'symptom_duration_days': None,
        'other_info': None
    })

    sid = session.get('_id')
    if not sid:
        sid = str(int(time.time() * 1000000)) + str(random.randint(100000, 999999))
        session['_id'] = sid
        session['ui_language'] = 'ja'
        session['detected_language'] = 'ja'

    all_sessions = get_all_sessions_from_db()

    if 'username' not in session:
        existing_session = find_existing_session(client_ip, user_agent)
        if existing_session:
            existing_session_data = get_session_from_db(existing_session)
            if existing_session_data:
                session['username'] = existing_session_data.get('username', '')
                session['messages'] = existing_session_data.get('messages', []).copy()
        else:
            user_number = get_next_user_number()
            session['username'] = f'ユーザー{user_number}'
            session['messages'] = []

    if sid:
        session_data = get_session_from_db(sid)
        if session_data:
            session['messages'] = session_data.get('messages', []).copy()
            db_attrs = session_data.get('user_attributes', {})
            if db_attrs:
                current_attrs = session.get('user_attributes', {}) or {}
                merged = {**current_attrs, **db_attrs}
                session['user_attributes'] = merged

    current_messages = session.get('messages', []).copy()

    if request.method == 'POST':
        from src.handlers.chat_handler import handle_chat_post
        return handle_chat_post(session, request, sid, monitor, client_ip, user_agent)

    VERSION = current_app.config.get('VERSION', str(int(time.time())))
    metrics = monitor.get_metrics()
    log_performance_metrics(monitor, sid, 'GET_request', {
        'user_agent': user_agent,
        'client_ip': client_ip
    })

    session_data = get_session_from_db(sid) if sid else None
    message_count = len(session_data.get('messages', [])) if session_data else 0
    log_access_analytics(sid, user_agent, client_ip, metrics['response_time_ms'], {
        'username': session.get('username', ''),
        'message_count': message_count
    })

    messages = session_data.get('messages', []) if session_data else []

    try:
        jst = pytz.timezone('Asia/Tokyo')
        current_date = datetime.now(jst)
        season_type = get_current_season(current_date)
        year = current_date.year
        decoration_images = []
        if season_type:
            decoration_images = get_season_images(season_type, year, session)
        image_version = VERSION
    except Exception:
        decoration_images = []
        image_version = VERSION

    return render_template('index.html',
                          messages=messages,
                          version=VERSION,
                          username=session.get('username', 'Unknown'),
                          decoration_images=decoration_images,
                          image_version=image_version)


def clear_chat():
    """チャット履歴をクリア"""
    session = current_app.extensions['safe_session']
    session['messages'] = []
    session.modified = True
    sid = session.get('_id')
    if sid:
        session_data = get_session_from_db(sid)
        if session_data:
            session_data['messages'] = []
            save_session_to_db(sid, session_data)
    session.pop('chat_ended', None)
    return '', 204


def new_session():
    """新しいセッションを開始"""
    session = current_app.extensions['safe_session']
    session.clear()

    sid = str(int(time.time() * 1000)) + str(id(session))
    session['_id'] = sid
    user_number = get_next_user_number()
    session['username'] = f'ユーザー{user_number}'
    session['messages'] = []
    session.modified = True

    client_ip = request.remote_addr
    user_agent = request.headers.get('User-Agent', '')
    session_data = {
        'session_id': sid,
        'username': session['username'],
        'messages': [],
        'last_activity': datetime.now(),
        'client_ip': client_ip,
        'user_agent': user_agent,
        'user_attributes': session.get('user_attributes', {}),
        'session_active': True
    }
    save_session_to_db(sid, session_data)

    return jsonify({
        'message': '新しいセッションを開始しました',
        'username': session['username']
    }), 200


def create_main_routes():
    """メインルートの Blueprint を作成（ビューは当モジュール内で定義）"""
    bp = Blueprint('main', __name__)
    bp.add_url_rule('/favicon.ico', view_func=favicon)
    bp.add_url_rule('/', view_func=index, methods=['GET', 'POST'])
    bp.add_url_rule('/clear', view_func=clear_chat, methods=['POST'])
    bp.add_url_rule('/new_session', view_func=new_session, methods=['POST'])
    return bp
