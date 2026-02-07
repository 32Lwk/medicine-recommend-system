"""
チャットPOSTリクエストハンドラー

index() の POST 処理を委譲し、責務を分離する。
Phase 2.4 の骨格として作成。index() からの委譲は段階的に移行する。
"""


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
        Flask Response (jsonify または redirect)

    Note:
        現時点では app.index() 内で直接処理しているため、本関数は
        将来的な移行先として用意。index() から呼び出す際は:
        if request.method == 'POST':
            from src.handlers.chat_handler import handle_chat_post
            return handle_chat_post(session, request, sid, monitor, client_ip, user_agent)
    """
    # TODO: POST処理を app から移行する
    raise NotImplementedError(
        "handle_chat_post: 処理は app.index() に残置。"
        "移行完了後に実装する。"
    )
