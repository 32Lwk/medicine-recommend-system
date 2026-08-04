"""
LINE Messaging API 連携の環境変数（Webhook 環境構築用）

メッセージ本文・Reply API は別フェーズで実装する。
"""
from __future__ import annotations

import logging
import os
import time
from typing import Optional, Tuple
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from config.llm_config import _get_bool

logger = logging.getLogger(__name__)

LINE_CHANNEL_SECRET = (os.getenv("LINE_CHANNEL_SECRET") or "").strip()
LINE_CHANNEL_ACCESS_TOKEN = (os.getenv("LINE_CHANNEL_ACCESS_TOKEN") or "").strip()
LINE_WEBHOOK_ENABLED = _get_bool("LINE_WEBHOOK_ENABLED", False)


def get_line_channel_access_token() -> str:
    """実行時に環境変数を読む（import 順・.env 読込後でも有効）。"""
    return (os.getenv("LINE_CHANNEL_ACCESS_TOKEN") or LINE_CHANNEL_ACCESS_TOKEN or "").strip()


def get_line_channel_secret() -> str:
    return (os.getenv("LINE_CHANNEL_SECRET") or LINE_CHANNEL_SECRET or "").strip()


def is_line_api_configured() -> bool:
    return bool(get_line_channel_access_token())
# Push プレビュースクリプト用（本番 Webhook では未使用）
LINE_PUSH_TO_USER_ID = (os.getenv("LINE_PUSH_TO_USER_ID") or "").strip()
# 商品画像がないときの Flex hero（未設定時は PUBLIC_SITE_URL/static/line/medicine-noimage-hero.png）
LINE_HERO_PLACEHOLDER_URL = (os.getenv("LINE_HERO_PLACEHOLDER_URL") or "").strip()
# 友だち追加 URL の明示上書き（未設定時は既定の lin.ee → Bot info API）
LINE_OFFICIAL_ACCOUNT_URL = (os.getenv("LINE_OFFICIAL_ACCOUNT_URL") or "").strip()
# QR 画像 URL（未設定時は PUBLIC_SITE_URL/static/line/line-official-qr.png）
LINE_OFFICIAL_ACCOUNT_QR_URL = (os.getenv("LINE_OFFICIAL_ACCOUNT_QR_URL") or "").strip()

_DEFAULT_LINE_OFFICIAL_ACCOUNT_URL = "https://lin.ee/no4FYRe"
_DEFAULT_LINE_QR_STATIC_PATH = "/static/line/line-official-qr.png"
# GCP/AWS 共通 CDN（static 未同期時も QR を表示）
_DEFAULT_LINE_QR_CDN_URL = "https://images.yutok.dev/line/line-official-qr.png"

_BOT_INFO_CACHE: Optional[Tuple[float, str]] = None
_BOT_INFO_CACHE_TTL_SEC = 3600


def _normalize_line_account_url(raw: str) -> str:
    url = (raw or "").strip()
    if not url:
        return ""
    if url.startswith("@"):
        return f"https://line.me/R/ti/p/{url}"
    return url


def _fetch_line_official_account_url_from_api() -> str:
    token = get_line_channel_access_token()
    if not token:
        return ""
    req = Request(
        "https://api.line.me/v2/bot/info",
        headers={"Authorization": f"Bearer {token}"},
    )
    try:
        with urlopen(req, timeout=8) as resp:
            import json

            data = json.loads(resp.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, ValueError, OSError) as exc:
        logger.warning("LINE bot info lookup failed: %s", exc)
        return ""
    basic_id = str(data.get("basicId") or "").strip()
    if not basic_id:
        return ""
    return _normalize_line_account_url(basic_id)


def _public_site_base() -> str:
    return (os.getenv("PUBLIC_SITE_URL") or "https://medicine.yutok.dev").strip().rstrip("/")


def get_line_official_account_qr_url() -> str:
    override = (os.getenv("LINE_OFFICIAL_ACCOUNT_QR_URL") or LINE_OFFICIAL_ACCOUNT_QR_URL or "").strip()
    if override:
        return override
    from config.aws_features import resolve_static_asset_url
    from config.static_assets import should_prefer_local_static_assets

    if should_prefer_local_static_assets():
        return resolve_static_asset_url("line/line-official-qr.png")
    return _DEFAULT_LINE_QR_CDN_URL


def get_line_official_account_url(*, force_refresh: bool = False) -> str:
    """友だち追加 URL。環境変数 → 既定 lin.ee → Bot info API。"""
    global _BOT_INFO_CACHE
    override = (os.getenv("LINE_OFFICIAL_ACCOUNT_URL") or LINE_OFFICIAL_ACCOUNT_URL or "").strip()
    if override:
        return _normalize_line_account_url(override)
    now = time.time()
    if (
        not force_refresh
        and _BOT_INFO_CACHE
        and now - _BOT_INFO_CACHE[0] <= _BOT_INFO_CACHE_TTL_SEC
    ):
        cached = _BOT_INFO_CACHE[1]
        if cached:
            return cached
    url = _fetch_line_official_account_url_from_api()
    if not url:
        url = _DEFAULT_LINE_OFFICIAL_ACCOUNT_URL
    _BOT_INFO_CACHE = (now, url)
    return url
