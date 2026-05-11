"""
ローカル開発用エントリポイント。

- 既定: FastAPI（`main:app`）を uvicorn で起動。
本番は `./start.sh` → gunicorn `main:app`。
環境変数 `ASGI_HOST`（既定 `0.0.0.0`）で待ち受けアドレスを変更可能。
`OPEN_BROWSER=0` で起動時のブラウザ自動オープンを無効化（CI 等）。
"""
import logging
import os
import threading
import time
import webbrowser

from config.app_config import configure_logging, load_env

configure_logging()
load_env()
logger = logging.getLogger(__name__)


def _resolve_port() -> int:
    from src.utils.port_utils import find_free_port, is_port_in_use

    requested_port = int(os.getenv('PORT', 5000))
    if is_port_in_use(requested_port):
        logger.warning(f"⚠️ Port {requested_port} is already in use. Finding alternative port...")
        port = find_free_port(requested_port + 1)
        logger.info(f"✅ Found available port: {port}")
        return port
    return requested_port


def _schedule_open_browser(port: int) -> None:
    """サーバー起動後に既定ブラウザでローカル URL を開く（uvicorn 起動直後はブロックするため別スレッド）。"""
    if os.getenv('OPEN_BROWSER', '1').strip().lower() in ('0', 'false', 'no'):
        return
    url = f'http://127.0.0.1:{port}/'

    def _open() -> None:
        time.sleep(1.5)
        if webbrowser.open(url):
            logger.info('ブラウザを開きました: %s', url)
        else:
            logger.info('ブラウザを自動で開けませんでした。手動で %s を開いてください。', url)

    threading.Thread(target=_open, daemon=True).start()


if __name__ == '__main__':
    try:
        import uvicorn
    except ModuleNotFoundError:
        logger.error(
            "FastAPI 起動に uvicorn が必要です。仮想環境で次を実行してください: pip install -r requirements.txt"
        )
        raise

    port = _resolve_port()
    reload = os.getenv('APP_ENV', '').strip().lower() != 'production'
    host = os.getenv('ASGI_HOST', '0.0.0.0')
    logger.info(f"🚀 Starting FastAPI (uvicorn) on port {port} (reload={reload})...")
    logger.info(
        "ローカルで開く URL: http://127.0.0.1:%s/ （uvicorn の「0.0.0.0」は全インターフェースで待ち受けている表示で、起動失敗ではありません）",
        port,
    )
    _schedule_open_browser(port)
    uvicorn.run('main:app', host=host, port=port, reload=reload)
