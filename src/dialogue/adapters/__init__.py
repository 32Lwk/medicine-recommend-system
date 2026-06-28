"""Dialogue 配信アダプタ（Web SSE / LINE）。"""

from src.dialogue.adapters.line_delivery import (
    build_line_delivery_envelope,
    resolve_line_messages,
    should_skip_redirect_on_missing_bot,
)
from src.dialogue.adapters.web_sse import (
    merge_dialogue_delivery_into_done,
    record_pipeline_envelope,
)

__all__ = [
    "build_line_delivery_envelope",
    "merge_dialogue_delivery_into_done",
    "record_pipeline_envelope",
    "resolve_line_messages",
    "should_skip_redirect_on_missing_bot",
]
