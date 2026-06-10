"""
LINE Messaging API 連携の環境変数（Webhook 環境構築用）

メッセージ本文・Reply API は別フェーズで実装する。
"""
import os

from config.llm_config import _get_bool

LINE_CHANNEL_SECRET = (os.getenv("LINE_CHANNEL_SECRET") or "").strip()
LINE_CHANNEL_ACCESS_TOKEN = (os.getenv("LINE_CHANNEL_ACCESS_TOKEN") or "").strip()
LINE_WEBHOOK_ENABLED = _get_bool("LINE_WEBHOOK_ENABLED", False)
# Push プレビュースクリプト用（本番 Webhook では未使用）
LINE_PUSH_TO_USER_ID = (os.getenv("LINE_PUSH_TO_USER_ID") or "").strip()
# 商品画像がないときの Flex hero（未設定時は PUBLIC_SITE_URL/static/line/medicine-noimage-hero.png）
LINE_HERO_PLACEHOLDER_URL = (os.getenv("LINE_HERO_PLACEHOLDER_URL") or "").strip()
