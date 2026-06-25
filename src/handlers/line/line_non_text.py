"""LINE の非テキストメッセージ（スタンプ・画像・音声など）の案内とスタンプ解釈。"""
from __future__ import annotations

import json
import logging
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

from src.services.concierge_intent import classify_concierge_intent

logger = logging.getLogger(__name__)

_STICKER_MAP_PATH = (
    Path(__file__).resolve().parents[3] / "data" / "line_official_sticker_intents.json"
)

_GREETING_KEYWORD_RE = re.compile(
    r"(こんにちは|こんばんは|おはよう|はじめまして|初めまして|やあ|やっほ|hello|hi\b|hey\b|"
    r"good\s*morning|good\s*evening|greeting|挨拶|おつかれ|よろしく)",
    re.I,
)
_THANKS_KEYWORD_RE = re.compile(
    r"(ありがとう|感謝|サンキュー|thanks|thank\s*you|ごちそう)",
    re.I,
)

_SYNTHETIC_BY_INTENT: dict[str, str] = {
    "greeting": "こんにちは",
    "thanks": "ありがとう",
}

_UNSUPPORTED_BY_TYPE: dict[str, str] = {
    "image": (
        "画像での症状の相談は、まだ対応していません。"
        "対応を進めていますので、今しばらくお待ちください。\n"
        "ひとまず、お困りの症状をテキストでお送りください。"
        "例：頭が痛い、咳が出る"
    ),
    "audio": (
        "音声メッセージでの相談は、まだ対応していません。"
        "今後の対応を予定しています。\n"
        "お手数ですが、症状をテキストでお知らせください。"
    ),
    "video": (
        "動画メッセージは、まだ症状の相談に使えません。"
        "お困りの内容をテキストでお送りください。"
    ),
    "file": (
        "ファイルの送付には対応していません。"
        "症状やご質問はテキストでお知らせください。"
    ),
    "location": (
        "位置情報の送付には対応していません。"
        "お困りの症状をテキストでお送りください。"
    ),
}

_DEFAULT_UNSUPPORTED = (
    "この形式のメッセージには、まだ対応していません。"
    "お身体の症状やご質問は、テキストでお送りください。"
    "例：頭が痛い"
)

STICKER_UNSUPPORTED_REPLY = (
    "スタンプありがとうございます！"
    "お身体の症状については、まだスタンプでは相談を受けられません。"
    "お手数ですが、「頭が痛い」のようにテキストでお送りください。"
)

# 後方互換（旧定数）
NON_TEXT_HINT = _DEFAULT_UNSUPPORTED


def build_non_text_reply(message_type: str | None) -> str:
    """メッセージ種別ごとの「未対応」案内文。"""
    key = (message_type or "").strip().lower()
    return _UNSUPPORTED_BY_TYPE.get(key, _DEFAULT_UNSUPPORTED)


def _intent_from_keyword(keyword: str) -> str | None:
    kw = (keyword or "").strip()
    if not kw:
        return None
    intent = classify_concierge_intent(kw)
    if intent in _SYNTHETIC_BY_INTENT:
        return intent
    if _GREETING_KEYWORD_RE.search(kw):
        return "greeting"
    if _THANKS_KEYWORD_RE.search(kw):
        return "thanks"
    return None


def _intent_from_keywords(keywords: list[Any]) -> str | None:
    for raw in keywords:
        intent = _intent_from_keyword(str(raw or ""))
        if intent:
            return intent
    combined = " ".join(str(k or "").strip() for k in keywords if str(k or "").strip())
    if combined:
        intent = classify_concierge_intent(combined)
        if intent in _SYNTHETIC_BY_INTENT:
            return intent
        if _GREETING_KEYWORD_RE.search(combined):
            return "greeting"
        if _THANKS_KEYWORD_RE.search(combined):
            return "thanks"
    return None


def _expand_variant_groups(raw: dict[str, Any], base: dict[str, dict[str, str]]) -> None:
    groups = raw.get("_meta", {}).get("variant_groups")
    if not isinstance(groups, list):
        return
    for group in groups:
        if not isinstance(group, dict):
            continue
        packages = group.get("packages")
        base_ids = group.get("base_ids")
        if not isinstance(packages, list) or len(packages) < 2:
            continue
        if not isinstance(base_ids, dict):
            continue
        primary = str(packages[0])
        try:
            primary_base = int(str(base_ids[primary]))
        except (TypeError, ValueError):
            continue
        primary_map = base.get(primary, {})
        for sticker_id, text in primary_map.items():
            try:
                index = int(sticker_id) - primary_base
            except ValueError:
                continue
            for sibling in packages[1:]:
                sibling_pkg = str(sibling)
                try:
                    sibling_base = int(str(base_ids[sibling_pkg]))
                except (TypeError, ValueError, KeyError):
                    continue
                sibling_id = str(sibling_base + index)
                base.setdefault(sibling_pkg, {})[sibling_id] = text


@lru_cache(maxsize=1)
def load_known_sticker_text() -> dict[str, dict[str, str]]:
    """data/line_official_sticker_intents.json を読み込み、多言語パックを展開。"""
    path = _STICKER_MAP_PATH
    if not path.is_file():
        logger.warning("LINE sticker map not found path=%s", path)
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("LINE sticker map load failed path=%s err=%s", path, exc)
        return {}
    if not isinstance(raw, dict):
        return {}

    result: dict[str, dict[str, str]] = {}
    for package_id, mappings in raw.items():
        if package_id.startswith("_") or not isinstance(mappings, dict):
            continue
        pack = result.setdefault(str(package_id), {})
        for sticker_id, text in mappings.items():
            if text:
                pack[str(sticker_id)] = str(text)
    _expand_variant_groups(raw, result)
    return result


def _lookup_known_sticker(package_id: str, sticker_id: str) -> str | None:
    pack = load_known_sticker_text().get(str(package_id or "").strip())
    if not pack:
        return None
    return pack.get(str(sticker_id or "").strip())


def _accept_known_sticker_text(text: str) -> str | None:
    known = (text or "").strip()
    if not known:
        return None
    intent = classify_concierge_intent(known)
    if intent in _SYNTHETIC_BY_INTENT:
        return known
    if _GREETING_KEYWORD_RE.search(known):
        return known
    if _THANKS_KEYWORD_RE.search(known):
        return known
    return None


def try_resolve_sticker_as_text(message: dict[str, Any]) -> str | None:
    """
    挨拶・感謝スタンプをテキストに変換できる場合のみ返す。
    変換できれば既存のテキスト相談フローへ渡せる。
    """
    if message.get("type") != "sticker":
        return None

    keywords = message.get("keywords")
    if isinstance(keywords, list) and keywords:
        intent = _intent_from_keywords(keywords)
        if intent:
            first_kw = next(
                (str(k).strip() for k in keywords if str(k or "").strip()),
                _SYNTHETIC_BY_INTENT[intent],
            )
            if intent == "greeting" and _GREETING_KEYWORD_RE.search(first_kw):
                return first_kw
            if intent == "thanks" and _THANKS_KEYWORD_RE.search(first_kw):
                return first_kw
            return _SYNTHETIC_BY_INTENT[intent]

    known = _lookup_known_sticker(
        str(message.get("packageId") or ""),
        str(message.get("stickerId") or ""),
    )
    if known:
        return _accept_known_sticker_text(known)
    return None
