"""絵文字のみ入力の意図分類（LINE 向け軽量 LLM）。"""
from __future__ import annotations

import json
import logging
import re
from typing import Literal, Optional, Tuple

from openai import OpenAI

from src.content.concierge_knowledge import (
    get_agents,
    get_app_info,
    get_capabilities,
    get_limitations,
)

logger = logging.getLogger(__name__)

EmojiIntent = Literal["greeting", "emotional", "offensive", "thanks", "unknown"]

_VALID_INTENTS = frozenset({"greeting", "emotional", "offensive", "thanks", "unknown"})

_EMOJI_INTENT_SYSTEM = """あなたは医薬品相談チャットにおける絵文字のみ入力の意図分類器です。
出力は JSON のみ。説明文は不要です。"""

_EMOJI_INTENT_USER = """次の絵文字のみメッセージの意図を分類してください。

【分類】
- greeting: 挨拶・呼びかけ（👋🙋等）
- thanks: 感謝・ねぎらい（🙏💐等）
- emotional: 悲しみ・つらさ・泣き・落ち込み（😭😢等）
- offensive: 侮辱・挑発・攻撃（🖕👹💩🤬等）
- unknown: 上記に当てはまらない

【入力】
{emoji_text}

JSON形式:
{{"intent": "greeting|emotional|offensive|thanks|unknown", "confidence": 0.0-1.0}}
"""


def build_emoji_soft_intro_text() -> str:
    """
    侮辱絵文字検出時の応答（侮辱への言及なし・長めの自己紹介）。
    concierge_knowledge SSOT から組み立てる。
    """
    app = get_app_info()
    caps = get_capabilities()
    agents = get_agents()
    limits = get_limitations()

    lines = [
        app.get("name", "チャット型医薬品相談ツール"),
        "",
        app.get("purpose", ""),
        f"対象: {app.get('audience', '')}",
        "",
        "【このツールについて】",
        f"・{app.get('service_nature', '')}",
        f"・{app.get('explicitly_not', '')}",
        "",
        "【できること】",
    ]
    for cap in caps:
        title = cap.get("title", "")
        body = cap.get("body", "")
        if title and body:
            lines.append(f"・{title}：{body}")

    lines.extend(["", "【しくみ（簡単に）】"])
    for agent in agents[:6]:
        name = agent.get("name_ja") or agent.get("id", "")
        role = agent.get("role_one_liner", "")
        if name and role:
            lines.append(f"・{name}：{role}")

    if limits:
        lines.extend(["", "【ご留意ください】"])
        for item in limits[:4]:
            lines.append(f"・{item}")

    lines.extend(
        [
            "",
            "お身体の不調や市販薬の選び方でお困りのことがあれば、"
            "「頭が痛い」「のどが痛い」のようにテキストで具体的にお書きください。",
        ]
    )
    return "\n".join(lines)


def build_emoji_unknown_ack_text() -> str:
    """分類不能な絵文字のみ入力への中立応答。"""
    app = get_app_info()
    name = app.get("name", "チャット型医薬品相談ツール")
    return (
        f"メッセージありがとうございます。\n"
        f"こちらは{name}です。"
        "絵文字だけだと意図が伝わりにくい場合があります。\n"
        "お身体の症状やご質問を、テキストでお書きいただけますか。\n"
        "例：頭が痛い、のどの痛み、眠れない など"
    )


def _parse_emoji_intent_json(raw: str) -> Tuple[Optional[EmojiIntent], float]:
    text = (raw or "").strip()
    if not text:
        return None, 0.0
    data = None
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        m = re.search(r"\{[^{}]+\}", text, re.DOTALL)
        if m:
            try:
                data = json.loads(m.group(0))
            except json.JSONDecodeError:
                pass
    if not isinstance(data, dict):
        return None, 0.0
    intent = str(data.get("intent") or "").strip().lower()
    if intent not in _VALID_INTENTS:
        return None, 0.0
    try:
        conf = float(data.get("confidence", 0.8))
    except (TypeError, ValueError):
        conf = 0.8
    return intent, conf  # type: ignore[return-value]


def classify_emoji_intent_llm(
    client: OpenAI,
    emoji_text: str,
    *,
    session_id: Optional[str] = None,
) -> Tuple[EmojiIntent, float]:
    """絵文字のみ入力を 5 分類。失敗時は unknown。"""
    from src.core.llm_client import chat_completion_create

    prompt = _EMOJI_INTENT_USER.format(emoji_text=emoji_text.strip())
    try:
        response = chat_completion_create(
            client,
            model_role="emoji_intent",
            path="emoji_intent.classify",
            messages=[
                {"role": "system", "content": _EMOJI_INTENT_SYSTEM},
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,
            max_tokens=80,
            session_id=session_id,
        )
        raw = (response.choices[0].message.content or "").strip()
        intent, conf = _parse_emoji_intent_json(raw)
        if intent:
            return intent, conf
    except Exception as exc:
        logger.warning("emoji_intent LLM failed: %s", exc)
    return "unknown", 0.0
