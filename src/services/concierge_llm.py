"""ConciergeAgent 専用 LLM 呼び出し（chitchat は SSE ストリーム可）"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from openai import OpenAI

from src.core.i18n_prompts import append_language_instruction, normalize_lang
from src.core.llm_client import chat_completion_create, chat_completion_stream, text_completion_adapter
from src.services.sse_emit import emit_chat_delta, get_stream_sink, is_streaming_active, pseudo_stream_chat, reply_stream_sse_enabled


def _with_lang(messages: List[Dict[str, str]], lang: str) -> List[Dict[str, str]]:
    if not messages or lang == "ja":
        return messages
    out = list(messages)
    last = out[-1]
    if last.get("role") == "user":
        out[-1] = {
            **last,
            "content": append_language_instruction(last.get("content", ""), lang),
        }
    return out


def concierge_chat(
    client: OpenAI,
    path: str,
    messages: List[Dict[str, str]],
    *,
    max_tokens: int = 200,
    temperature: float = 0.6,
    lang: str = "ja",
    session_id: Optional[str] = None,
    allow_stream: bool = True,
) -> Any:
    kwargs: Dict[str, Any] = {
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    msgs = _with_lang(messages, normalize_lang(lang))
    sink = get_stream_sink()
    sid = session_id or (sink.session_id if sink else None)
    use_stream = allow_stream and is_streaming_active(sid) and reply_stream_sse_enabled()

    if use_stream and normalize_lang(lang) == "ja":
        text = chat_completion_stream(
            client,
            model_role="concierge",
            path=path,
            messages=msgs,
            on_delta=lambda c: emit_chat_delta(c, sid),
            session_id=sid,
            **kwargs,
        )
        return text_completion_adapter(text)

    response = chat_completion_create(
        client,
        model_role="concierge",
        path=path,
        messages=msgs,
        **kwargs,
    )
    if use_stream and normalize_lang(lang) != "ja":
        raw = (response.choices[0].message.content or "").strip()
        if raw:
            from src.core.translation_service import translate_medicine_recommendation

            translated = translate_medicine_recommendation(raw, lang, session_id=sid)
            pseudo_stream_chat(translated, sid)
    return response
