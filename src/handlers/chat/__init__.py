"""
チャットPOST処理の部品

責務: 入力検証・トリアージ・推奨フロー・カウンセリングフロー・レスポンス組み立て
"""
from src.handlers.chat.chat_input_validator import validate_and_block_input
from src.handlers.chat.chat_response_builder import build_success_response
from src.handlers.chat.chat_triage import run_triage
from src.handlers.chat.chat_counseling_flow import run_counseling_flow
from src.handlers.chat.chat_recommendation_flow import run_recommendation_flow

__all__ = [
    'validate_and_block_input',
    'build_success_response',
    'run_triage',
    'run_counseling_flow',
    'run_recommendation_flow',
]
