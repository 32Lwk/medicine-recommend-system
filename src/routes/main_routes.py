"""
メイン画面・チャットルート

責務: メイン画面（index）、favicon、clear のルート定義
"""
from flask import Blueprint


def create_main_routes(favicon, index, clear_chat, new_session):
    """
    メインルートのBlueprintを作成

    Args:
        favicon: faviconハンドラー
        index: index（メイン画面）ハンドラー
        clear_chat: チャットクリアハンドラー
        new_session: 新規セッション作成ハンドラー

    Returns:
        Blueprint
    """
    bp = Blueprint('main', __name__)
    bp.add_url_rule('/favicon.ico', view_func=favicon)
    bp.add_url_rule('/', view_func=index, methods=['GET', 'POST'])
    bp.add_url_rule('/clear', view_func=clear_chat, methods=['POST'])
    bp.add_url_rule('/new_session', view_func=new_session, methods=['POST'])
    return bp
