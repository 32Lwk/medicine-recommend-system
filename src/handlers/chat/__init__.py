"""
チャットPOST処理の部品

責務: 入力検証・トリアージ・推奨フロー・カウンセリングフロー・
手動返信・緊急・診断名・店舗案内・レスポンス組み立て
"""
from src.handlers.chat.chat_input_validator import validate_and_block_input
from src.handlers.chat.chat_response_builder import build_success_response
from src.handlers.chat.chat_triage import run_triage
from src.handlers.chat.chat_counseling_flow import run_counseling_flow
from src.handlers.chat.chat_recommendation_flow import run_recommendation_flow
from src.handlers.chat.chat_manual_reply import handle_manual_reply_when_off
from src.handlers.chat.chat_emergency_handler import handle_emergency_if_detected
from src.handlers.chat.chat_diagnosis_handler import handle_diagnosis_if_detected
from src.handlers.chat.chat_store_inquiry import handle_store_inquiry_response

__all__ = [
    'validate_and_block_input',
    'build_success_response',
    'run_triage',
    'run_counseling_flow',
    'run_recommendation_flow',
    'handle_manual_reply_when_off',
    'handle_emergency_if_detected',
    'handle_diagnosis_if_detected',
    'handle_store_inquiry_response',
]
