"""
チャット推奨フロー実行

責務: 医薬品推奨分岐と medicine_logic 等の呼び出し。
現状は handle_chat_post 内で実行され、当モジュールはインターフェースを定義。
"""


def run_recommendation_flow(session, request, sid, monitor, client_ip, user_agent,
                            sanitized_message, processed_message, triage_result, recommendation_client):
    """
    推奨フローを実行し、レスポンスを返す。
    Returns:
        Flask Response (jsonify)
    """
    return None
