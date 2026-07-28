"""
ローカル開発用エントリポイント。

- 既定: FastAPI（`main:app`）を uvicorn で起動。
本番は `./start.sh` → gunicorn `main:app`。
環境変数 `ASGI_HOST`（既定 `0.0.0.0`）で待ち受けアドレスを変更可能。
`OPEN_BROWSER=1` で起動時にブラウザを自動オープン（既定はオフ — 二重タブによる SSE 競合を避ける）。
`OPEN_BROWSER_WAIT_SEC`（既定 120）で /health 応答待ちの上限秒数を変更可能。
`APP_PYTHON_REEXEC=0` で .venv への自動切替を無効化。
"""
import os
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent


def _project_venv_python() -> Path | None:
    if os.name == 'nt':
        candidates = (_REPO_ROOT / '.venv' / 'Scripts' / 'python.exe',)
    else:
        candidates = (_REPO_ROOT / '.venv' / 'bin' / 'python',)
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return None


def _reexec_with_project_venv_if_needed() -> None:
    """Cursor/VS Code の再生ボタンが壊れた system Python を選ぶ事故を防ぐ。"""
    if os.environ.get('APP_PY_VENV_REEXEC') == '1':
        return
    if os.environ.get('APP_PYTHON_REEXEC', '1').strip().lower() in ('0', 'false', 'no', 'off'):
        return
    if os.environ.get('CI', '').strip().lower() in ('1', 'true', 'yes'):
        return

    venv_python = _project_venv_python()
    if venv_python is None:
        return

    try:
        current = Path(sys.executable).resolve()
    except OSError:
        return

    if current == venv_python.resolve():
        return

    os.environ['APP_PY_VENV_REEXEC'] = '1'
    print(
        f'[app.py] プロジェクト venv で再起動します: {venv_python}',
        file=sys.stderr,
        flush=True,
    )
    os.execv(str(venv_python), [str(venv_python), *sys.argv])


_reexec_with_project_venv_if_needed()

import logging
import subprocess
import threading
import time
import webbrowser

from config.app_config import configure_logging, load_env

configure_logging()
load_env()
logger = logging.getLogger(__name__)


def _prepare_local_database_async() -> None:
    """ローカル開発: Docker Postgres の起動と接続待ち（uvicorn 起動をブロックしない）。"""

    def _run() -> None:
        try:
            from src.utils.local_docker_db import ensure_local_docker_postgres

            ensure_local_docker_postgres()
        except Exception as exc:
            logger.warning("ローカル DB 準備をスキップしました: %s", exc)

    threading.Thread(target=_run, daemon=True, name='local-db-prep').start()


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


def _open_browser_url(url: str) -> bool:
    if webbrowser.open(url):
        return True
    if os.name == 'nt':
        try:
            os.startfile(url)  # type: ignore[attr-defined]
            return True
        except OSError:
            pass
        try:
            subprocess.run(
                ['cmd', '/c', 'start', '', url],
                check=False,
                creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0),
            )
            return True
        except OSError:
            return False
    return False


def _schedule_open_browser(port: int) -> None:
    """/health が応答してから既定ブラウザでローカル URL を開く（reload 子プロセスの起動待ち）。"""
    if os.getenv('OPEN_BROWSER', '0').strip().lower() in ('0', 'false', 'no'):
        return
    url = f'http://127.0.0.1:{port}/'
    health_url = f'http://127.0.0.1:{port}/health'
    timeout_sec = float(os.getenv('OPEN_BROWSER_WAIT_SEC', '120'))

    def _open_when_ready() -> None:
        import urllib.error
        import urllib.request

        deadline = time.monotonic() + timeout_sec
        while time.monotonic() < deadline:
            try:
                with urllib.request.urlopen(health_url, timeout=2) as resp:
                    if resp.status == 200:
                        break
            except (urllib.error.URLError, OSError, TimeoutError):
                time.sleep(0.5)
        else:
            logger.warning(
                'サーバーが %s 秒以内に応答しませんでした。手動で %s を開いてください。',
                int(timeout_sec),
                url,
            )
            return

        if _open_browser_url(url):
            logger.info('ブラウザを開きました: %s', url)
        else:
            logger.info('ブラウザを自動で開けませんでした。手動で %s を開いてください。', url)

    threading.Thread(target=_open_when_ready, daemon=True, name='open-browser').start()


if __name__ == '__main__':
    try:
        import uvicorn
    except ModuleNotFoundError:
        venv_hint = _project_venv_python()
        if venv_hint is not None:
            logger.error(
                "FastAPI 起動に uvicorn が必要です。次を実行してください: %s -m pip install -r requirements.txt",
                venv_hint,
            )
        else:
            logger.error(
                "FastAPI 起動に uvicorn が必要です。仮想環境を作成し pip install -r requirements.txt を実行してください。"
            )
        raise

    _prepare_local_database_async()
    port = _resolve_port()
    from config.app_config import is_development_runtime

    # 開発時は reload 既定 ON（Windows でチャット中に再起動するとハングするため UVICORN_RELOAD=0 で無効化可）
    reload_env = os.getenv('UVICORN_RELOAD', '').strip().lower()
    if reload_env in ('1', 'true', 'yes'):
        reload = True
    elif reload_env in ('0', 'false', 'no'):
        reload = False
    else:
        reload = is_development_runtime()
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
