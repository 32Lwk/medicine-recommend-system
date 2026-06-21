"""
クリティカルルートの非同期ルーティング検証（ログ・監査用）
"""
from __future__ import annotations

import json
import logging
import os
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from openai import OpenAI

logger = logging.getLogger(__name__)

_LOG_PATH = Path("log/routing_validator.jsonl")


def is_verify_routing_enabled() -> bool:
    """本番既定 OFF。VERIFY_ROUTING_LLM=1 で有効化。"""
    return os.getenv("VERIFY_ROUTING_LLM", "").strip().lower() in ("1", "true", "yes")


def _append_log(entry: Dict[str, Any]) -> None:
    try:
        _LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with _LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception as exc:
        logger.debug("routing_validator log skip: %s", exc)


def verify_routing_async(
    *,
    route_kind: str,
    user_text: str,
    decided_category: str,
    client: OpenAI,
    session_id: Optional[str] = None,
    extra: Optional[Dict[str, Any]] = None,
) -> None:
    """非ブロッキングで軽量モデルにルーティング妥当性を確認しログする。"""
    if not is_verify_routing_enabled():
        return

    def _run() -> None:
        try:
            from src.core.llm_client import chat_completion_create

            prompt = (
                f"ルート種別: {route_kind}\n"
                f"決定カテゴリ: {decided_category}\n"
                f"ユーザー入力: {user_text[:200]}\n\n"
                "このルーティングは妥当か。JSON: "
                '{"confirmed": true|false, "suggested_category": "Physical|Emotional|Ask|Other|Emergency|null"}'
            )
            response = chat_completion_create(
                client,
                model_role="validator",
                path=f"routing_validator.{route_kind}",
                messages=[
                    {"role": "system", "content": "ルーティング監査。JSONのみ。"},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.0,
                max_tokens=80,
            )
            raw = (response.choices[0].message.content or "").strip()
            _append_log({
                "timestamp": datetime.now().isoformat(),
                "session_id": session_id,
                "route_kind": route_kind,
                "decided_category": decided_category,
                "validator_raw": raw[:500],
                "extra": extra or {},
            })
        except Exception as exc:
            logger.debug("routing_validator async failed: %s", exc)

    threading.Thread(target=_run, daemon=True).start()
