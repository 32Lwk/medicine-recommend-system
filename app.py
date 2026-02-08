from flask import Flask, render_template, request, jsonify, has_request_context
from flask_cors import CORS
from typing import Dict, List
import json
import time
import os
from datetime import datetime
import random
import logging
import re
import socket

# 環境変数・ログ設定（medicine_logic等より前に実行）
from config.app_config import load_env, configure_logging, get_cors_config, get_session_config

configure_logging()
load_env()
logger = logging.getLogger(__name__)

from config.settings import (
    MAX_SESSIONS,
    SESSION_TIMEOUT,
    CHAT_END_TIMEOUT,
)
from src.core.medicine_logic import get_medicines_by_symptom, csv_load_status
from src.core.medicine_logic import select_symptoms_via_gpt, comprehensive_medicine_recommendation, chat_with_medicine_context
from src.core.medicine_logic import rule_based_medicine_recommendation, analyze_symptoms_and_medicine_type, client
from src.core.medicine_logic import detect_language, extract_user_attributes_multilingual, translate_medicine_recommendation
from src.utils.debug_logger import performance_stats, network_logs, add_network_log
from src.utils.user_attribute_registration import register_user_attributes_from_message
from src.services.analytics import log_access_analytics, get_access_statistics
from src.utils.performance_monitor import get_global_monitor, log_performance_metrics, check_performance_alerts
from src.services.database import init_database, get_database
from src.core.season_manager import get_current_season, get_season_images
from src.utils.request_logger import (
    log_network_request,
    log_medicine_logic_call,
    log_user_interaction,
    log_system_status,
)
from src.utils.input_helpers import (
    is_ambiguous_input,
    check_missing_attributes,
    is_operation_command,
    is_symptom_input,
)
from src.services.chat_response_service import generate_personalized_advice
from src.utils.request_safe_session import RequestSafeSession
from src.handlers.error_handlers import register_error_handlers
from src.services.session_manager import (
    get_ai_auto_reply,
    set_ai_auto_reply,
    get_admin_mode,
    set_admin_mode,
    get_manual_reply_queue,
    set_manual_reply_queue,
    get_manual_reply_message,
    set_manual_reply_message,
    get_session_from_db,
    save_session_to_db,
    get_all_sessions_from_db,
    get_next_user_number,
    find_existing_session,
    update_session_activity,
    cleanup_old_sessions,
    remove_duplicate_user_messages_after_ai_response,
    get_admin_sessions,
)
import pytz


session = RequestSafeSession()

app = Flask(__name__)
app.extensions['safe_session'] = session  # Blueprint用
app.secret_key = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')  # セッション管理用

# CORS・セッション設定
cors_config = get_cors_config()
CORS(app, **cors_config)

session_config = get_session_config()
for key, value in session_config.items():
    app.config[key] = value

# データベース初期化（非同期化）
try:
    if not init_database():
        logger.warning("⚠️ Database initialization failed. Feedback features will be disabled.")
    else:
        logger.info("✅ Database initialized successfully.")
except Exception as e:
    logger.warning(f"⚠️ Database initialization error: {e}. Feedback features will be disabled.")

# キャッシュバスティング用のバージョン番号
VERSION = str(int(time.time()))

# エラーハンドラーを登録
register_error_handlers(app, session, VERSION)

def favicon():
    """favicon.icoの404エラーを防ぐ"""
    return '', 204

def index():
    # datetimeを明示的にインポート（UnboundLocalError対策）
    from datetime import datetime
    
    # パフォーマンス監視開始
    monitor = get_global_monitor()
    monitor.start_monitoring()
    monitor.increment_request()
    
    # 古いセッションをクリーンアップ（定期的に実行）
    current_sid = session.get('_id') if has_request_context() else None
    cleanup_old_sessions(force=False, exclude_current_session=True, current_sid=current_sid)
    
    current_time = time.time()
    client_ip = request.remote_addr
    user_agent = request.headers.get('User-Agent', '')
    
    # セッション初期化（最優先・KeyError対策）
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
    
    # セッションIDの取得または作成
    sid = session.get('_id')
    if not sid:
        # より安定したセッションID生成（マイクロ秒 + ランダム）
        # randomモジュールは15行目でグローバルにインポート済み
        sid = str(int(time.time() * 1000000)) + str(random.randint(100000, 999999))
        session['_id'] = sid
        # 言語設定を初期化
        session['ui_language'] = 'ja'  # UI言語（デフォルトは日本語）
        session['detected_language'] = 'ja'  # 検出された言語（デフォルトは日本語）
        logger.info(f"🆕 新しいセッションIDを作成: {sid}")
    
    # セッションIDの整合性を確認
    all_sessions = get_all_sessions_from_db()
    logger.info(f"🔍 Current session ID: {sid}")
    logger.info(f"🔍 sessions keys: {list(all_sessions.keys())}")
    
    # ユーザー名の設定
    if 'username' not in session:
        # 既存のセッションを検索（同じ人からのアクセスのみ）
        existing_session = find_existing_session(client_ip, user_agent)
        
        if existing_session:
            # 既存のセッションを再利用
            existing_session_data = get_session_from_db(existing_session)
            if existing_session_data:
                session['username'] = existing_session_data.get('username', '')
                session['messages'] = existing_session_data.get('messages', []).copy()
                logger.info(f"🔄 Reusing existing session: {existing_session} for IP: {client_ip}, User: {session['username']}")
        else:
            # 新しいユーザー番号を取得
            user_number = get_next_user_number()
            session['username'] = f'ユーザー{user_number}'
            session['messages'] = []
            logger.info(f"👤 New user created: {session['username']} for IP: {client_ip}, User-Agent: {user_agent[:50]}...")
    else:
        logger.info(f"👤 Existing session accessed: {session['username']} for IP: {client_ip}")
    
    # DBからセッションを復元（Cookieサイズ削減のため）
    if sid:
        session_data = get_session_from_db(sid)
        if session_data:
            # 会話履歴は常に完全な履歴を復元する（管理者要請メッセージのみで上書きしない）
            session['messages'] = session_data.get('messages', []).copy()
            # user_attributes（妊娠・授乳等）をDBから復元（Otherフローで登録した属性を次回以降も利用）
            db_attrs = session_data.get('user_attributes', {})
            if db_attrs:
                current_attrs = session.get('user_attributes', {}) or {}
                merged = {**current_attrs, **db_attrs}
                session['user_attributes'] = merged
            logger.info(f"📥 Session messages restored from DB: {len(session['messages'])} messages (full history)")
    
    # current_messagesは安全に取得
    current_messages = session.get('messages', []).copy()
    
    if request.method == 'POST':
        from src.handlers.chat_handler import handle_chat_post
        return handle_chat_post(session, request, sid, monitor, client_ip, user_agent)

    # GET処理（初期表示）
    # パフォーマンスメトリクスをログに記録
    metrics = monitor.get_metrics()
    log_performance_metrics(monitor, sid, 'GET_request', {
        'user_agent': user_agent,
        'client_ip': client_ip
    })
    
    # アクセス分析ログを記録
    session_data = get_session_from_db(sid) if sid else None
    message_count = len(session_data.get('messages', [])) if session_data else 0
    log_access_analytics(sid, user_agent, client_ip, metrics['response_time_ms'], {
        'username': session.get('username', ''),
        'message_count': message_count
    })
    
    messages = session_data.get('messages', []) if session_data else []
    
    # 季節装飾画像の生成
    try:
        jst = pytz.timezone('Asia/Tokyo')
        current_date = datetime.now(jst)
        season_type = get_current_season(current_date)
        year = current_date.year
        
        decoration_images = []
        if season_type:
            decoration_images = get_season_images(season_type, year, session)
        
        image_version = VERSION
    except Exception as e:
        logger.warning(f"⚠️ 季節画像の生成でエラー: {e}")
        decoration_images = []
        image_version = VERSION
    
    logger.info(f"✅ GET処理完了 - HTML返却: {len(messages)} messages, 装飾画像: {len(decoration_images)}枚")
    return render_template('index.html', 
                         messages=messages, 
                         version=VERSION, 
                         username=session.get('username', 'Unknown'),
                         decoration_images=decoration_images,
                         image_version=image_version)

