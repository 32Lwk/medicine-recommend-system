#!/usr/bin/env python3
"""Extract index POST block to chat_handler.handle_chat_post."""
import os

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP_PATH = os.path.join(BASE, 'app.py')
HANDLER_PATH = os.path.join(BASE, 'src', 'handlers', 'chat_handler.py')

with open(APP_PATH, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# POST block: lines 190-7030 (0-indexed: 189-7030)
# Line 190 is "    if request.method == 'POST':"
# Lines 191-7030 are the body (8 spaces base)
START = 189   # 0-indexed, line 190
END = 7030   # 0-indexed, line 7031 (exclusive in slice, so 189:7031 gives 190-7031)

block_lines = lines[START:END + 1]
# First line is "    if request.method == 'POST':" - skip it
# Remaining lines: subtract 4 spaces from each
result_lines = []
for line in block_lines[1:]:  # skip the if line
    if line.strip() == '':
        result_lines.append(line)
    elif len(line) >= 4 and line[:4] == '    ':
        result_lines.append(line[4:])  # remove 4 spaces
    else:
        result_lines.append(line)

impl_body = ''.join(result_lines)

# Build chat_handler.py with required imports
IMPORTS = '''"""
チャットPOSTリクエストハンドラー

index() の POST 処理を委譲し、責務を分離する。
"""

import os
import time
import logging
import uuid
from datetime import datetime

from flask import jsonify, request, has_request_context

from src.utils.request_logger import log_user_interaction
from src.utils.performance_monitor import log_performance_metrics
from src.services.analytics import log_access_analytics
from src.utils.user_attribute_registration import register_user_attributes_from_message
from src.utils.debug_logger import add_network_log
from src.services.session_manager import (
    get_ai_auto_reply,
    get_admin_mode,
    get_manual_reply_queue,
    set_manual_reply_queue,
    get_manual_reply_message,
    get_session_from_db,
    save_session_to_db,
    remove_duplicate_user_messages_after_ai_response,
    get_admin_sessions,
)
from src.core.medicine_logic import client

logger = logging.getLogger(__name__)

def handle_chat_post(session, request, sid, monitor, client_ip, user_agent):
    """
    チャットPOSTリクエストを処理する。

    Args:
        session: Flaskセッションオブジェクト
        request: Flaskのrequestオブジェクト
        sid: セッションID
        monitor: パフォーマンスモニター
        client_ip: クライアントIP
        user_agent: User-Agent

    Returns:
        Flask Response (jsonify)
    """
    ADMIN_SESSIONS = get_admin_sessions()

'''

# Replace ADMIN_SESSIONS in impl_body with the local variable (already ADMIN_SESSIONS in body)
full_content = IMPORTS + impl_body

with open(HANDLER_PATH, 'w', encoding='utf-8') as f:
    f.write(full_content)

print(f"Wrote {HANDLER_PATH}")
print(f"Extracted {len(result_lines)} lines")
