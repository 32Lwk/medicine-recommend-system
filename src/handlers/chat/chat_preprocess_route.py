"""
メッセージ前処理（基本正規化）
"""
from __future__ import annotations

import logging
from typing import Any, Optional, Tuple

logger = logging.getLogger(__name__)


def basic_normalize(sanitized_message: str) -> str:
    try:
        from src.core.scoring_utils import basic_normalize_text

        return basic_normalize_text(sanitized_message)
    except ImportError:
        logger.warning("⚠️ 基本正規化機能のインポートに失敗")
    except Exception as e:
        logger.error("❌ 基本正規化エラー: %s", e)
    return sanitized_message


def apply_dialect_conversion(
    session: Any,
    sid: Optional[str],
    sanitized_message: str,
) -> str:
    """
    方言→標準語のルール変換は廃止。processed_message は sanitized_message と同一。
    方言の理解・応答は LLM プロンプト側で行う（scoring_utils の辞書コードはテスト用に残置）。
    """
    _ = session, sid
    return sanitized_message


def preprocess_user_message(
    session: Any,
    sid: Optional[str],
    sanitized_message: str,
) -> Tuple[str, str]:
    """(sanitized_message, processed_message) を返す"""
    sanitized_message = basic_normalize(sanitized_message)
    processed_message = apply_dialect_conversion(session, sid, sanitized_message)
    return sanitized_message, processed_message
