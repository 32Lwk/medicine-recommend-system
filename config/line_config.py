"""
LINE Messaging API 連携の環境変数（Webhook 環境構築用）

メッセージ本文・Reply API は別フェーズで実装する。
"""
import os

from config.llm_config import _get_bool

LINE_CHANNEL_SECRET = (os.getenv("LINE_CHANNEL_SECRET") or "").strip()
LINE_CHANNEL_ACCESS_TOKEN = (os.getenv("LINE_CHANNEL_ACCESS_TOKEN") or "").strip()
LINE_WEBHOOK_ENABLED = _get_bool("LINE_WEBHOOK_ENABLED", False)
