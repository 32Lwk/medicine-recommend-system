"""
汎用APIルート

責務: status, performance, sessions, ai_control 等の汎用APIルート定義とビュー実装
"""
import json
import math
import os
import time
from datetime import datetime

from flask import Blueprint, current_app, jsonify, request, has_request_context

from config.settings import MAX_SESSIONS, SESSION_TIMEOUT
from src.core.medicine_logic import csv_load_status, client
from src.utils.debug_logger import performance_stats, network_logs, add_network_log
from src.services.database import get_database
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
    cleanup_old_sessions,
    get_admin_sessions,
)
import logging

logger = logging.getLogger(__name__)


def api_status():
    """システム状況を返す"""
    session = current_app.extensions['safe_session']
    VERSION = current_app.config.get('VERSION', '0')
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
    session = current_app.extensions['safe_session']
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
            'current_user_counter': 0,
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

def request_admin():
    """管理者対応要請を受け付ける（個別チャット単位）"""
    session = current_app.extensions['safe_session']
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

def api_main_sessions():
    """全セッション情報を取得（admin_chat.html用）"""
    session = current_app.extensions['safe_session']
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
        saved_message = get_manual_reply_message() or message
        logger.info(f"💾 保存したメッセージを取得 (長さ: {len(saved_message)}): {saved_message[:50]}...")
        
        return jsonify({
            'message': 'メッセージを保存しました',
            'manual_reply_message': saved_message
        })

def api_user_attributes():
    """ユーザー属性情報の取得と保存"""
    session = current_app.extensions['safe_session']
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
    session = current_app.extensions['safe_session']
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

def create_api_routes():
    """汎用APIルートの Blueprint を作成（ビューは当モジュール内で定義）"""
    bp = Blueprint('api', __name__, url_prefix='/api')
    bp.add_url_rule('/status', view_func=api_status)
    bp.add_url_rule('/performance', view_func=api_performance)
    bp.add_url_rule('/logs', view_func=api_logs)
    bp.add_url_rule('/sessions', view_func=api_sessions, methods=['GET', 'POST'])
    bp.add_url_rule('/ai_control', view_func=api_ai_control, methods=['GET', 'POST'])
    bp.add_url_rule('/manual_reply_queue', view_func=api_manual_reply_queue, methods=['GET', 'POST'])
    bp.add_url_rule('/all_sessions', view_func=api_all_sessions)
    bp.add_url_rule('/session_stats', view_func=api_session_stats)
    bp.add_url_rule('/debug_manual_replies', view_func=api_debug_manual_replies)
    bp.add_url_rule('/request_admin', view_func=request_admin, methods=['POST'])
    bp.add_url_rule('/admin_mode', view_func=api_admin_mode, methods=['POST'])
    bp.add_url_rule('/main_sessions', view_func=api_main_sessions)
    bp.add_url_rule('/main_manual_reply_queue', view_func=api_main_manual_reply_queue, methods=['GET', 'POST'])
    bp.add_url_rule('/main_ai_control', view_func=api_main_ai_control, methods=['GET', 'POST'])
    bp.add_url_rule('/manual_reply_message', view_func=api_manual_reply_message, methods=['GET', 'POST'])
    bp.add_url_rule('/user_attributes', view_func=api_user_attributes, methods=['GET', 'POST'])
    bp.add_url_rule('/translate', view_func=translate_text, methods=['POST'])
    bp.add_url_rule('/set_language', view_func=set_language, methods=['POST'])
    return bp
