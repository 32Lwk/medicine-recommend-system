"""
言語検出ユーティリティ

優先順位（返信言語）:
1. ユーザー入力からの検出（明確な言語シグナルがある場合）
2. session.detected_language（直前までの会話言語）
3. session.language（LINE プロフィール等のフォールバック）
4. line_profile.language
5. ja（既定）
"""
from __future__ import annotations

import re
from typing import Any, Optional

from src.core.i18n_prompts import normalize_lang

_AMBIGUOUS_ASCII = frozenset({
    "ok", "okay", "yes", "no", "y", "n", "hi", "hey", "thx", "thanks",
    "1", "2", "3", "4", "5",
})


def detect_language(text, session_language=None):
    """
    テキストから言語を自動検出

    Args:
        text (str): 検出対象のテキスト
        session_language (str): セッションの既存言語情報（曖昧な短文の補助）

    Returns:
        str: 検出された言語コード ('ja', 'en', 'ko', 'zh')
    """
    hint = normalize_lang(session_language) if session_language else None

    if not text or not isinstance(text, str):
        return hint or "ja"

    text = text.strip()
    if not text:
        return hint or "ja"

    # セッションの既存言語情報がある場合は優先的に考慮
    if hint and hint != "en":
        # 既存言語が日本語の場合、短いテキストは日本語として扱う
        if hint == "ja" and len(text) <= 10:
            # 日本語の一般的な医学用語・症状名リスト
            japanese_medical_terms = [
                "精神疾患", "うつ病", "統合失調症", "不安障害", "パニック障害",
                "頭痛", "腹痛", "発熱", "咳", "鼻水", "下痢", "便秘", "吐き気",
                "不眠", "倦怠感", "疲労感", "ストレス", "イライラ", "不安",
                "風邪", "インフルエンザ", "花粉症", "アレルギー", "湿疹",
                "肩こり", "腰痛", "関節痛", "筋肉痛", "めまい", "動悸",
            ]
            if text in japanese_medical_terms:
                return "ja"

    # 韓国語の文字が含まれているかチェック（ハングル）- 最初にチェック（重複がないため）
    if re.search(r"[\uAC00-\uD7AF]", text):
        return "ko"

    # 中国語の文字が含まれているかチェック（簡体字・繁体字）
    chinese_chars = re.search(r"[\u4E00-\u9FFF]", text)
    if chinese_chars:
        # ひらがなやカタカナが含まれていれば日本語
        if re.search(r"[\u3040-\u309F\u30A0-\u30FF]", text):
            return "ja"

        # 漢字のみの場合の判定を改善
        if len(text) <= 10:
            japanese_medical_terms = [
                "精神疾患", "うつ病", "統合失調症", "不安障害", "パニック障害",
                "頭痛", "腹痛", "発熱", "咳", "鼻水", "下痢", "便秘", "吐き気",
                "不眠", "倦怠感", "疲労感", "ストレス", "イライラ", "不安",
                "風邪", "インフルエンザ", "花粉症", "アレルギー", "湿疹",
                "肩こり", "腰痛", "関節痛", "筋肉痛", "めまい", "動悸",
                "のどの痛み", "喉の痛み", "胃痛", "胸痛", "背痛",
            ]
            if text in japanese_medical_terms:
                return "ja"

            if hint == "ja":
                return "ja"

        return "zh"

    # 日本語の文字が含まれているかチェック（ひらがな、カタカナ）
    if re.search(r"[\u3040-\u309F\u30A0-\u30FF]", text):
        return "ja"

    # デフォルトは英語
    return "en"


def line_profile_language(session: Any) -> Optional[str]:
    """LINE プロフィールの language を正規化して返す。"""
    if not session or not hasattr(session, "get"):
        return None
    prof = session.get("line_profile")
    if not isinstance(prof, dict):
        return None
    raw = prof.get("language")
    if not raw:
        return None
    return normalize_lang(str(raw))


def is_weak_language_signal(text: Optional[str]) -> bool:
    """入力だけでは言語を信頼できない短文・空・記号のみ。"""
    if not text or not isinstance(text, str):
        return True
    t = text.strip()
    if not t:
        return True
    if t.lower() in _AMBIGUOUS_ASCII:
        return True
    if re.search(r"[\u3040-\u309F\u30A0-\u30FF\uAC00-\uD7AF\u4E00-\u9FFF]", t):
        return False
    if len(t) <= 4 and re.match(r"^[\x00-\x7F\d\s\W]+$", t):
        return True
    if not re.search(r"[A-Za-z\u00C0-\u024F]", t) and len(t) <= 8:
        return True
    return False


def language_hint_from_session(session: Any) -> str:
    """フォールバックチェーン: detected > session.language > LINE profile > ja"""
    if session and hasattr(session, "get"):
        detected = session.get("detected_language")
        if detected:
            return normalize_lang(str(detected))
        lang = session.get("language")
        if lang:
            return normalize_lang(str(lang))
        prof_lang = line_profile_language(session)
        if prof_lang:
            return prof_lang
    return "ja"


def resolve_session_language(session: Any) -> str:
    """返信・翻訳に使う現在のセッション言語。"""
    return language_hint_from_session(session)


def resolve_message_language(text: Optional[str], session: Any = None) -> str:
    """
    1メッセージ分の言語を決定（session 更新はしない）。
    入力が曖昧な場合は session / LINE プロフィールのヒントを使う。
    """
    hint = language_hint_from_session(session) if session else "ja"
    if is_weak_language_signal(text):
        return hint
    return normalize_lang(detect_language(text, hint))


def update_session_language_from_message(session: Any, text: Optional[str]) -> str:
    """
    メッセージから言語を決定し session.detected_language を更新する。
    曖昧な入力では既存 detected_language を維持（なければヒント）。
    """
    if not session or not hasattr(session, "__setitem__"):
        return resolve_message_language(text, session)

    if is_weak_language_signal(text):
        existing = session.get("detected_language")
        if existing:
            return normalize_lang(str(existing))
        lang = language_hint_from_session(session)
        session["detected_language"] = lang
        return lang

    lang = normalize_lang(detect_language(text, language_hint_from_session(session)))
    session["detected_language"] = lang
    return lang


def sync_language_from_line_profile(session: Any, session_data: Optional[dict] = None) -> None:
    """
    LINE プロフィール language を session.language に反映（detected_language は上書きしない）。
    """
    prof_lang = line_profile_language(session)
    if not prof_lang:
        if session_data is not None and isinstance(session_data.get("line_profile"), dict):
            raw = session_data["line_profile"].get("language")
            if raw:
                prof_lang = normalize_lang(str(raw))
    if not prof_lang:
        return
    if hasattr(session, "__setitem__"):
        session["language"] = prof_lang
    if session_data is not None:
        session_data["language"] = prof_lang
