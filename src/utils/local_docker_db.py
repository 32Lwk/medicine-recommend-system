"""ローカル Docker Postgres の起動と接続待ち（app.py 開発用）。"""
from __future__ import annotations

import logging
import os
import subprocess
import time
from pathlib import Path
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

_REPO_ROOT = Path(__file__).resolve().parents[2]
_COMPOSE_FILE = _REPO_ROOT / "docker-compose.yml"


def is_local_docker_database_url(url: str) -> bool:
    """DATABASE_URL が localhost の Postgres を指すか。"""
    if not url:
        return False
    parsed = urlparse(url)
    if (parsed.scheme or "").lower() not in ("postgresql", "postgres"):
        return False
    host = (parsed.hostname or "").lower()
    return host in ("localhost", "127.0.0.1", "::1")


def local_docker_auto_start_enabled() -> bool:
    raw = os.getenv("LOCAL_DOCKER_DB_AUTO", "1").strip().lower()
    return raw not in ("0", "false", "no", "off")


def _run_docker_compose_up() -> bool:
    if not _COMPOSE_FILE.is_file():
        logger.warning("docker-compose.yml が見つかりません: %s", _COMPOSE_FILE)
        return False
    try:
        result = subprocess.run(
            ["docker", "compose", "-f", str(_COMPOSE_FILE), "up", "-d"],
            cwd=str(_REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
    except FileNotFoundError:
        logger.warning(
            "docker コマンドがありません。Docker Desktop を起動するか、"
            "手動で `docker compose up -d` を実行してください。"
        )
        return False
    except subprocess.TimeoutExpired:
        logger.error("docker compose up がタイムアウトしました。")
        return False

    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "").strip()
        logger.error(
            "docker compose up に失敗しました (exit %s): %s",
            result.returncode,
            detail[:500],
        )
        return False

    logger.info("docker compose up -d 完了")
    return True


def wait_for_postgres(url: str, *, timeout_sec: float = 60.0) -> bool:
    try:
        import psycopg2
    except ImportError:
        logger.warning("psycopg2 未導入のため DB 接続待ちをスキップします。")
        return True

    deadline = time.monotonic() + timeout_sec
    attempt = 0
    last_error = ""
    while time.monotonic() < deadline:
        attempt += 1
        try:
            conn = psycopg2.connect(url, connect_timeout=3)
            conn.close()
            logger.info("ローカル Postgres に接続できました (attempt %s)", attempt)
            return True
        except Exception as exc:
            last_error = str(exc).split("\n")[0][:160]
            if attempt == 1 or attempt % 5 == 0:
                logger.info("Postgres 接続待ち... attempt=%s (%s)", attempt, last_error)
            time.sleep(1.5)

    logger.error(
        "ローカル Postgres への接続が %s 秒以内に確立できませんでした: %s",
        int(timeout_sec),
        last_error,
    )
    return False


def ensure_local_docker_postgres() -> None:
    """
    DATABASE_URL が localhost Postgres のとき:
    1. docker compose up -d
    2. 接続可能になるまで待機
    """
    from src.services.database import resolve_database_url

    url = resolve_database_url() or ""
    if not is_local_docker_database_url(url):
        return
    if not local_docker_auto_start_enabled():
        logger.info("LOCAL_DOCKER_DB_AUTO=0 のため Docker 自動起動をスキップします。")
        return

    timeout = float(os.getenv("LOCAL_DOCKER_DB_WAIT_SEC", "60"))
    logger.info("ローカル Docker Postgres を準備します...")
    _run_docker_compose_up()
    if not wait_for_postgres(url, timeout_sec=timeout):
        logger.warning(
            "DB 接続待ちに失敗しました。app は起動しますが、"
            "セッションはメモリ保存になる可能性があります。"
        )
