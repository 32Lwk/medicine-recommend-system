"""
チャットJSONレスポンスの組み立て

責務: 共通の成功レスポンス等の組み立て
"""
def build_success_response(session, message_count=None):
    """
    POST成功時の共通JSONレスポンスを組み立てる。
    """
    if message_count is None:
        message_count = len(session.get('messages', []))
    return {'status': 'ok', 'message_count': message_count}, 200
