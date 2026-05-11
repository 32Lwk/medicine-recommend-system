"""
Flask アプリケーション（レガシー・ローカル比較用）

本番・通常のローカル起動は `python app.py`（uvicorn → main:app）または `./start.sh`。
Blueprint 経路の挙動確認のみこのモジュールを使う。
"""
import logging
import os
import time

from flask import Flask, current_app, session as flask_session
from flask_cors import CORS

from config.app_config import load_env, configure_logging, get_cors_config, get_session_config
from src.services.database import init_database
from src.utils.request_safe_session import RequestSafeSession
from src.handlers.error_handlers import register_error_handlers

configure_logging()
load_env()
logger = logging.getLogger(__name__)


app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')  # セッション管理用

# CORS・セッション設定
cors_config = get_cors_config()
CORS(app, **cors_config)

session_config = get_session_config()
for key, value in session_config.items():
    app.config[key] = value

# データベース初期化（非同期化）
try:
    init_database()
except Exception as e:
    logger.warning(f"⚠️ Database startup unexpected error: {e}. Feedback features will be disabled.")

# キャッシュバスティング用のバージョン番号
VERSION = str(int(time.time()))
app.config['VERSION'] = VERSION


@app.before_request
def _bind_request_safe_session():
    """リクエストごとに RequestSafeSession を flask.session から複製し extensions に載せる。"""
    from flask import g

    ws = RequestSafeSession(dict(flask_session))
    g.safe_session_work = ws
    current_app.extensions['safe_session'] = ws


@app.after_request
def _persist_request_safe_session(response):
    from flask import g

    ws = getattr(g, 'safe_session_work', None)
    if ws is not None and ws.modified:
        flask_session.clear()
        for k, v in dict(ws).items():
            flask_session[k] = v
    return response


# エラーハンドラーを登録
register_error_handlers(app, VERSION)

# Blueprint登録
from src.routes import create_main_routes, create_admin_routes, create_api_routes, create_feedback_routes

app.register_blueprint(create_main_routes())
app.register_blueprint(create_main_routes(url_prefix='/test', blueprint_name='main_test'))
app.register_blueprint(create_admin_routes())
app.register_blueprint(create_api_routes())
app.register_blueprint(create_feedback_routes())


def run_flask_development_server() -> None:
    """Flask 開発サーバーを起動する（レガシー比較用）。"""
    from src.utils.port_utils import find_free_port, is_port_in_use

    logger.info("🚀 Starting Medicine Recommendation System (Flask legacy)...")

    try:
        from src.core.scoring_utils import initialize_dialect_resources
        initialize_dialect_resources()
    except Exception as e:
        logger.warning(f"⚠️ 方言変換リソースの初期化に失敗: {e}")
        import traceback
        traceback.print_exc()

    requested_port = int(os.getenv('PORT', 5000))
    debug_mode = os.getenv('FLASK_ENV') != 'production'

    if is_port_in_use(requested_port):
        logger.warning(f"⚠️ Port {requested_port} is already in use. Finding alternative port...")
        port = find_free_port(requested_port + 1)
        logger.info(f"✅ Found available port: {port}")
    else:
        port = requested_port

    logger.info(f"🌐 Starting Flask server on port {port} (debug={debug_mode})...")
    app.run(debug=debug_mode, port=port, host='0.0.0.0')


if __name__ == '__main__':
    run_flask_development_server()
