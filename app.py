"""
Flask アプリケーションエントリポイント（レガシー・ローカル比較用）

本番は start.sh → gunicorn main:app（FastAPI）を使用する。
責務: アプリ作成、設定（CORS・セッション・DB初期化）、エラーハンドラー登録、
     Blueprint の import と register、起動処理のみ。
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
    if not init_database():
        logger.warning("⚠️ Database initialization failed. Feedback features will be disabled.")
    else:
        logger.info("✅ Database initialized successfully.")
except Exception as e:
    logger.warning(f"⚠️ Database initialization error: {e}. Feedback features will be disabled.")

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

if __name__ == '__main__':
    from src.utils.port_utils import find_free_port, is_port_in_use

    logger.info("🚀 Starting Medicine Recommendation System...")
    
    # 方言変換リソースの初期化（アプリ起動時に一度だけ実行）
    try:
        from src.core.scoring_utils import initialize_dialect_resources
        initialize_dialect_resources()
    except Exception as e:
        logger.warning(f"⚠️ 方言変換リソースの初期化に失敗: {e}")
        import traceback
        traceback.print_exc()
    
    # 最小限のログ出力で起動時間を短縮
    requested_port = int(os.getenv('PORT', 5000))
    debug_mode = os.getenv('FLASK_ENV') != 'production'
    
    # ポートが使用中の場合は、利用可能なポートを探す
    if is_port_in_use(requested_port):
        logger.warning(f"⚠️ Port {requested_port} is already in use. Finding alternative port...")
        port = find_free_port(requested_port + 1)
        logger.info(f"✅ Found available port: {port}")
    else:
        port = requested_port
    
    logger.info(f"🌐 Starting Flask server on port {port} (debug={debug_mode})...")
    app.run(debug=debug_mode, port=port, host='0.0.0.0')