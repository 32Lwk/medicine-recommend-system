"""
メッセージ前処理（基本正規化・方言変換）
"""
from __future__ import annotations

import logging
import os
import traceback
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
    方言→標準語変換。内部処理用 processed_message を返し、重症度等を session に保存。
    sanitized_message（UI表示用）は変更しない。
    """
    processed_message = sanitized_message
    if sid:
        from src.services.processing_status import mark_processing_step

        mark_processing_step(sid, "dialect")

    try:
        from src.core.scoring_utils import check_escalation_threshold, convert_dialect_to_standard

        converted_message, severity_tag, escalation_score, non_destructive_candidates, normalized_weights = (
            convert_dialect_to_standard(
                sanitized_message,
                extract_severity=True,
                non_destructive=True,
                use_aho_corasick=True,
                use_index=True,
                use_scanner=True,
            )
        )
        processed_message = converted_message

        if severity_tag:
            session["detected_severity_tag"] = severity_tag
        if escalation_score > 0:
            session["escalation_score"] = escalation_score
            if check_escalation_threshold(escalation_score):
                session["doctor_referral_required"] = True
                session["escalation_reason"] = (
                    f"複数の強調表現が検出されました（escalation_score: {escalation_score:.1f}）。"
                    "特に高齢の方の場合、複数の強調語は「痛みに耐えかねている」シグナルです。"
                    "医師の診断を受けることをお勧めします。"
                )
        if non_destructive_candidates:
            session["dialect_candidates"] = non_destructive_candidates
        if normalized_weights:
            session["normalized_symptom_weights"] = normalized_weights

        if os.getenv("DEBUG_MODE", "false").lower() == "true" or logger.level <= logging.DEBUG:
            logger.debug(
                "方言変換: %s... (重症度タグ: %s, escalation_score: %.1f, 候補数: %s, 重み数: %s)",
                sanitized_message[:50],
                severity_tag,
                escalation_score,
                len(non_destructive_candidates),
                len(normalized_weights),
            )
    except ImportError:
        logger.warning("⚠️ 方言変換機能のインポートに失敗")
    except Exception as e:
        logger.error("❌ 方言変換エラー: %s", e)
        traceback.print_exc()

    return processed_message


def preprocess_user_message(
    session: Any,
    sid: Optional[str],
    sanitized_message: str,
) -> Tuple[str, str]:
    """(sanitized_message, processed_message) を返す"""
    sanitized_message = basic_normalize(sanitized_message)
    processed_message = apply_dialect_conversion(session, sid, sanitized_message)
    return sanitized_message, processed_message
