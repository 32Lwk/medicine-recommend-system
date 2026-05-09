"""
エラー応答構築ハンドラー

責務: 404/502/500 エラー時のレスポンス構築
"""
import json
import logging
import os
import traceback
from datetime import datetime

import pytz
from flask import request, render_template, jsonify, has_request_context, session as flask_session

from src.core.season_manager import get_current_season, get_season_images

logger = logging.getLogger(__name__)


def _get_decoration_images(session, version):
    """季節装飾画像を取得（エラーハンドラー用）"""
    try:
        jst = pytz.timezone('Asia/Tokyo')
        current_date = datetime.now(jst)
        season_type = get_current_season(current_date)
        year = current_date.year
        decoration_images = []
        if season_type:
            try:
                decoration_images = get_season_images(season_type, year, session)
            except Exception:
                decoration_images = get_season_images(season_type, year, None)
        return decoration_images, version
    except Exception as e:
        logger.warning(f"⚠️ 季節画像の生成でエラー: {e}")
        return [], version


def _session_like_for_error_pages():
    if has_request_context():
        try:
            return dict(flask_session)
        except Exception:
            return {}
    return {}


def register_error_handlers(app, version):
    """
    アプリにエラーハンドラーを登録する

    Args:
        app: Flaskアプリケーション
        version: キャッシュバスティング用バージョン文字列
    """
    @app.errorhandler(404)
    def handle_404(e):
        """404エラーのハンドラー"""
        logger.warning(f"⚠️ 404 Not Found: {request.url}")
        decoration_images, image_version = _get_decoration_images(_session_like_for_error_pages(), version)
        return render_template(
            'index.html',
            messages=[],
            version=version,
            decoration_images=decoration_images,
            image_version=image_version
        ), 404

    @app.errorhandler(502)
    def handle_502(e):
        """502エラーのハンドラー"""
        logger.error(f"❌ 502 Bad Gateway Error: {str(e)}")
        logger.error(f"❌ エラータイプ: {type(e).__name__}")
        if request.is_json or request.method == 'POST':
            return jsonify({
                'error': True,
                'response': 'サーバーエラーが発生しました。しばらく時間をおいてから再度お試しください。'
            }), 502
        decoration_images, image_version = _get_decoration_images(_session_like_for_error_pages(), version)
        return render_template(
            'index.html',
            messages=[],
            version=version,
            decoration_images=decoration_images,
            image_version=image_version
        ), 502

    @app.errorhandler(500)
    def handle_500(e):
        """500エラーのハンドラー"""
        error_type = type(e).__name__
        error_message = str(e)
        stack_trace_str = traceback.format_exc()
        logger.error(f"❌ 500 Internal Server Error: {error_message}")
        logger.error(f"❌ エラータイプ: {error_type}")
        logger.error(f"❌ トレースバック:\n{stack_trace_str}")

        session_id = None
        try:
            session_id = flask_session.get('_id') if has_request_context() else None
        except Exception:
            pass

        user_input = None
        try:
            if request.method == 'POST':
                if request.is_json:
                    user_input = json.dumps(request.get_json())
                else:
                    user_input = request.form.get('message', '')
        except Exception:
            pass

        system_state = {}
        try:
            from src.utils.performance_monitor import get_global_monitor
            monitor = get_global_monitor()
            metrics = monitor.get_metrics()
            system_state = {
                'memory_usage_percent': metrics.get('memory_usage_percent', 0),
                'cpu_usage_percent': metrics.get('cpu_usage_percent', 0),
                'response_time_ms': metrics.get('response_time_ms', 0),
                'error_count': metrics.get('error_count', 0),
                'request_count': metrics.get('request_count', 0)
            }
        except Exception:
            pass

        if not os.getenv('OPENAI_API_KEY'):
            logger.error("❌ OPENAI_API_KEY が環境変数に設定されていません！")
            error_msg = "⚠️ OpenAI APIキーが設定されていません。Renderの環境変数を確認してください。"
        else:
            error_msg = "申し訳ございません。システムエラーが発生しました。管理者に連絡してください。"

        conversation_history = None
        try:
            if has_request_context():
                messages = flask_session.get('messages', [])
                if messages:
                    conversation_history = messages[-10:] if len(messages) > 10 else messages
        except Exception:
            pass

        try:
            from src.utils.structured_logger import log_error_detail
            log_error_detail(
                session_id=session_id,
                error_type=error_type,
                error_message=error_message,
                stack_trace=stack_trace_str,
                user_input=user_input,
                system_state=system_state,
                user_display_message=error_msg,
                conversation_history=conversation_history
            )
        except Exception as log_err:
            logger.warning(f"エラーログ記録エラー: {log_err}")

        if request.is_json or request.method == 'POST':
            return jsonify({
                'error': True,
                'response': error_msg,
                'error_type': error_type if os.getenv('FLASK_ENV') != 'production' else None
            }), 500
        return f"<h1>エラー</h1><p>{error_msg}</p>", 500
