"""
リクエスト・ロジック呼び出しのログ出力モジュール
"""
import logging

logger = logging.getLogger(__name__)


def log_network_request(method, endpoint, request_data, response_data, response_time, status):
    """ネットワークリクエストをログ出力"""
    logger.info(f"🌐 NETWORK REQUEST:")
    logger.info(f"   Method: {method}")
    logger.info(f"   Endpoint: {endpoint}")
    logger.info(f"   Request Data: {request_data}")
    logger.info(f"   Response Time: {response_time}s")
    logger.info(f"   Status: {status}")
    if response_data:
        logger.info(f"   Response Data: {response_data}")


def log_medicine_logic_call(function_name, input_data, output_data, execution_time=None):
    """medicine_logic.pyの関数呼び出しをログ出力"""
    logger.info(f"💊 MEDICINE_LOGIC CALL:")
    logger.info(f"   Function: {function_name}")
    logger.info(f"   Input: {input_data}")
    if execution_time:
        logger.info(f"   Execution Time: {execution_time}s")
    logger.info(f"   Output: {output_data}")


def log_user_interaction(user_message, response_type, session_id, username):
    """ユーザーインタラクションをログ出力"""
    logger.info(f"👤 USER INTERACTION:")
    logger.info(f"   Session ID: {session_id}")
    logger.info(f"   Username: {username}")
    logger.info(f"   User Message: {user_message}")
    logger.info(f"   Response Type: {response_type}")


def log_system_status():
    """システムステータスをログ出力"""
    from src.services.session_manager import (
        get_all_sessions_from_db,
        get_ai_auto_reply,
        get_admin_mode,
        get_manual_reply_queue,
    )
    all_sessions = get_all_sessions_from_db()
    logger.info(f"📊 SYSTEM STATUS:")
    logger.info(f"   Active Sessions: {len(all_sessions)}")
    logger.info(f"   AI Auto Reply: {get_ai_auto_reply()}")
    logger.info(f"   Admin Mode: {get_admin_mode()}")
    logger.info(f"   Manual Reply Queue: {len(get_manual_reply_queue())}")
