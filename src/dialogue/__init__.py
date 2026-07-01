"""
Chat Pipeline v2 — 対話状態・文脈・配信の単一責務パッケージ。

`src/core/`（推奨ロジック・medicine_logic）とは分離。
"""

from config.llm_flags import (
    is_chat_pipeline_v2_enabled,
    is_chat_pipeline_v2_for_session,
)
from src.dialogue.context import load_dialogue_context, save_dialogue_context
from src.dialogue.context_provider import ContextBundle, build_context_bundle
from src.dialogue.history import resolve_conversation_history, resolve_counseling_history
from src.dialogue.envelope import DeliveryMode, ResponseEnvelope
from src.dialogue.pipeline import try_session_ops_route, v2_session_ops_enabled
from src.dialogue.session_ops import try_handle_session_ops

__all__ = [
    "ContextBundle",
    "DeliveryMode",
    "ResponseEnvelope",
    "build_context_bundle",
    "is_chat_pipeline_v2_enabled",
    "is_chat_pipeline_v2_for_session",
    "load_dialogue_context",
    "save_dialogue_context",
    "try_handle_session_ops",
    "try_session_ops_route",
    "v2_session_ops_enabled",
]
