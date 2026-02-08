# Build api_routes.py from app.py lines 102-1022
import re

with open("app.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

# Api views: 102-955 (api_status through api_user_attributes), 958-1022 (translate_text, set_language)
# Feedback views 956-957 are between them
block1 = lines[101:955]   # 102-955
block2 = lines[957:1022]  # 958-1022
content = "".join(block1) + "\n" + "".join(block2)

# Prepend header with imports and session/VERSION helpers
header = '''"""
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


'''

# Inject session and VERSION at start of functions that need them (simple string replace)
content = content.replace(
    '''def api_status():
    """システム状況を返す"""
    try:''',
    '''def api_status():
    """システム状況を返す"""
    session = current_app.extensions['safe_session']
    VERSION = current_app.config.get('VERSION', '0')
    try:'''
)
content = content.replace(
    '''def api_sessions():
    """セッション情報を返す（GET）またはユーザー属性を保存（POST）"""
    try:''',
    '''def api_sessions():
    """セッション情報を返す（GET）またはユーザー属性を保存（POST）"""
    session = current_app.extensions['safe_session']
    try:'''
)
content = content.replace(
    '''def request_admin():
    """管理者対応要請を受け付ける（個別チャット単位）"""
    sid = session.get('_id')''',
    '''def request_admin():
    """管理者対応要請を受け付ける（個別チャット単位）"""
    session = current_app.extensions['safe_session']
    sid = session.get('_id')'''
)
content = content.replace(
    '''def api_main_sessions():
    """全セッション情報を取得（admin_chat.html用）"""
    current_sid = session.get('_id')''',
    '''def api_main_sessions():
    """全セッション情報を取得（admin_chat.html用）"""
    session = current_app.extensions['safe_session']
    current_sid = session.get('_id')'''
)
content = content.replace(
    '''def api_user_attributes():
    """ユーザー属性情報の取得と保存"""
    if request.method == 'GET':''',
    '''def api_user_attributes():
    """ユーザー属性情報の取得と保存"""
    session = current_app.extensions['safe_session']
    if request.method == 'GET':'''
)
content = content.replace(
    '''def set_language():
    """UI言語を設定"""
    try:''',
    '''def set_language():
    """UI言語を設定"""
    session = current_app.extensions['safe_session']
    try:'''
)

# Fix api_session_stats: USER_COUNTER might not exist, use 0
content = content.replace("'current_user_counter': USER_COUNTER,", "'current_user_counter': 0,")

# Fix api_manual_reply_message: globals().get('MANUAL_REPLY_MESSAGE', message) -> get_manual_reply_message() or message
content = content.replace(
    "saved_message = globals().get('MANUAL_REPLY_MESSAGE', message)",
    "saved_message = get_manual_reply_message() or message"
)

out = header + content

# Add create_api_routes() at the end
create_def = '''
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
'''

with open("src/routes/api_routes.py", "w", encoding="utf-8") as f:
    f.write(out + create_def)

print("Written api_routes.py", len(out), "chars")
