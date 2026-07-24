"""Concierge 技術 FAQ 出力のサニタイズ（env 名・メタ・内部パス除去）。"""
from __future__ import annotations

import re
from typing import Optional

from src.utils.sage_message_plain import strip_concierge_prompt_leakage, strip_internal_llm_prefix

_ENV_ASSIGNMENT_RE = re.compile(
    r"`?[A-Z][A-Z0-9_]{2,}=(?:[^\s`]+)`?"
)
_ENV_NAME_RE = re.compile(
    r"\b(?:"
    r"TRANSLATION_PROVIDER|TTS_PROVIDER|CONCIERGE_RAG_PROVIDER|"
    r"DATABASE_URL|OPENAI_API_KEY|GIT_COMMIT|REDIS_URL|"
    r"BEDROCK_KB_ID|STATIC_CDN_BASE_URL|MEDICINE_IMAGE_CDN_BASE|"
    r"CHAT_PIPELINE_V2|INTENT_ROUTER_PRIMARY|AWS_STAGING|PUBLIC_SITE_URL"
    r")\b"
)
_META_PHRASE_RES: tuple[re.Pattern[str], ...] = (
    re.compile(r"環境変数(?:を|の)?(?:参照|確認|読み取|設定)"),
    re.compile(r"(?:server|サーバ)(?:設定|側)(?:を|の)?(?:参照|確認)"),
    re.compile(r"\b\.env\b"),
    re.compile(r"Secrets Manager"),
    re.compile(r"タスク定義(?:を|の)?(?:参照|確認)"),
)
_INTERNAL_PATH_RE = re.compile(
    r"(?:docs/|src/|config/|static/)[a-zA-Z0-9_./\-]+(?:\.(?:py|md|yaml|yml|json|sh))?"
)
_SYMPTOM_BOUNDARY_LINE = (
    "症状やお薬の選び方については、具体的な症状を入力していただければ別途ご案内します。"
)


def _replace_env_assignments(text: str) -> str:
    return _ENV_ASSIGNMENT_RE.sub("", text)


def _replace_env_names(text: str) -> str:
    replacements = (
        ("TRANSLATION_PROVIDER", "翻訳機能"),
        ("TTS_PROVIDER", "読み上げ機能"),
        ("CONCIERGE_RAG_PROVIDER", "ナレッジ検索"),
        ("STATIC_CDN_BASE_URL", "static CDN"),
        ("MEDICINE_IMAGE_CDN_BASE", "医薬品画像 CDN"),
    )
    result = text
    for name, label in replacements:
        result = result.replace(name, label)
    result = _ENV_NAME_RE.sub("", result)
    return result


def _strip_meta_phrases(text: str) -> str:
    result = text
    for pattern in _META_PHRASE_RES:
        result = pattern.sub("", result)
    return result


def _strip_internal_paths(text: str) -> str:
    return _INTERNAL_PATH_RE.sub("公開ドキュメント", text)


def _collapse_whitespace(text: str) -> str:
    result = re.sub(r"[ \t]{2,}", " ", text)
    result = re.sub(r"\n{3,}", "\n\n", result)
    result = re.sub(r" +([。、！？])", r"\1", result)
    return result.strip()


def sanitize_medicine_ask_output(text: str) -> str:
    """Ask 回答から env 名・内部パス等を除去（Concierge と同パターン）。"""
    result = strip_internal_llm_prefix((text or "").strip())
    if not result:
        return result
    result = _replace_env_assignments(result)
    result = _replace_env_names(result)
    result = _strip_internal_paths(result)
    result = _collapse_whitespace(result)
    return strip_concierge_prompt_leakage(result)


def sanitize_concierge_meta_output(
    text: str,
    *,
    intent: str = "",
) -> str:
    """LLM 生成本文から利用者向けに不適切な内部表現を除去する。"""
    result = strip_internal_llm_prefix((text or "").strip())
    if not result:
        return result

    result = _replace_env_assignments(result)
    if intent in ("architecture", "capabilities", "app_about", "doc_changelog"):
        result = _replace_env_names(result)
        result = _strip_meta_phrases(result)
        result = _strip_internal_paths(result)

    result = _collapse_whitespace(result)
    return strip_concierge_prompt_leakage(result)


_SYMPTOM_HINT_RE = re.compile(
    r"頭痛|のど|発熱|咳|腹痛|吐き気|眠れ|風邪|症状|痛い|痛み|くすり|薬"
)
_TECH_MIXED_RE = re.compile(
    r"インフラ|構成|AWS|GCP|デプロイ|Cloud|サーバ|ECS|Translate|Bedrock",
    re.I,
)


def _should_append_symptom_boundary(user_text: str) -> bool:
    ut = (user_text or "").strip()
    if not ut:
        return False
    try:
        from src.utils.input_helpers import has_explicit_symptom_signal, is_symptom_input
    except ImportError:
        return False
    if has_explicit_symptom_signal(ut) or is_symptom_input(ut):
        return True
    return bool(_SYMPTOM_HINT_RE.search(ut) and _TECH_MIXED_RE.search(ut))


def append_symptom_consultation_boundary(text: str, user_text: str) -> str:
    """技術 FAQ に症状が混ざった質問への一行導線（Q4-c）。"""
    body = (text or "").strip()
    if not body or _SYMPTOM_BOUNDARY_LINE in body:
        return body
    if not _should_append_symptom_boundary(user_text):
        return body
    return f"{body}\n\n{_SYMPTOM_BOUNDARY_LINE}"


def concierge_source_hint(intent: str, *, deep: bool = False) -> Optional[str]:
    """深掘り時の参照表示（ファイルパスは出さない）。"""
    if intent == "doc_changelog":
        return "参照: 更新履歴"
    if intent == "architecture" and deep:
        return "参照: 公開技術ドキュメント"
    return None
