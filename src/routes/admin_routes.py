"""
管理画面・管理APIルート

責務: 管理画面、管理APIのルート定義とビュー実装
"""
import json
import logging
import math
import os
import time
from datetime import datetime

from flask import Blueprint, current_app, jsonify, render_template, request, has_request_context

from config.settings import SESSION_TIMEOUT
from src.core.medicine_logic import (
    csv_load_status,
    select_symptoms_via_gpt,
    comprehensive_medicine_recommendation,
    rule_based_medicine_recommendation,
    analyze_symptoms_and_medicine_type,
)
from src.services.database import get_database
from src.services.session_manager import (
    get_all_sessions_from_db,
    get_manual_reply_queue,
    set_manual_reply_queue,
    get_ai_auto_reply,
    set_ai_auto_reply,
    get_admin_mode,
    get_session_from_db,
    save_session_to_db,
    cleanup_old_sessions,
    get_admin_sessions,
    clear_sessions_fallback,
)
from src.utils.debug_logger import performance_stats, network_logs, add_network_log

logger = logging.getLogger(__name__)


def admin():
    """管理画面（パスワード認証付き）"""
    auth = request.authorization
    admin_password = os.getenv('ADMIN_PASSWORD', 'admin123')
    if not auth or auth.username != 'admin' or auth.password != admin_password:
        return ('認証が必要です', 401, {'WWW-Authenticate': 'Basic realm="Admin Area"'})
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
            except Exception:
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
    data = {
        'access_stats': get_access_statistics(),
        'performance_stats': get_performance_statistics(),
        'export_time': datetime.now().isoformat()
    }
    return jsonify(data)


def clear_logs():
    """ログとセッション履歴をクリア"""
    network_logs.clear()
    db = get_database()
    if db and (db.connection or db.connection_pool):
        all_sessions = get_all_sessions_from_db()
        for sid in all_sessions.keys():
            db.delete_session(sid)
        logger.info("🗑️ All sessions cleared from database")
    else:
        clear_sessions_fallback()
        logger.warning("⚠️ DB unavailable, cleared memory sessions only")
    set_manual_reply_queue([])
    log_file = 'log/recommendation_log.jsonl'
    if os.path.exists(log_file):
        try:
            with open(log_file, 'w', encoding='utf-8') as f:
                pass
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
    return jsonify({'status': 'ok', 'message': message, 'ai_auto_reply': get_ai_auto_reply()})


def _clean_nan(obj):
    """NaN/Infinityを処理"""
    if isinstance(obj, dict):
        return {k: _clean_nan(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_clean_nan(item) for item in obj]
    if isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)):
        return None
    return obj