def clear_chat():
    """チャット履歴をクリア"""
    session['messages'] = []
    session.modified = True
    sid = session.get('_id')
    if sid:
        session_data = get_session_from_db(sid)
        if session_data:
            session_data['messages'] = []
            save_session_to_db(sid, session_data)
    # 「チャットを終了しました。」フラグも消す
    session.pop('chat_ended', None)
    return '', 204

def api_status():
    """システム状況を返す"""
    try:
        # csv_load_statusのpathを文字列として確実に返す
        csv_path = csv_load_status.get('path')
        if csv_path is not None:
            csv_path_str = str(csv_path)
        else:
            csv_path_str = None
            
        status_data = {
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'csv_load_status': {
                'success': csv_load_status.get('success', False),
                'encoding': csv_load_status.get('encoding'),
                'error': csv_load_status.get('error'),
                'row_count': csv_load_status.get('row_count', 0),
                'col_count': csv_load_status.get('col_count', 0),
                'columns': csv_load_status.get('columns', []),
                'path': csv_path_str
            },
            'session_active': 'messages' in session,
            'message_count': len(session.get('messages', [])),
            'version': VERSION
        }
        return jsonify(status_data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def api_performance():
    """パフォーマンス統計を返す"""
    try:
        return jsonify(performance_stats)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def api_logs():
    """通信ログを返す"""
    try:
        # network_logsが配列でない場合は空配列を返す
        if not isinstance(network_logs, list):
            return jsonify([])
        return jsonify(network_logs)
    except Exception as e:
        # エラーの場合も空配列を返す
        return jsonify([])

def api_sessions():
    """セッション情報を返す（GET）またはユーザー属性を保存（POST）"""
    try:
        sid = session.get('_id', 'unknown')
        
        # POSTリクエストの場合：ユーザー属性を保存
        if request.method == 'POST':
            data = request.get_json()
            user_attributes = data.get('user_attributes', {})
            
            if not sid or sid == 'unknown':
                sid = str(int(time.time() * 1000000))
                session['_id'] = sid
                session['username'] = f'ユーザー{get_next_user_number()}'
            
            # セッションとDBの両方にuser_attributesを保存
            session['user_attributes'] = user_attributes
            session.modified = True
            
            session_data = get_session_from_db(sid)
            if not session_data:
                session_data = {
                    'session_id': sid,
                    'username': session.get('username', f'ユーザー{get_next_user_number()}'),
                    'messages': [],
                    'session_active': True,
                    'last_activity': datetime.now(),
                    'client_ip': request.remote_addr,
                    'user_agent': request.headers.get('User-Agent', ''),
                    'user_attributes': user_attributes
                }
            else:
                session_data['user_attributes'] = user_attributes
                session_data['last_activity'] = datetime.now()
            
            save_session_to_db(sid, session_data)
            logger.info(f"💾 ユーザー属性を保存: {sid}")
            return jsonify({'status': 'ok', 'message': 'ユーザー情報を保存しました'})
        
        # GETリクエストの場合：セッション情報を返す
        all_sessions = get_all_sessions_from_db()
        logger.info(f"🔍 /api/sessions called - Session ID: {sid}")
        logger.info(f"🔍 sessions keys: {list(all_sessions.keys())}")
        
        # セッションIDがない場合は新規作成
        if not sid or sid == 'unknown':
            sid = str(int(time.time() * 1000000))
            session['_id'] = sid
            session['username'] = f'ユーザー{get_next_user_number()}'
            logger.info(f"🆕 新しいセッションIDを作成: {sid}")
        
        # DBに存在しない場合は復旧
        session_data = get_session_from_db(sid)
        if not session_data:
            logger.warning(f"⚠️ /api/sessions - セッションIDがDBに存在しません (sid={sid})。セッションから復旧を試みます。")
            session_data = {
                'session_id': sid,
                'username': session.get('username', f'ユーザー{get_next_user_number()}'),
                'messages': session.get('messages', []),
                'session_active': True,
                'last_activity': datetime.now(),
                'client_ip': request.remote_addr,
                'user_agent': request.headers.get('User-Agent', ''),
                'user_attributes': session.get('user_attributes', {})
            }
            save_session_to_db(sid, session_data)
            logger.info(f"🆕 新規セッション作成: {sid}")
        else:
            # 既存セッションの場合はlast_activityのみ更新
            session_data['last_activity'] = datetime.now()
            save_session_to_db(sid, session_data)
            logger.info(f"🔄 既存セッション更新: {sid} ({len(session_data.get('messages', []))} messages)")
        
        # DBから取得（セッションCookieの肥大化を防ぐ）
        messages = session_data.get('messages', [])
        logger.info(f"📦 /api/sessions - DBから取得: {len(messages)} messages (sid={sid})")
        
        # セッションCookie肥大化を防ぐため、messagesをDBのみに保存
        # Flaskセッションからはmessagesを削除
        if 'messages' in session:
            del session['messages']
            session.modified = True
            logger.info(f"📝 Session cookie size reduced - messages only in DB")
        
        # user_attributesを取得（DB/ストアを優先＝非同期抽出結果を確実に反映）
        db_attrs = session_data.get('user_attributes') or {}
        flask_attrs = session.get('user_attributes') or {}
        # DB側が非同期LLM抽出等で更新されるため、DBを優先してマージ
        user_attributes = {**flask_attrs, **db_attrs}
        # マージ結果をストアに反映（モーダル表示の確実な反映のため）
        if user_attributes and session_data.get('user_attributes') != user_attributes:
            session_data['user_attributes'] = user_attributes
            save_session_to_db(sid, session_data)
        
        session_data = {
            'session_id': sid,
            'messages_count': len(messages),
            'last_activity': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'session_active': len(messages) > 0,
            'messages': messages,
            'user_attributes': user_attributes  # user_attributesを追加
        }
        
        # usage_notesを直近のbotレスポンスから抽出
        latest_usage_notes = None
        for msg in reversed(messages):
            if msg.get('type') == 'bot':
                # diagnosisにusage_notesがあれば優先
                diagnosis = msg.get('diagnosis')
                if isinstance(diagnosis, dict) and 'usage_notes' in diagnosis:
                    latest_usage_notes = diagnosis['usage_notes']
                # content直下にusage_notesがあればそれも考慮
                if not latest_usage_notes and 'usage_notes' in msg:
                    latest_usage_notes = msg['usage_notes']
                break
        session_data['latest_usage_notes'] = latest_usage_notes
        
        # NaN値をnullに変換（JSONシリアライズ対応）
        import math
        import json
        
        def convert_nan_to_null(obj):
            """NaN値をnullに変換する再帰関数"""
            if isinstance(obj, dict):
                return {k: convert_nan_to_null(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_nan_to_null(item) for item in obj]
            elif isinstance(obj, float) and math.isnan(obj):
                return None
            else:
                return obj
        
        session_data = convert_nan_to_null(session_data)
        
        logger.info(f"✅ /api/sessions レスポンス: {len(messages)} messages")
        return jsonify(session_data)
    except Exception as e:
        logger.error(f"❌ /api/sessions エラー: {e}")
        return jsonify({'error': str(e)}), 500

def api_ai_control():
    """AI自動応答の制御"""
    if request.method == 'GET':
        return jsonify({
            'ai_auto_reply': get_ai_auto_reply(),
            'manual_reply_queue_count': len(get_manual_reply_queue())
        })
    
    elif request.method == 'POST':
        data = request.get_json()
        mode = data.get('mode')
        
        if mode in ['on', 'off']:
            set_ai_auto_reply(mode == 'on')
            return jsonify({
                'ai_auto_reply': get_ai_auto_reply(),
                'message': f'AI自動応答を{"ON" if get_ai_auto_reply() else "OFF"}にしました'
            })
        else:
            return jsonify({'error': 'Invalid mode. Use "on" or "off"'}), 400
    
    return jsonify({'error': 'Method not allowed'}), 405

def api_manual_reply_queue():
    """手動返信待ちキュー"""
    
    if request.method == 'GET':
        queue = get_manual_reply_queue()
        return jsonify(queue)
    
    elif request.method == 'POST':
        data = request.get_json()
        session_id = data.get('session_id')
        reply_message = data.get('reply_message')
        
        logger.info(f"Manual reply request received: session_id={session_id}, message={reply_message[:50] if reply_message else None}...")
        all_sessions = get_all_sessions_from_db()
        if os.getenv('DEBUG_MODE', 'false').lower() == 'true':
            logger.debug(f"Current session keys: {list(all_sessions.keys())}")
        
        if not session_id or not reply_message:
            return jsonify({'error': 'session_id and reply_message are required'}), 400
        
        # キューから該当するメッセージを削除
        queue = get_manual_reply_queue()
        for i, pending in enumerate(queue):
            if pending['session_id'] == session_id:
                queue.pop(i)
                set_manual_reply_queue(queue)
                logger.info(f"Removed pending message from queue for session {session_id}")
                break
        
        # 指定されたセッションIDのユーザーセッションに返信メッセージを追加
        target_session = get_session_from_db(session_id)
        if target_session:
            if os.getenv('DEBUG_MODE', 'false').lower() == 'true':
                logger.debug(f"Found target session: {target_session.get('session_id', 'unknown')}")
            
            # 返信メッセージを追加
            manual_reply_message = {
                'type': 'bot',
                'content': reply_message,
                'diagnosis': None,
                'manual_reply': True  # 手動返信のフラグ
            }
            
            if 'messages' not in target_session:
                target_session['messages'] = []
            target_session['messages'].append(manual_reply_message)
            target_session['last_activity'] = datetime.now()  # 最終アクティビティを更新
            
            # DBを更新
            save_session_to_db(session_id, target_session)
            
            # ログに記録
            add_network_log(
                'POST',
                'メインサイト - 手動返信',
                {'session_id': session_id, 'reply': reply_message},
                {'status': 'manual_reply_sent'},
                0,
                'success'
            )
            
            logger.info(f"📝 Manual reply sent to session {session_id}: {reply_message}")
            logger.info(f"📝 DB updated: {len(target_session['messages'])} messages")
            logger.info(f"📝 Target session info: {target_session}")
            logger.info(f"📝 Manual reply message added: {manual_reply_message}")
            
            # メインサイトでの反映確認用ログ
            logger.info(f"=== Manual Reply Summary ===")
            logger.info(f"Session ID: {session_id}")
            logger.info(f"Total messages in DB: {len(target_session['messages'])}")
            logger.info(f"Manual reply messages: {len([msg for msg in target_session['messages'] if msg.get('manual_reply')])}")
            logger.info(f"Latest message: {target_session['messages'][-1] if target_session['messages'] else 'None'}")
            logger.info(f"===========================")
            
            return jsonify({
                'message': '手動返信を送信しました',
                'remaining_queue': len(get_manual_reply_queue()),
                'target_session_id': session_id,
                'messages_count': len(target_session['messages']),
                'session_updated': True
            })
        else:
            all_sessions = get_all_sessions_from_db()
            logger.error(f"❌ Session {session_id} not found in DB")
            logger.error(f"❌ Available sessions: {list(all_sessions.keys())}")
            return jsonify({'error': f'Session {session_id} not found'}), 404
    
    return jsonify({'error': 'Method not allowed'}), 405

def api_all_sessions():
    result = []
    all_sessions = get_all_sessions_from_db()
    for sid, info in all_sessions.items():
        result.append({
            'session_id': sid,
            'username': info.get('username', ''),
            'messages': info.get('messages', []),
            'messages_count': len(info.get('messages', []))
        })
    
    # デバッグ用ログ
    logger.info(f"📊 All sessions API called: {len(result)} sessions")
    for session_info in result:
        logger.info(f"📊 Session {session_info['session_id']}: {session_info['messages_count']} messages")
    
    return jsonify(result)

def api_session_stats():
    """セッション管理の統計情報を返す"""
    try:
        current_time = time.time()
        active_sessions = 0
        expired_sessions = 0
        used_user_numbers = set()
        session_details = []
        
        all_sessions = get_all_sessions_from_db()
        for sid, info in all_sessions.items():
            last_activity = info.get('last_activity', 0)
            # last_activityがdatetimeオブジェクトの場合はtimestampに変換
            if isinstance(last_activity, datetime):
                last_activity = last_activity.timestamp()
            elif isinstance(last_activity, str):
                try:
                    last_activity = datetime.fromisoformat(last_activity.replace('Z', '+00:00')).timestamp()
                except:
                    last_activity = 0
            
            if current_time - (last_activity or 0) < SESSION_TIMEOUT:
                active_sessions += 1
                # ユーザー番号を収集
                username = info.get('username', '')
                if username.startswith('ユーザー'):
                    try:
                        number = int(username.replace('ユーザー', ''))
                        used_user_numbers.add(number)
                    except ValueError:
                        pass
                
                # セッション詳細情報を収集
                session_details.append({
                    'session_id': sid,
                    'username': username,
                    'client_ip': info.get('client_ip', ''),
                    'user_agent': info.get('user_agent', '')[:50] + '...' if len(info.get('user_agent', '')) > 50 else info.get('user_agent', ''),
                    'messages_count': len(info.get('messages', [])),
                    'last_activity': datetime.fromtimestamp(last_activity).strftime("%Y-%m-%d %H:%M:%S"),
                    'age_minutes': int((current_time - last_activity) / 60)
                })
            else:
                expired_sessions += 1
        
        stats = {
            'total_sessions': len(all_sessions),
            'active_sessions': active_sessions,
            'expired_sessions': expired_sessions,
            'max_sessions': MAX_SESSIONS,
            'session_timeout': SESSION_TIMEOUT,
            'current_user_counter': USER_COUNTER,
            'used_user_numbers': sorted(list(used_user_numbers)),
            'next_available_number': get_next_user_number(),
            'session_details': session_details,
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        return jsonify(stats)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def api_debug_manual_replies():
    """手動返信のデバッグ情報を返す"""
    try:
        all_sessions = get_all_sessions_from_db()
        queue = get_manual_reply_queue()
        debug_info = {
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'total_sessions': len(all_sessions),
            'sessions_with_manual_replies': [],
            'manual_reply_queue': queue
        }
        
        for sid, info in all_sessions.items():
            manual_replies = [msg for msg in info.get('messages', []) if msg.get('manual_reply')]
            if manual_replies:
                debug_info['sessions_with_manual_replies'].append({
                    'session_id': sid,
                    'username': info.get('username', ''),
                    'manual_replies_count': len(manual_replies),
                    'manual_replies': manual_replies,
                    'total_messages': len(info.get('messages', []))
                })
        
        return jsonify(debug_info)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def new_session():
    """新しいセッションを開始"""
    # 現在のセッション情報をクリア（ユーザーが明示的に新しいセッションを開始した場合のみ）
    session.clear()

    # 新しいセッションIDとユーザー名を割り当て
    sid = str(int(time.time() * 1000)) + str(id(session))
    session['_id'] = sid
    user_number = get_next_user_number()
    session['username'] = f'ユーザー{user_number}'
    session['messages'] = []
    session.modified = True

    # DBに新規登録
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

    return jsonify({'message': '新しいセッションを開始しました', 'username': session['username']}), 200

def request_admin():
    """管理者対応要請を受け付ける（個別チャット単位）"""
    sid = session.get('_id')
    username = session.get('username', 'unknown')
    if sid:
        # セッションに要請フラグとAI自動応答OFFフラグを追加（個別チャット単位）
        session_data = get_session_from_db(sid) or {}

        # 既存セッションが存在しない場合は基本情報を補完
        if not session_data:
            session_data = {
                'session_id': sid,
                'username': username,
                'messages': session.get('messages', []).copy(),
                'last_activity': datetime.now(),
                'client_ip': request.remote_addr,
                'user_agent': request.headers.get('User-Agent', ''),
                'user_attributes': session.get('user_attributes', {}),
                'session_active': True
            }

        session_data['admin_request'] = True
        session_data['ai_auto_reply'] = False  # このチャットのみAI自動応答OFF

        session['admin_request'] = True
        session['ai_auto_reply'] = False  # このチャットのみAI自動応答OFF

        # システムメッセージを追加
        system_message = {
            'type': 'bot',
            'content': '薬剤師対応を要請しました。しばらくお待ちください。',
            'admin_request': True,
            'style_class': 'admin-request'
        }
        if 'messages' not in session:
            session['messages'] = []
        session['messages'].append(system_message)

        # DBにも保存（ページ更新後も表示されるように）
        messages_for_db = session_data.get('messages') or []
        messages_for_db.append(system_message)
        session_data['messages'] = messages_for_db
        session_data['last_activity'] = datetime.now()
        save_session_to_db(sid, session_data)

        session.modified = True
        
        # MANUAL_REPLY_QUEUEに同じセッションIDのadmin_requestがなければ追加
        queue = get_manual_reply_queue()
        already_exists = any(item.get('session_id') == sid and item.get('admin_request') for item in queue)
        if not already_exists:
            queue.append({
                'session_id': sid,
                'username': username,
                'user_message': '【薬剤師要請】' + username,
                'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'status': 'admin_requested',
                'admin_request': True
            })
            set_manual_reply_queue(queue)
        
        logger.info(f"💊 薬剤師要請: {username} (Session: {sid}) - このチャットのみAI自動応答OFF")
        return jsonify({'status': 'ok', 'message': '薬剤師対応を要請しました'})
    return jsonify({'status': 'error', 'message': 'No session'}), 400

def api_admin_mode():
    set_admin_mode(True)
    set_ai_auto_reply(False)
    return jsonify({'admin_mode': get_admin_mode(), 'ai_auto_reply': get_ai_auto_reply(), 'message': '管理者対応モードに切り替えました'})

def admin():
    """管理画面（パスワード認証付き）"""
    # Basic認証のチェック
    auth = request.authorization
    admin_password = os.getenv('ADMIN_PASSWORD', 'admin123')  # デフォルトパスワード
    
    if not auth or auth.username != 'admin' or auth.password != admin_password:
        # 認証が必要
        return ('認証が必要です', 401, {
            'WWW-Authenticate': 'Basic realm="Admin Area"'
        })
    
    return render_template('admin_chat.html')

def admin_system_status():
    """システム状況を取得"""
    all_sessions = get_all_sessions_from_db()
    current_time = time.time()
    active_sessions = 0
    for s in all_sessions.values():
        last_activity = s.get('last_activity', 0)
        if isinstance(last_activity, datetime):
            last_activity = last_activity.timestamp()
        elif isinstance(last_activity, str):
            try:
                last_activity = datetime.fromisoformat(last_activity.replace('Z', '+00:00')).timestamp()
            except:
                last_activity = 0
        if current_time - (last_activity or 0) < SESSION_TIMEOUT:
            active_sessions += 1
    
    return jsonify({
        'status': 'ok',
        'csv_load_status': csv_load_status,
        'total_sessions': len(all_sessions),
        'active_sessions': active_sessions,
        'manual_reply_queue': len(get_manual_reply_queue()),
        'ai_auto_reply': get_ai_auto_reply(),
        'admin_mode': get_admin_mode(),
        'performance_stats': performance_stats
    })

def admin_access_stats():
    """アクセス統計を取得"""
    from src.services.analytics import get_access_statistics
    stats = get_access_statistics()
    return jsonify(stats)

def admin_performance_stats():
    """パフォーマンス統計を取得"""
    from src.utils.performance_monitor import get_performance_statistics
    stats = get_performance_statistics()
    return jsonify(stats)

def admin_browser_distribution():
    """ブラウザ分布を取得"""
    from src.services.analytics import get_browser_distribution
    distribution = get_browser_distribution()
    return jsonify(distribution)

def admin_os_distribution():
    """OS分布を取得"""
    from src.services.analytics import get_os_distribution
    distribution = get_os_distribution()
    return jsonify(distribution)

def admin_device_distribution():
    """デバイス分布を取得"""
    from src.services.analytics import get_device_distribution
    distribution = get_device_distribution()
    return jsonify(distribution)

def admin_realtime_monitoring():
    """リアルタイム監視データを取得"""
    from src.utils.performance_monitor import get_global_monitor
    monitor = get_global_monitor()
    metrics = monitor.get_metrics()
    
    all_sessions = get_all_sessions_from_db()
    return jsonify({
        'memory_usage_percent': metrics.get('memory_usage_percent', 0),
        'cpu_usage_percent': metrics.get('cpu_usage_percent', 0),
        'response_time_ms': metrics.get('response_time_ms', 0),
        'active_sessions': len(all_sessions),
        'api_calls': metrics.get('api_calls', 0),
        'cache_hit_rate': metrics.get('cache_hit_rate', 0)
    })

def admin_export_monitoring_data():
    """監視データをエクスポート"""
    from src.services.analytics import get_access_statistics
    from src.utils.performance_monitor import get_performance_statistics
    import json
    
    data = {
        'access_stats': get_access_statistics(),
        'performance_stats': get_performance_statistics(),
        'export_time': datetime.now().isoformat()
    }
    
    return jsonify(data)

def clear_logs():
    """ログとセッション履歴をクリア"""
    global network_logs
    
    # ネットワークログをクリア
    network_logs.clear()
    
    # すべてのセッションをクリア（管理者が明示的にクリアした場合のみ）
    # 注意: これによりすべてのチャット履歴が削除されます
    db = get_database()
    if db and (db.connection or db.connection_pool):
        # DBからすべてのセッションを削除
        all_sessions = get_all_sessions_from_db()
        for sid in all_sessions.keys():
            db.delete_session(sid)
        logger.info("🗑️ All sessions cleared from database")
    else:
        # フォールバック: メモリから削除
        from src.services.session_manager import clear_sessions_fallback
        clear_sessions_fallback()
        logger.warning("⚠️ DB unavailable, cleared memory sessions only")
    
    # 手動返信待ちキューをクリア
    set_manual_reply_queue([])
    
    # ログファイルもクリア
    log_file = 'log/recommendation_log.jsonl'
    if os.path.exists(log_file):
        try:
            with open(log_file, 'w', encoding='utf-8') as f:
                pass  # ファイルを空にする
            logger.info("📝 ログファイルをクリアしました")
        except Exception as e:
            logger.error(f"❌ ログファイルのクリアに失敗: {e}")
    
    logger.info("🗑️ ログ、セッション履歴、手動返信待ちキューをすべてクリアしました")
    
    return jsonify({'status': 'ok', 'message': 'ログ、セッション履歴、手動返信待ちキューをクリアしました'})

def admin_ai_control():
    """AI自動応答の制御（管理画面用）"""
    data = request.get_json()
    mode = data.get('mode')
    
    if mode == 'on':
        set_ai_auto_reply(True)
        message = 'AI自動応答をONにしました'
    elif mode == 'off':
        set_ai_auto_reply(False)
        message = 'AI自動応答をOFFにしました'
    else:
        return jsonify({'status': 'error', 'message': '無効なモード'}), 400
    
    logger.info(f"🤖 AI自動応答: {mode.upper()} (グローバル設定)")
    
    return jsonify({
        'status': 'ok',
        'message': message,
        'ai_auto_reply': get_ai_auto_reply()
    })

def admin_medicine_chat():
    """医薬品相談テスト（管理画面用）"""
    data = request.get_json()
    user_message = data.get('message', '').strip()
    
    if not user_message:
        return jsonify({'status': 'error', 'message': 'メッセージが空です'}), 400
    
    try:
        start_time = time.time()
        
        # OpenAI APIキーを確認
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            logger.error("❌ OPENAI_API_KEY が環境変数に設定されていません")
            add_network_log(
                'POST',
                '管理画面 - 医薬品相談テスト',
                {'message': user_message},
                None,
                time.time() - start_time,
                'failed',
                'OpenAI APIキーが設定されていません'
            )
            return jsonify({
                'status': 'error',
                'message': 'OpenAI APIキーが設定されていません',
                'error': '環境変数 OPENAI_API_KEY を設定してください'
            }), 500
        
        # OpenAIクライアントを初期化
        from openai import OpenAI
        test_client = OpenAI(api_key=api_key)
        logger.info(f"✅ OpenAIクライアント初期化成功（医薬品相談テスト用）")
        
        # 症状抽出を実行
        from src.core.medicine_logic import select_symptoms_via_gpt
        symptoms_result = select_symptoms_via_gpt(user_message, None, test_client)
        
        # 医薬品推奨を実行
        if symptoms_result and symptoms_result.get('status') == 'success':
            symptoms = symptoms_result.get('symptoms', [])
            
            # ルールベース推奨を試行
            from src.core.medicine_logic import analyze_symptoms_and_medicine_type
            medicine_type_result = analyze_symptoms_and_medicine_type(user_message, test_client)
            
            if medicine_type_result and medicine_type_result.get('medicine_type'):
                medicine_type = medicine_type_result['medicine_type']
                
                # ルールベース推奨
                from src.core.medicine_logic import rule_based_medicine_recommendation
                recommendation = rule_based_medicine_recommendation(
                    user_text=user_message,
                    user_info={},
                    client=test_client
                )
                
                # NaN値を処理してJSON互換にする
                import json
                import math
                
                def clean_nan(obj):
                    """NaN/Infinityを処理"""
                    if isinstance(obj, dict):
                        return {k: clean_nan(v) for k, v in obj.items()}
                    elif isinstance(obj, list):
                        return [clean_nan(item) for item in obj]
                    elif isinstance(obj, float):
                        if math.isnan(obj) or math.isinf(obj):
                            return None
                        return obj
                    return obj
                
                clean_recommendation = clean_nan(recommendation)
                
                # パフォーマンス統計を更新
                response_time = time.time() - start_time
                add_network_log(
                    'POST',
                    '管理画面 - 医薬品相談テスト',
                    {'message': user_message, 'type': 'rule_based'},
                    clean_recommendation,
                    response_time,
                    'success'
                )
                
                logger.info(f"✅ 医薬品相談テスト成功（ルールベース）: {response_time:.2f}秒")
                
                return jsonify({
                    'status': 'ok',
                    'message': '医薬品推奨を実行しました',
                    'symptoms': symptoms,
                    'medicine_type': medicine_type,
                    'recommendation': clean_recommendation
                })
            else:
                # AI推奨
                from src.core.medicine_logic import comprehensive_medicine_recommendation
                recommendation = comprehensive_medicine_recommendation(
                    user_text=user_message,
                    client=test_client
                )
                
                # NaN値を処理してJSON互換にする
                import json
                import math
                
                def clean_nan(obj):
                    """NaN/Infinityを処理"""
                    if isinstance(obj, dict):
                        return {k: clean_nan(v) for k, v in obj.items()}
                    elif isinstance(obj, list):
                        return [clean_nan(item) for item in obj]
                    elif isinstance(obj, float):
                        if math.isnan(obj) or math.isinf(obj):
                            return None
                        return obj
                    return obj
                
                clean_recommendation = clean_nan(recommendation)
                
                # パフォーマンス統計を更新
                response_time = time.time() - start_time
                add_network_log(
                    'POST',
                    '管理画面 - 医薬品相談テスト',
                    {'message': user_message, 'type': 'ai_based'},
                    clean_recommendation,
                    response_time,
                    'success'
                )
                
                logger.info(f"✅ 医薬品相談テスト成功（AI）: {response_time:.2f}秒")
                
                return jsonify({
                    'status': 'ok',
                    'message': '医薬品推奨を実行しました（AI）',
                    'symptoms': symptoms,
                    'recommendation': clean_recommendation
                })
        else:
            return jsonify({
                'status': 'error',
                'message': '症状抽出に失敗しました',
                'details': symptoms_result
            }), 500
            
    except Exception as e:
        logger.error(f"❌ 医薬品相談テストエラー: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        
        # エラー時もパフォーマンス統計を更新
        response_time = time.time() - start_time if 'start_time' in locals() else 0
        add_network_log(
            'POST',
            '管理画面 - 医薬品相談テスト',
            {'message': user_message},
            None,
            response_time,
            'failed',
            str(e)
        )
        
        return jsonify({
            'status': 'error',
            'message': 'エラーが発生しました',
            'error': str(e)
        }), 500

def get_all_sessions():
    """全セッション情報を取得"""
    current_sid = session.get('_id') if has_request_context() else None
    cleanup_old_sessions(force=True, exclude_current_session=True, current_sid=current_sid)
    
    all_sessions = get_all_sessions_from_db()
    sessions_data = []
    for sid, info in all_sessions.items():
        # infoがNoneまたはMockオブジェクトの場合はスキップ
        if info is None or hasattr(info, '_mock_name'):
            continue
            
        last_activity = info.get('last_activity', 0) if isinstance(info, dict) else 0
        if isinstance(last_activity, datetime):
            last_activity = last_activity.timestamp()
        elif isinstance(last_activity, str):
            try:
                last_activity = datetime.fromisoformat(last_activity.replace('Z', '+00:00')).timestamp()
            except:
                last_activity = 0
        elif not isinstance(last_activity, (int, float)):
            last_activity = 0
        
        # 詳細診断情報を取得（DBから優先、なければget_admin_sessions()から）
        detailed_diag = info.get('detailed_diagnosis') if isinstance(info, dict) else None
        if not detailed_diag:
            detailed_diag = get_admin_sessions().get(sid, {}).get('detailed_diagnosis')
        # 互換対応: detailed_diagnosis に session_id が無ければ付与
        if isinstance(detailed_diag, dict) and 'session_id' not in detailed_diag:
            try:
                detailed_diag = dict(detailed_diag)
                detailed_diag['session_id'] = str(sid)
            except Exception:
                pass
        
        # セッションデータをシリアライズ可能な形式に変換
        session_dict = {
            'session_id': str(sid),
            'username': str(info.get('username', 'Unknown')) if isinstance(info, dict) else 'Unknown',
            'messages': list(info.get('messages', [])) if isinstance(info, dict) and isinstance(info.get('messages'), list) else [],
            'last_activity': float(last_activity),
            'session_active': bool(info.get('session_active', True)) if isinstance(info, dict) else True,
            'client_ip': str(info.get('client_ip', '')) if isinstance(info, dict) else '',
            'user_agent': str(info.get('user_agent', '')) if isinstance(info, dict) else '',
            'user_attributes': dict(info.get('user_attributes', {})) if isinstance(info, dict) and isinstance(info.get('user_attributes'), dict) else {},
            'detailed_diagnosis': detailed_diag
        }
        sessions_data.append(session_dict)
    
    # グローバル状態を取得（Mockオブジェクトの場合はboolに変換）
    admin_mode = get_admin_mode()
    ai_auto_reply = get_ai_auto_reply()
    
    # Mockオブジェクトの場合はデフォルト値を使用
    if hasattr(admin_mode, '_mock_name'):
        admin_mode = False
    if hasattr(ai_auto_reply, '_mock_name'):
        ai_auto_reply = True
    
    return jsonify({
        'sessions': sessions_data,
        'admin_mode': bool(admin_mode),
        'ai_auto_reply': bool(ai_auto_reply)
    })

def delete_session(session_id):
    """セッションを削除"""
    try:
        db = get_database()
        if db and (db.connection or db.connection_pool):
            success = db.delete_session(session_id)
            if success:
                return jsonify({'status': 'success', 'message': 'セッションを削除しました'})
            else:
                return jsonify({'status': 'error', 'message': 'セッションが見つかりませんでした'}), 404
        else:
            return jsonify({'status': 'error', 'message': 'データベース接続エラー'}), 500
    except Exception as e:
        logger.error(f"❌ セッション削除エラー: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

def delete_all_sessions():
    """全セッションを削除"""
    try:
        db = get_database()
        if db and (db.connection or db.connection_pool):
            deleted_count = db.delete_all_sessions()
            return jsonify({'status': 'success', 'message': f'{deleted_count}件のセッションを削除しました', 'deleted_count': deleted_count})
        else:
            return jsonify({'status': 'error', 'message': 'データベース接続エラー'}), 500
    except Exception as e:
        logger.error(f"❌ 全セッション削除エラー: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

def update_session(session_id):
    """セッション情報を更新"""
    try:
        data = request.json
        session_data = get_session_from_db(session_id)
        if not session_data:
            return jsonify({'status': 'error', 'message': 'セッションが見つかりませんでした'}), 404
        
        # 更新可能なフィールド
        if 'username' in data:
            session_data['username'] = data['username']
        if 'session_active' in data:
            session_data['session_active'] = data['session_active']
        if 'user_attributes' in data:
            session_data['user_attributes'] = data['user_attributes']
        
        session_data['last_activity'] = datetime.now()
        
        success = save_session_to_db(session_id, session_data)
        if success:
            return jsonify({'status': 'success', 'message': 'セッション情報を更新しました'})
        else:
            return jsonify({'status': 'error', 'message': 'セッション更新に失敗しました'}), 500
    except Exception as e:
        logger.error(f"❌ セッション更新エラー: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

def admin_send_message():
    """管理者からのメッセージ送信"""
    data = request.json
    session_id = data.get('session_id')
    message = data.get('message')
    
    if not session_id or not message:
        return jsonify({'status': 'error', 'message': 'session_idとmessageが必要です'}), 400
    
    session_data = get_session_from_db(session_id)
    if not session_data:
        return jsonify({'status': 'error', 'message': 'セッションが見つかりません'}), 404
    
    # 管理者メッセージを追加
    ai_response = {
        'role': 'ai',
        'content': message,
        'timestamp': datetime.now().isoformat(),
        'from_admin': True
    }
    
    if 'messages' not in session_data:
        session_data['messages'] = []
    session_data['messages'].append(ai_response)
    session_data['last_activity'] = datetime.now()
    save_session_to_db(session_id, session_data)
    
    return jsonify({'status': 'success', 'message': 'メッセージを送信しました'})

def api_main_sessions():
    """全セッション情報を取得（admin_chat.html用）"""
    current_sid = session.get('_id') if has_request_context() else None
    cleanup_old_sessions(force=True, exclude_current_session=True, current_sid=current_sid)
    
    all_sessions = get_all_sessions_from_db()
    sessions_list = []
    for sid, info in all_sessions.items():
        # まずDBから詳細診断情報を取得、なければget_admin_sessions()から取得
        detailed_diag = info.get('detailed_diagnosis') if isinstance(info, dict) else None
        if not detailed_diag:
            detailed_diag = get_admin_sessions().get(sid, {}).get('detailed_diagnosis')
        # 互換対応: detailed_diagnosis に session_id が無ければ付与（フロントの一致判定用）
        if isinstance(detailed_diag, dict) and 'session_id' not in detailed_diag:
            try:
                detailed_diag = dict(detailed_diag)
                detailed_diag['session_id'] = sid
            except Exception:
                pass
        sessions_list.append({
            'session_id': sid,
            'username': info.get('username', 'Unknown'),
            'messages': info.get('messages', []),
            'last_activity': info.get('last_activity', 0),
            'message_count': len(info.get('messages', [])),
            'user_info': info.get('user_attributes', {}),
            'attributes': info.get('user_attributes', {}),
            # 管理者向けに詳細な診断情報（スコア内訳を含む）も返す
            'detailed_diagnosis': detailed_diag
        })
    
    # NaN値をnullに変換（JSONシリアライズ対応）
    import math
    import json
    
    def convert_nan_to_null(obj):
        """NaN値をnullに変換する再帰関数"""
        if isinstance(obj, dict):
            return {k: convert_nan_to_null(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [convert_nan_to_null(item) for item in obj]
        elif isinstance(obj, float) and math.isnan(obj):
            return None
        else:
            return obj
    
    sessions_list = convert_nan_to_null(sessions_list)

    return jsonify({'sessions': sessions_list})

def api_main_manual_reply_queue():
    """手動返信キューの管理"""
    
    if request.method == 'GET':
        queue = get_manual_reply_queue()
        return jsonify(queue)
    
    elif request.method == 'POST':
        data = request.json
        action = data.get('action')
        session_id = data.get('session_id')
        
        logger.info(f"📥 Manual reply queue POST request: action={action}, session_id={session_id}, data_keys={list(data.keys())}")
        
        # actionが指定されていない場合は、reply_messageの有無で判断
        if not action:
            if data.get('reply_message'):
                action = 'reply'
                logger.info(f"🔄 Action auto-detected as 'reply' from reply_message")
        
        queue = get_manual_reply_queue()
        
        if action == 'add':
            session_id = data.get('session_id')
            if session_id:
                session_data = get_session_from_db(session_id)
                if session_data:
                    # キューに追加（既存のキュー形式に合わせる）
                    queue_item = {
                        'session_id': session_id,
                        'user_message': '',
                        'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        'status': 'pending'
                    }
                    if queue_item not in queue:
                        queue.append(queue_item)
                        set_manual_reply_queue(queue)
                return jsonify({'status': 'success', 'queue': get_manual_reply_queue()})
        
        elif action == 'remove':
            session_id = data.get('session_id')
            if session_id:
                queue = [q for q in queue if q.get('session_id') != session_id]
                set_manual_reply_queue(queue)
            return jsonify({'status': 'success', 'queue': get_manual_reply_queue()})
        
        elif action == 'reply':
            # reply_messageとmessageの両方をサポート
            message = data.get('reply_message') or data.get('message')
            
            if session_id and message:
                session_data = get_session_from_db(session_id)
                if session_data:
                    # 管理者メッセージを追加（manual_replyフラグを使用）
                    manual_reply = {
                        'type': 'bot',
                        'content': message,
                        'timestamp': datetime.now().isoformat(),
                        'manual_reply': True
                    }
                    
                    if 'messages' not in session_data:
                        session_data['messages'] = []
                    session_data['messages'].append(manual_reply)
                    session_data['last_activity'] = datetime.now()
                    save_session_to_db(session_id, session_data)
                    
                    logger.info(f"💬 Manual reply sent to session {session_id}: {message[:50]}...")
                    
                    # キューから削除
                    queue = [q for q in queue if q.get('session_id') != session_id]
                    set_manual_reply_queue(queue)
                    
                    return jsonify({'status': 'success', 'message': 'メッセージを送信しました'})
        
        return jsonify({'status': 'error', 'message': '無効なアクションです'}), 400

def api_main_ai_control():
    """AI自動応答の制御"""
    
    if request.method == 'GET':
        return jsonify({
            'ai_auto_reply': get_ai_auto_reply(),
            'admin_mode': get_admin_mode(),
            'manual_reply_message': get_manual_reply_message()
        })
    
    elif request.method == 'POST':
        data = request.json
        action = data.get('action')
        mode = data.get('mode')  # 'auto'/'manual' または 'on'/'off' に対応
        
        # 'on'/'off'を'auto'/'manual'に変換（後方互換性のため）
        if mode == 'on':
            mode = 'auto'
        elif mode == 'off':
            mode = 'manual'
        
        # modeパラメータがある場合はそれを使用（後方互換性のためactionも対応）
        if mode == 'auto' or action == 'enable':
            set_ai_auto_reply(True)
            set_admin_mode(False)
            message = 'AI自動応答を有効化しました'
        elif mode == 'manual' or action == 'disable':
            set_ai_auto_reply(False)
            set_admin_mode(True)
            message = 'AI自動応答を無効化しました'
        else:
            return jsonify({'error': '無効なパラメータです'}), 400
        
        return jsonify({
            'ai_auto_reply': get_ai_auto_reply(),
            'admin_mode': get_admin_mode(),
            'message': message,
            'manual_reply_message': get_manual_reply_message()
        })

def api_manual_reply_message():
    """手動返信時の自動メッセージの取得・保存"""
    
    if request.method == 'GET':
        return jsonify({
            'message': get_manual_reply_message()
        })
    
    elif request.method == 'POST':
        data = request.json
        message = data.get('message', '').strip()
        
        if not message:
            return jsonify({'error': 'メッセージが空です'}), 400
        
        # メッセージを保存
        set_manual_reply_message(message)
        logger.info(f"💾 手動返信メッセージを更新 (長さ: {len(message)}): {message[:50]}...")
        
        # 保存した値を確実に取得（globals()から直接取得、なければ保存したmessageを使用）
        saved_message = globals().get('MANUAL_REPLY_MESSAGE', message)
        logger.info(f"💾 保存したメッセージを取得 (長さ: {len(saved_message)}): {saved_message[:50]}...")
        
        return jsonify({
            'message': 'メッセージを保存しました',
            'manual_reply_message': saved_message
        })

def api_user_attributes():
    """ユーザー属性情報の取得と保存"""
    if request.method == 'GET':
        # 現在のセッションのユーザー属性を返す
        user_attributes = session.get('user_attributes', {
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
        logger.info(f"📊 GET /api/user_attributes: {user_attributes}")
        return jsonify(user_attributes)
    
    elif request.method == 'POST':
        # ユーザー属性を保存
        data = request.json
        logger.info(f"💾 POST /api/user_attributes: {data}")
        
        sid = session.get('_id')
        
        # セッションに保存
        session['user_attributes'] = {
            'age': data.get('age'),
            'gender': data.get('gender'),
            'pregnant': data.get('pregnant'),
            'breastfeeding': data.get('breastfeeding'),
            'current_medications': data.get('current_medications', []),
            'allergies': data.get('allergies', []),
            'medical_history': data.get('medical_history', []),
            'symptom_duration_days': data.get('symptom_duration_days'),
            'other_info': data.get('other_info')
        }
        session.modified = True
        
        # DBにも保存
        if sid:
            session_data = get_session_from_db(sid)
            if session_data:
                session_data['user_attributes'] = session['user_attributes'].copy()
                session_data['last_activity'] = datetime.now()
                save_session_to_db(sid, session_data)
                logger.info(f"✅ User attributes saved to session {sid}")
        
        return jsonify({'status': 'success', 'message': 'ユーザー属性を保存しました'})

# フィードバック関連API
def submit_feedback():
    """フィードバックをデータベースに保存"""
    try:
        data = request.json
        logger.info(f"📝 Feedback submission: {data}")
        
        # データベース接続確認
        db = get_database()
        if not (db and (db.connection or db.connection_pool)):
            return jsonify({'error': 'Database not available'}), 500
        
        # 必須フィールドの検証
        required_fields = ['report_type', 'user_message', 'ai_response']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # レート制限チェック（同一セッションから60秒に1回まで）
        session_id = session.get('_id')
        if session_id:
            # 簡易的なレート制限（実際の実装ではRedis等を使用）
            current_time = time.time()
            last_feedback_time = session.get('last_feedback_time', 0)
            if current_time - last_feedback_time < 60:
                return jsonify({'error': 'Rate limit exceeded. Please wait 60 seconds.'}), 429
            session['last_feedback_time'] = current_time
        
        # フィードバックテキストの文字数制限
        feedback_text = data.get('feedback_text', '')
        if len(feedback_text) > 1000:
            return jsonify({'error': 'Feedback text too long (max 1000 characters)'}), 400
        
        # データベースに保存
        feedback_id = db.insert_feedback(
            report_type=data['report_type'],
            session_id=session_id,
            username=session.get('username', 'Unknown'),
            user_message=data['user_message'],
            ai_response=data['ai_response'],
            security_score=data.get('security_score'),
            feedback_text=feedback_text,
            is_google_form=data.get('is_google_form', False)
        )
        
        if feedback_id:
            logger.info(f"✅ Feedback saved with ID: {feedback_id}")
            
            # 不適切評価（negative_feedback）の場合、会話履歴を含むログを出力
            if data.get('report_type') == 'negative_feedback' and session_id:
                try:
                    from src.utils.structured_logger import log_counseling_detail
                    # 会話履歴を取得（最新10件）
                    messages = session.get('messages', [])
                    conversation_history = messages[-10:] if len(messages) > 10 else messages
                    
                    log_counseling_detail(
                        session_id=session_id,
                        user_input=data.get('user_message', ''),
                        response=data.get('ai_response', ''),
                        conversation_history=conversation_history
                    )
                    logger.info(f"📝 不適切評価ログ記録完了 [session_id: {session_id}, feedback_id: {feedback_id}]")
                except Exception as log_error:
                    logger.warning(f"不適切評価ログ記録エラー: {log_error}")
            
            return jsonify({'status': 'success', 'feedback_id': feedback_id})
        else:
            return jsonify({'error': 'Failed to save feedback'}), 500
            
    except Exception as e:
        logger.error(f"❌ Feedback submission error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

def get_feedback_reports():
    """フィードバック報告一覧を取得（管理画面用）"""
    try:
        db = get_database()
        if not (db and (db.connection or db.connection_pool)):
            return jsonify({'error': 'Database not available'}), 500
        
        # クエリパラメータ
        limit = request.args.get('limit', 100, type=int)
        unresolved_only = request.args.get('unresolved_only', 'false').lower() == 'true'
        
        reports = db.get_feedback_reports(limit=limit, unresolved_only=unresolved_only)
        
        logger.info(f"📊 Retrieved {len(reports)} feedback reports")
        return jsonify({'reports': reports})
        
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        logger.error(f"❌ Get feedback reports error: {str(e)}")
        logger.error(f"❌ Traceback: {error_trace}")
        return jsonify({'error': f'Internal server error: {str(e)}'}), 500

def resolve_feedback(feedback_id):
    """フィードバックを解決済みにマーク"""
    try:
        db = get_database()
        if not (db and (db.connection or db.connection_pool)):
            return jsonify({'error': 'Database not available'}), 500
        
        success = db.resolve_feedback(feedback_id)
        
        if success:
            logger.info(f"✅ Feedback {feedback_id} marked as resolved")
            return jsonify({'status': 'success'})
        else:
            return jsonify({'error': 'Failed to resolve feedback'}), 500
            
    except Exception as e:
        logger.error(f"❌ Resolve feedback error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

def delete_feedback(feedback_id):
    """フィードバックを削除"""
    try:
        db = get_database()
        if not (db and (db.connection or db.connection_pool)):
            return jsonify({'error': 'Database not available'}), 500

        success = db.delete_feedback(feedback_id)

        if success:
            logger.info(f"🗑️ Feedback {feedback_id} deleted")
            return jsonify({'status': 'success'})
        else:
            return jsonify({'error': 'Failed to delete feedback'}), 500

    except Exception as e:
        logger.error(f"❌ Delete feedback error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

def translate_text():
    """テキスト翻訳API"""
    try:
        data = request.get_json()
        text = data.get('text', '')
        target_language = data.get('target_language', 'ja')
        
        if not text:
            return jsonify({'error': 'No text provided'}), 400
        
        # ChatGPTを使用して翻訳
        translation_prompt = f"""
以下の医薬品関連情報を{target_language}に翻訳してください。医療専門用語は正確に翻訳し、医薬品名は適切に翻訳してください。

翻訳対象テキスト:
{text}

翻訳:
"""
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a medical translator specializing in medicine recommendations. Translate accurately while maintaining medical terminology."},
                {"role": "user", "content": translation_prompt}
            ],
            temperature=0.1,
            max_tokens=2000
        )
        
        translated_text = response.choices[0].message.content.strip()
        
        return jsonify({
            'translated_text': translated_text,
            'original_text': text,
            'target_language': target_language
        })
        
    except Exception as e:
        logger.error(f"翻訳エラー: {e}")
        return jsonify({'error': 'Translation failed'}), 500

def set_language():
    """UI言語を設定"""
    try:
        data = request.get_json()
        language = data.get('language', 'ja')
        
        if language not in ['ja', 'en', 'ko', 'zh']:
            return jsonify({'error': 'Invalid language code'}), 400
        
        # セッションにUI言語を保存
        session['ui_language'] = language
        session.modified = True
        
        logger.info(f"🌍 UI言語を設定: {language}")
        
        return jsonify({
            'status': 'success',
            'language': language,
            'message': f'Language set to {language}'
        })
        
    except Exception as e:
        logger.error(f"言語設定エラー: {e}")
        return jsonify({'error': 'Failed to set language'}), 500

# Blueprint登録
from src.routes import create_main_routes, create_admin_routes, create_api_routes, create_feedback_routes

app.register_blueprint(create_main_routes(favicon, index, clear_chat, new_session))
app.register_blueprint(create_admin_routes(
    admin, admin_system_status, admin_access_stats, admin_performance_stats,
    admin_browser_distribution, admin_os_distribution, admin_device_distribution,
    admin_realtime_monitoring, admin_export_monitoring_data, clear_logs,
    admin_ai_control, admin_medicine_chat, get_all_sessions, delete_session,
    delete_all_sessions, update_session, admin_send_message,
))
app.register_blueprint(create_api_routes(
    api_status, api_performance, api_logs, api_sessions, api_ai_control,
    api_manual_reply_queue, api_all_sessions, api_session_stats, api_debug_manual_replies,
    request_admin, api_admin_mode, api_main_sessions, api_main_manual_reply_queue,
    api_main_ai_control, api_manual_reply_message, api_user_attributes,
    translate_text, set_language,
))
app.register_blueprint(create_feedback_routes(
    submit_feedback, get_feedback_reports, resolve_feedback, delete_feedback,
))

if __name__ == '__main__':
    from src.utils.port_utils import find_free_port, is_port_in_use

    logger.info("🚀 Starting Medicine Recommendation System...")
    
    # 方言変換リソースの初期化（アプリ起動時に一度だけ実行）
    try:
        from src.core.scoring_utils import initialize_dialect_resources
        initialize_dialect_resources()
    except Exception as e:
        logger.warning(f"⚠️ 方言変換リソースの初期化に失敗: {e}")
        import traceback
        traceback.print_exc()
    
    # 最小限のログ出力で起動時間を短縮
    requested_port = int(os.getenv('PORT', 5000))
    debug_mode = os.getenv('FLASK_ENV') != 'production'
    
    # ポートが使用中の場合は、利用可能なポートを探す
    if is_port_in_use(requested_port):
        logger.warning(f"⚠️ Port {requested_port} is already in use. Finding alternative port...")
        port = find_free_port(requested_port + 1)
        logger.info(f"✅ Found available port: {port}")
    else:
        port = requested_port
    
    logger.info(f"🌐 Starting Flask server on port {port} (debug={debug_mode})...")
    app.run(debug=debug_mode, port=port, host='0.0.0.0')