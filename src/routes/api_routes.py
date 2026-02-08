"""
汎用APIルート

責務: status, performance, sessions, ai_control 等の汎用APIルート定義
"""
from flask import Blueprint


def create_api_routes(
    api_status,
    api_performance,
    api_logs,
    api_sessions,
    api_ai_control,
    api_manual_reply_queue,
    api_all_sessions,
    api_session_stats,
    api_debug_manual_replies,
    request_admin,
    api_admin_mode,
    api_main_sessions,
    api_main_manual_reply_queue,
    api_main_ai_control,
    api_manual_reply_message,
    api_user_attributes,
    translate_text,
    set_language,
):
    """
    汎用APIルートのBlueprintを作成

    Returns:
        Blueprint
    """
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
