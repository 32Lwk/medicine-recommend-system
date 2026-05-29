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
        logger.warning(
            "⚠️ Port %s is already in use (古い uvicorn が残っている可能性があります). "
            "Finding alternative port...",
            requested_port,
        )
        port = find_free_port(requested_port + 1)
        logger.info("✅ Found available port: %s", port)
        logger.warning(
            "別ポートで起動しました。ブラウザは http://127.0.0.1:%s/ を開きます。"
            " /about が古い表示のときは、ポート %s のプロセスを終了してから再起動してください。",
            port,
            requested_port,
        )
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
    # 既定は reload OFF（Windows でチャット中に再起動すると全 API がハングするため）
    reload = os.getenv('UVICORN_RELOAD', '').strip().lower() in ('1', 'true', 'yes')
    host = os.getenv('ASGI_HOST', '0.0.0.0')
    logger.info(f"🚀 Starting FastAPI (uvicorn) on port {port} (reload={reload})...")
    logger.info(
        "ローカルで開く URL: http://127.0.0.1:%s/ （uvicorn の「0.0.0.0」は全インターフェースで待ち受けている表示で、起動失敗ではありません）",
        port,
    )
    _schedule_open_browser(port)
    # reload 時に log/ やキャッシュ変更で再起動すると SSE が切れ「接続できません」になるため監視範囲を限定
    uvicorn_kwargs = {
        'host': host,
        'port': port,
        'reload': reload,
    }
    if reload:
        uvicorn_kwargs['reload_dirs'] = ['src', 'config', 'templates', 'static']
        # main.py の /about ルート変更も開発時に反映する
        uvicorn_kwargs['reload_includes'] = [
            'main.py',
            'src/content/about_i18n.py',
        ]
        uvicorn_kwargs['reload_excludes'] = [
            'log',
            'log/*',
            '**/__pycache__',
            '**/__pycache__/*',
            '.pytest_cache',
            '.pytest_cache/*',
            '*.pyc',
            '*.jsonl',
        ]
    uvicorn.run('main:app', **uvicorn_kwargs)
