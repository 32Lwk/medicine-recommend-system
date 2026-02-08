"""
チャットカウンセリングフロー実行

責務: カウンセリングモード中の処理（handle_user_input_in_counseling_mode 等の呼び出し）。
現状は handle_chat_post 内で実行され、当モジュールはインターフェースを定義。
"""


def run_counseling_flow(session, request, sid, processed_message, triage_result, recommendation_client):
    """
    カウンセリングモードが有効な場合の処理を実行する。
    Returns:
        Response or None - None の場合は推奨フローへフォールスルー。
    """
    return None
