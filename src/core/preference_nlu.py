"""
ユーザー嗜好の GPT 抽出（症状 NLU と並列実行想定）
"""
from __future__ import annotations

import logging
import os
from typing import Any, Dict, Optional

from openai import OpenAI

from src.core.dictionary_loader import load_preference_keyword_catalog
from src.core.user_detection import preference_context_text

logger = logging.getLogger(__name__)

PREFERENCE_FIELDS = (
    "ingredient_balance",
    "ease_of_taking",
    "accompanying_symptoms",
    "prefers_kampo",
    "prefers_not_kampo",
    "avoid_drowsiness",
    "avoid_dry_mouth",
    "prefer_fewer_daily_doses",
    "prefer_nasal_route",
    "avoid_nasal_route",
)

_PROMPT_TEMPLATES = {
    "ja": """あなたは市販薬推奨の嗜好分類器です。ユーザーの発話から「薬選びの希望」を抽出してください。
症状そのもの（例: 今口が渇いている）と、薬の希望（例: 口渇が少ない薬がいい）は区別してください。後者のみ嗜好として扱います。

【ユーザー入力】
{text}

【参照キーワード例（各カテゴリの意味）】
{catalog_summary}

【出力ルール】
- 各フィールドについて value (true/false), confidence (0.0-1.0), evidence (短い引用またはnull)
- preferred_max_daily_doses は 1, 2, 3 のいずれかまたは null
- 該当しない場合は value=false, confidence=0.0
- prefers_kampo と prefers_not_kampo が両方 true の場合は prefers_not_kampo のみ true

JSON形式:
{{
  "user_preferences": {{
    "avoid_drowsiness": {{"value": false, "confidence": 0.0, "evidence": null}},
    "avoid_dry_mouth": {{"value": false, "confidence": 0.0, "evidence": null}},
    "prefer_nasal_route": {{"value": false, "confidence": 0.0, "evidence": null}},
    "avoid_nasal_route": {{"value": false, "confidence": 0.0, "evidence": null}},
    "prefer_fewer_daily_doses": {{"value": false, "confidence": 0.0, "evidence": null}},
    "preferred_max_daily_doses": {{"value": null, "confidence": 0.0, "evidence": null}},
    "prefers_kampo": {{"value": false, "confidence": 0.0, "evidence": null}},
    "prefers_not_kampo": {{"value": false, "confidence": 0.0, "evidence": null}},
    "ingredient_balance": {{"value": false, "confidence": 0.0, "evidence": null}},
    "ease_of_taking": {{"value": false, "confidence": 0.0, "evidence": null}},
    "accompanying_symptoms": {{"value": false, "confidence": 0.0, "evidence": null}}
  }}
}}
""",
    "en": """You are a preference classifier for OTC medicine recommendations. Extract medicine-selection preferences (not chief complaints as symptoms).
Distinguish "my mouth is dry now" (symptom) from "I want a drug with less dry mouth" (preference).

User input:
{text}

Keyword hints:
{catalog_summary}

Return JSON with user_preferences: each field has value (bool), confidence (0-1), evidence (short quote or null).
preferred_max_daily_doses value: 1, 2, 3 or null.
If prefers_kampo and prefers_not_kampo both true, keep only prefers_not_kampo true.
""",
}


def _i18n_preference_prompt(lang_label: str) -> str:
    return f"""You are a preference classifier for OTC medicine recommendations in Japan.
The user may write in {lang_label}. Extract medicine-selection preferences (not chief complaints as symptoms).
Distinguish current symptoms from drug preferences (e.g. "mouth is dry now" vs "want less dry-mouth side effect").

User input:
{{text}}

Keyword hints (Japanese labels; map user language to these fields):
{{catalog_summary}}

Return JSON with user_preferences: each field has value (bool), confidence (0-1), evidence (short quote or null).
preferred_max_daily_doses value: 1, 2, 3 or null.
If prefers_kampo and prefers_not_kampo both true, keep only prefers_not_kampo true.
"""


_PROMPT_TEMPLATES["ko"] = _i18n_preference_prompt("Korean")
_PROMPT_TEMPLATES["zh"] = _i18n_preference_prompt("Chinese")


def _catalog_summary_for_prompt(max_keywords_per_field: int = 12) -> str:
    catalog = load_preference_keyword_catalog()
    lines = []
    for cat in catalog.get("categories", []):
        field = cat.get("preference_field", "")
        desc = cat.get("description_ja", "")
        kws = cat.get("gpt_reference_keywords", [])[:max_keywords_per_field]
        lines.append(f"- {field}: {desc} 例: {', '.join(kws)}")
    return "\n".join(lines)


def extract_preferences_with_gpt(
    user_text: str,
    user_info: Optional[Dict[str, Any]],
    client: Optional[OpenAI],
    detected_language: str = "ja",
    *,
    session_id: Optional[str] = None,
) -> Dict[str, Any]:
    """嗜好 GPT 抽出。失敗時は空 dict。"""
    if client is None:
        return {}

    text = preference_context_text(user_text or "", user_info)
    if not text.strip():
        return {}

    from src.core.i18n_prompts import normalize_lang

    lang = normalize_lang(detected_language)
    if lang not in _PROMPT_TEMPLATES:
        lang = "ja"
    template = _PROMPT_TEMPLATES[lang]
    prompt = template.format(text=text, catalog_summary=_catalog_summary_for_prompt())

    timeout_sec = float(os.getenv("PREFERENCE_NLU_TIMEOUT_SEC", "8"))

    try:
        from src.security.security_validator import validate_user_input
        from src.security.security_config import should_block_input

        is_safe, risk_score, _, sanitized = validate_user_input(text, context="symptom")
        if should_block_input(risk_score):
            logger.warning("嗜好NLU: 入力ブロック risk=%s", risk_score)
            return {}
        text_for_prompt = sanitized or text
        prompt = template.format(text=text_for_prompt, catalog_summary=_catalog_summary_for_prompt())

        from src.core.llm_client import chat_completion_create

        response = chat_completion_create(
            client,
            model_role="nlu",
            path="preference_nlu.extract",
            messages=[
                {
                    "role": "system",
                    "content": "Return only valid JSON. Classify medicine preferences, not symptoms.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,
            max_tokens=500,
            response_format={"type": "json_object"},
            timeout=timeout_sec,
        )
        from src.core.llm_client import extract_completion_text
        from src.security.json_validator import safe_json_parse

        result_text = extract_completion_text(response)
        if not result_text:
            return {}
        parsed = safe_json_parse(result_text, schema="preference_analysis")
        return parsed.get("user_preferences") or {}
    except Exception as e:
        logger.warning("嗜好NLU GPT 失敗: %s", e)
        return {}
