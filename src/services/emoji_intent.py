"""絵文字のみ入力の意図分類（LINE 向け軽量 LLM）。"""
from __future__ import annotations

import json
import logging
import random
import re
from typing import Literal, Optional, Tuple

from openai import OpenAI

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

_OFFENSIVE_EMOJI_RESPONSE_SYSTEM = (
    "あなたは市販薬相談ツールの案内役です。"
    "ユーザーが怒り・苛立ち・挑発を示す絵文字を送ったとき、"
    "短く寄り添い、落ち着いて受け止めます。"
    "侮辱への反論・説教・長い自己紹介はしません。"
)

_OFFENSIVE_EMOJI_FALLBACKS = [
    (
        "お気持ち、受け止めました。"
        "つらいときやモヤモヤがあるときは、無理せず少し休んでください。"
        "お薬のことでお困りでしたら、いつでもお聞かせください。"
    ),
    (
        "お声がけありがとうございます。"
        "こちらは市販薬の相談窓口です。"
        "お身体のことで気になることがあれば、ゆっくりお書きください。"
    ),
    (
        "気持ちが重いときは、ひとりで抱え込まなくて大丈夫です。"
        "症状やお薬のことでしたら、お手伝いしますのでお知らせください。"
    ),
]


def build_offensive_emoji_fallback_text() -> str:
    """侮辱・挑発絵文字への短い寄り添い応答（LLM 失敗時）。"""
    return random.choice(_OFFENSIVE_EMOJI_FALLBACKS)


def generate_offensive_emoji_response_llm(
    client: OpenAI,
    emoji_text: str,
    *,
    session_id: Optional[str] = None,
) -> str:
    """
    侮辱・挑発絵文字への短い寄り添い応答（2〜3文・60〜140文字）。
    侮辱への言及・反論・長い自己紹介はしない。
    """
    from src.core.llm_client import chat_completion_create

    prompt = f"""次の絵文字メッセージを受け取りました。意図（苛立ち・挑発・怒りなど）を汲み取り、短く寄り添って返答してください。

【入力】
{emoji_text.strip()}

【要件】
- 2〜3文、60〜140文字程度
- 感情を受け止め、責めない・反論しない
- 侮辱・攻撃への言及はしない
- 長い自己紹介・技術説明・機能一覧はしない
- 市販薬相談窓口であることは必要なら1文だけ
- 症状相談へ戻すときは自然な言い回しで
"""
    try:
        response = chat_completion_create(
            client,
            model_role="emoji_intent",
            path="emoji_intent.offensive_response",
            messages=[
                {"role": "system", "content": _OFFENSIVE_EMOJI_RESPONSE_SYSTEM},
                {"role": "user", "content": prompt},
            ],
            temperature=0.55,
            max_tokens=160,
            session_id=session_id,
        )
        text = (response.choices[0].message.content or "").strip()
        if 40 <= len(text) <= 220:
            return text
        if text and len(text) > 220:
            return text[:200].rstrip("、。,.") + "。"
    except Exception as exc:
        logger.warning("offensive emoji response LLM failed: %s", exc)
    return build_offensive_emoji_fallback_text()


def build_emoji_unknown_ack_text() -> str:
    """分類不能な絵文字のみ入力への中立応答。"""
    from src.content.concierge_knowledge import get_app_info

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