def admin_medicine_chat():
    """医薬品相談テスト（管理画面用）"""
    data = request.get_json()
    user_message = data.get('message', '').strip()
    if not user_message:
        return jsonify({'status': 'error', 'message': 'メッセージが空です'}), 400
    start_time = time.time()
    try:
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            logger.error("❌ OPENAI_API_KEY が環境変数に設定されていません")
            add_network_log('POST', '管理画面 - 医薬品相談テスト', {'message': user_message}, None, time.time() - start_time, 'failed', 'OpenAI APIキーが設定されていません')
            return jsonify({'status': 'error', 'message': 'OpenAI APIキーが設定されていません', 'error': '環境変数 OPENAI_API_KEY を設定してください'}), 500
        from openai import OpenAI
        test_client = OpenAI(api_key=api_key)
        symptoms_result = select_symptoms_via_gpt(user_message, None, test_client)
        if symptoms_result and symptoms_result.get('status') == 'success':
            symptoms = symptoms_result.get('symptoms', [])
            medicine_type_result = analyze_symptoms_and_medicine_type(user_message, test_client)
            if medicine_type_result and medicine_type_result.get('medicine_type'):
                recommendation = rule_based_medicine_recommendation(user_text=user_message, user_info={}, client=test_client)
                clean_recommendation = _clean_nan(recommendation)
                response_time = time.time() - start_time
                add_network_log('POST', '管理画面 - 医薬品相談テスト', {'message': user_message, 'type': 'rule_based'}, clean_recommendation, response_time, 'success')
                logger.info(f"✅ 医薬品相談テスト成功（ルールベース）: {response_time:.2f}秒")
                return jsonify({'status': 'ok', 'message': '医薬品推奨を実行しました', 'symptoms': symptoms, 'medicine_type': medicine_type_result['medicine_type'], 'recommendation': clean_recommendation})
            else:
                recommendation = comprehensive_medicine_recommendation(user_text=user_message, client=test_client)
                clean_recommendation = _clean_nan(recommendation)
                response_time = time.time() - start_time
                add_network_log('POST', '管理画面 - 医薬品相談テスト', {'message': user_message, 'type': 'ai_based'}, clean_recommendation, response_time, 'success')
                logger.info(f"✅ 医薬品相談テスト成功（AI）: {response_time:.2f}秒")
                return jsonify({'status': 'ok', 'message': '医薬品推奨を実行しました（AI）', 'symptoms': symptoms, 'recommendation': clean_recommendation})
        else:
            return jsonify({'status': 'error', 'message': '症状抽出に失敗しました', 'details': symptoms_result}), 500
    except Exception as e:
        logger.error(f"❌ 医薬品相談テストエラー: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        response_time = time.time() - start_time
        add_network_log('POST', '管理画面 - 医薬品相談テスト', {'message': user_message}, None, response_time, 'failed', str(e))
        return jsonify({'status': 'error', 'message': 'エラーが発生しました', 'error': str(e)}), 500


def get_all_sessions():
    """全セッション情報を取得"""
    session = current_app.extensions['safe_session']
    current_sid = session.get('_id') if has_request_context() else None
    cleanup_old_sessions(force=True, exclude_current_session=True, current_sid=current_sid)
    all_sessions = get_all_sessions_from_db()
    sessions_data = []
    for sid, info in all_sessions.items():
        if info is None or hasattr(info, '_mock_name'):
            continue
        last_activity = info.get('last_activity', 0) if isinstance(info, dict) else 0
        if isinstance(last_activity, datetime):
            last_activity = last_activity.timestamp()
        elif isinstance(last_activity, str):
            try:
                last_activity = datetime.fromisoformat(last_activity.replace('Z', '+00:00')).timestamp()
            except Exception:
                last_activity = 0
        elif not isinstance(last_activity, (int, float)):
            last_activity = 0
        detailed_diag = info.get('detailed_diagnosis') if isinstance(info, dict) else None
        if not detailed_diag:
            detailed_diag = get_admin_sessions().get(sid, {}).get('detailed_diagnosis')
        if isinstance(detailed_diag, dict) and 'session_id' not in detailed_diag:
            try:
                detailed_diag = dict(detailed_diag)
                detailed_diag['session_id'] = str(sid)
            except Exception:
                pass
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
    admin_mode = get_admin_mode()
    ai_auto_reply = get_ai_auto_reply()
    if hasattr(admin_mode, '_mock_name'):
        admin_mode = False
    if hasattr(ai_auto_reply, '_mock_name'):
        ai_auto_reply = True
    return jsonify({'sessions': sessions_data, 'admin_mode': bool(admin_mode), 'ai_auto_reply': bool(ai_auto_reply)})


def delete_session(session_id):
    """セッションを削除"""
    try:
        db = get_database()
        if db and (db.connection or db.connection_pool):
            success = db.delete_session(session_id)
            if success:
                return jsonify({'status': 'success', 'message': 'セッションを削除しました'})
            return jsonify({'status': 'error', 'message': 'セッションが見つかりませんでした'}), 404
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


def create_admin_routes():
    """管理ルートの Blueprint を作成（ビューは当モジュール内で定義）"""
    bp = Blueprint('admin', __name__)
    bp.add_url_rule('/admin', view_func=admin)
    bp.add_url_rule('/admin/system_status', view_func=admin_system_status, methods=['GET'])
    bp.add_url_rule('/admin/access_stats', view_func=admin_access_stats, methods=['GET'])
    bp.add_url_rule('/admin/performance_stats', view_func=admin_performance_stats, methods=['GET'])
    bp.add_url_rule('/admin/browser_distribution', view_func=admin_browser_distribution, methods=['GET'])
    bp.add_url_rule('/admin/os_distribution', view_func=admin_os_distribution, methods=['GET'])
    bp.add_url_rule('/admin/device_distribution', view_func=admin_device_distribution, methods=['GET'])
    bp.add_url_rule('/admin/realtime_monitoring', view_func=admin_realtime_monitoring, methods=['GET'])
    bp.add_url_rule('/admin/export_monitoring_data', view_func=admin_export_monitoring_data, methods=['GET'])
    bp.add_url_rule('/clear_logs', view_func=clear_logs, methods=['POST'])
    bp.add_url_rule('/admin/ai_control', view_func=admin_ai_control, methods=['POST'])
    bp.add_url_rule('/admin/medicine_chat', view_func=admin_medicine_chat, methods=['POST'])
    bp.add_url_rule('/api/admin/sessions', view_func=get_all_sessions, methods=['GET'])
    bp.add_url_rule('/api/admin/sessions/<session_id>', view_func=delete_session, methods=['DELETE'])
    bp.add_url_rule('/api/admin/sessions/delete_all', view_func=delete_all_sessions, methods=['DELETE'])
    bp.add_url_rule('/api/admin/sessions/<session_id>', view_func=update_session, methods=['PUT'])
    bp.add_url_rule('/api/admin/send_message', view_func=admin_send_message, methods=['POST'])
    return bp
