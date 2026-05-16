"""
Other カテゴリ向け Concierge メタ意図の LLM 分類
"""
from __future__ import annotations

import hashlib
import json
import logging
import time
from typing import Any, Dict, Optional, Tuple

from openai import OpenAI

from src.services.concierge_intent import ConciergeIntent
from src.services.triage_history import format_triage_history_block, history_digest

logger = logging.getLogger(__name__)

_META_CACHE: Dict[str, Tuple[float, Optional[ConciergeIntent]]] = {}
_META_CACHE_TTL_SEC = 600
_META_CACHE_MAX = 128

_VALID_INTENTS = frozenset({
    "capabilities",
    "architecture",
    "app_about",
    "doc_privacy",
    "doc_terms",
    "doc_operator",
    "doc_consultation",
    "doc_app_overview",
    "chitchat",
    "redirect",
    "none",
})

_META_PROMPT = """ユーザーの発言がこの医薬品相談チャットアプリへのメタ質問かを分類してください。
方言・口語（例: あんた、お前）も標準語と同様に解釈してください。

【意図】
- capabilities: できること・機能・対応言語の説明（例: 「何ができる？」「できることを教えて」）
- architecture: マルチエージェント・内部構成・仕組み・薬の選び方の仕組み（例: 「マルチエージェントなの？」「薬はどうやって決まる？」）
- app_about: 短い自己紹介・あなたは誰・一行でのツール説明（例: 「あなたは誰？」「自己紹介して」）
- doc_privacy: プライバシーポリシー・個人情報・データの取り扱い（例: 「プライバシーポリシーは？」「個人情報は収集する？」）
- doc_terms: 免責事項・利用規約・禁止事項・試験運用の条件（例: 「利用規約を教えて」「免責事項は？」）
- doc_operator: 運営者情報・連絡先・不具合報告・開発者・所属（例: 「運営者は誰？」「大学はどこ？」＝開発者の所属大学、「連絡先は？」）
- doc_consultation: 公的機関の相談窓口・PMDA・厚労省・#7119 など（例: 「相談先を教えて」「PMDAのリンクは？」）
- doc_app_overview: アプリ概要.md の内容（開発背景・β版の目的・技術構成・対象者の詳細）（例: 「アプリの概要」「開発背景は？」「β版の対象者は？」）
- chitchat: 雑談・天気・暇つぶし（医療相談ではない）
- redirect: 話題がずれている・医薬品相談へ誘導すべき
- none: 上記以外（店舗案内・症状・医薬品相談などは none）

医薬品・症状・店舗・違法薬物の相談は none としてください。
アシスタント自身について聞いている場合は app_about を選んでください（none にしない）。
公式ドキュメントの内容を聞いている場合は、該当する doc_* を選んでください。

【補足（architecture 回答時に伝える事実）】
市販薬（OTC）の候補選定はルールベースアルゴリズムのみで行い、LLM が自由に薬名を創作して決めることはありません。

JSON形式:
{"intent": "capabilities|architecture|app_about|doc_privacy|doc_terms|doc_operator|doc_consultation|doc_app_overview|chitchat|redirect|none", "confidence": 0.0-1.0}
"""


def _meta_cache_key(user_text: str, conversation_history: Optional[list]) -> str:
    norm = (user_text or "").strip().lower()
    hist = history_digest(conversation_history or [])
    raw = f"{norm}|{hist}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]


def _purge_meta_cache() -> None:
    now = time.time()
    expired = [k for k, (ts, _) in _META_CACHE.items() if now - ts > _META_CACHE_TTL_SEC]
    for k in expired:
        del _META_CACHE[k]
    while len(_META_CACHE) > _META_CACHE_MAX:
        _META_CACHE.pop(next(iter(_META_CACHE)))


def classify_meta_concierge_intent(
    user_text: str,
    client: OpenAI,
    *,
    conversation_history: Optional[list] = None,
) -> Optional[ConciergeIntent]:
    cache_key = _meta_cache_key(user_text, conversation_history)
    _purge_meta_cache()
    cached = _META_CACHE.get(cache_key)
    if cached and time.time() - cached[0] <= _META_CACHE_TTL_SEC:
        return cached[1]

    hist = format_triage_history_block(conversation_history or [])
    prompt = f"{_META_PROMPT}\n\n【会話履歴】\n{hist}\n\n【発言】\n{user_text}"
    try:
        from src.core.llm_client import chat_completion_create

        response = chat_completion_create(
            client,
            model_role="concierge",
            path="meta_triage.classify",
            messages=[
                {"role": "system", "content": "JSONのみ返してください。"},
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,
            max_tokens=120,
            response_format={"type": "json_object"},
        )
        raw = (response.choices[0].message.content or "").strip()
        start = raw.find("{")
        end = raw.rfind("}")
        if start < 0 or end <= start:
            return None
        data = json.loads(raw[start : end + 1])
        intent = str(data.get("intent") or "none").lower()
        if intent in ("self_intro", "about", "intro"):
            intent = "app_about"
        if intent == "none":
            _META_CACHE[cache_key] = (time.time(), None)
            return None
        if intent not in _VALID_INTENTS:
            _META_CACHE[cache_key] = (time.time(), None)
            return None
        result = intent  # type: ignore[assignment]
        _META_CACHE[cache_key] = (time.time(), result)
        return result
    except Exception as exc:
        logger.warning("meta_triage failed: %s", exc)
        return None
