"""
メイン画面・チャットルート

責務: メイン画面（index）、favicon、sitemap、clear、new_session のルート定義とビュー実装
"""
import os
import random
import time
from datetime import datetime
from xml.sax.saxutils import escape

import pytz
from flask import Blueprint, current_app, has_request_context, jsonify, render_template, request, Response, send_from_directory

from src.utils.chat_http_context import ChatClientInfo

from src.services.analytics import log_access_analytics
from src.services.session_manager import (
    cleanup_old_sessions,
    find_existing_session,
    get_all_sessions_from_db,
    get_next_user_number,
    get_session_from_db,
    save_session_to_db,
)
import json

from src.core.season_manager import get_current_season, get_particle_profile, get_season_images
from src.utils.performance_monitor import get_global_monitor, log_performance_metrics


def favicon():
    """ブラウザの /favicon.ico 要求に PNG を返す（無い場合のみ 204）。"""
    path = os.path.join(current_app.static_folder, 'favicon.ico.png')
    if not os.path.isfile(path):
        return '', 204
    return send_from_directory(current_app.static_folder, 'favicon.ico.png', mimetype='image/png')


def sitemap():
    """
    Google Search Console 向けサイトマップ。
    公開 URL は環境変数 PUBLIC_SITE_URL（例: https://medicine.yutok.dev）で指定。未設定時は本番想定の既定値。
    情報系画面は同一 URL 上の UI のため、インデックス対象はトップのみ。
    """
    base = (os.getenv('PUBLIC_SITE_URL') or 'https://medicine.yutok.dev').rstrip('/')
    loc = escape(f'{base}/', {'"': '&quot;', "'": '&apos;'})
    body = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        f'<url><loc>{loc}</loc><changefreq>weekly</changefreq><priority>1.0</priority></url>'
        '</urlset>'
    )
    return Response(body, mimetype='application/xml; charset=utf-8')


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
    chat_client = ChatClientInfo.from_flask_request(request)
    client_ip = chat_client.client_ip
    user_agent = chat_client.user_agent

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
                # 既存セッションを見つけた場合は、SIDも含めて引き継ぐ。
                # messagesだけコピーしてSIDを新規のままにすると、/api/sessions（DB優先）が0件になり、
                # その後にセッションcookie内のmessagesが削除されて「履歴が消えた」ように見える。
                sid = existing_session
                session['_id'] = sid
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
        message = request.form.get('message', '')
        body, code = handle_chat_post(session, chat_client, message, sid, monitor)
        return jsonify(body), code

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
        particle_profile_json = json.dumps(get_particle_profile(season_type, current_date), ensure_ascii=False)
    except Exception:
        decoration_images = []
        image_version = VERSION
        jst = pytz.timezone('Asia/Tokyo')
        particle_profile_json = json.dumps(
            get_particle_profile(None, datetime.now(jst)), ensure_ascii=False
        )

    app_base_path = '/test' if request.blueprint == 'main_test' else ''

    return render_template('index.html',
                          messages=messages,
                          version=VERSION,
                          username=session.get('username', 'Unknown'),
                          decoration_images=decoration_images,
                          image_version=image_version,
                          app_base_path=app_base_path,
                          particle_profile_json=particle_profile_json)


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

    chat_client = ChatClientInfo.from_flask_request(request)
    client_ip = chat_client.client_ip
    user_agent = chat_client.user_agent
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


def create_main_routes(url_prefix=None, blueprint_name='main'):
    """
    メインルートの Blueprint を作成（ビューは当モジュール内で定義）。

    url_prefix='/test' と blueprint_name='main_test' を指定すると、
    https://example.com/test/ で同一チャット UI を提供する（API はルートのまま）。
    """
    bp = Blueprint(blueprint_name, __name__, url_prefix=url_prefix)
    bp.add_url_rule('/favicon.ico', view_func=favicon)
    bp.add_url_rule('/sitemap.xml', view_func=sitemap, methods=['GET'])
    bp.add_url_rule('/', view_func=index, methods=['GET', 'POST'])
    bp.add_url_rule('/clear', view_func=clear_chat, methods=['POST'])
    bp.add_url_rule('/new_session', view_func=new_session, methods=['POST'])
    return bp
