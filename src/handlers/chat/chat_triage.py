"""
チャットトリアージ判定

責務: 緊急・カウンセリング・推奨等の分岐判定。
現状は handle_chat_post 内で実行され、当モジュールはインターフェースを定義。
"""


def run_triage(session, request, sid, user_message, sanitized_message):
    """
    トリアージを実行し、早期リターンすべきレスポンスがあれば返す。
    Returns:
        (early_response or None) - None の場合は後続の推奨/カウンセリングフローへ。
    """
    return None
