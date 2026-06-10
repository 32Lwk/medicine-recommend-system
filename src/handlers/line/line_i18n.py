"""
LINE Flex Message 用 UI 文言（チャット本体 i18n とは別の表示ラベル）。
"""
from __future__ import annotations

_SUPPORTED = frozenset({"ja", "en", "ko", "zh"})

_STRINGS: dict[str, dict[str, str]] = {
    "ja": {
        "advice_header": "あなたに合わせたアドバイス",
        "advice_alt": "あなたに合わせたアドバイス",
        "carousel_alt": "おすすめの医薬品",
        "efficacy_label": "効能・効果",
        "reason_label": "推奨理由",
        "score_label": "おすすめ度",
        "usage_prefix": "使用上の注意",
        "footer_caution": "用法用量を守り、症状が続く場合は医師・薬剤師にご相談ください。",
        "intro_template": "あなたに合った{medicine_type}の候補を{count}つご用意しました。",
        "rank_prefix": "第",
        "rank_suffix": "位",
        "score_high": "高",
        "score_medium": "中",
        "score_low": "低",
        "pharmacist_fallback": "適切な市販薬が見つかりませんでした。症状に応じて医師・薬剤師にご相談ください。",
        "bullet_fallback_angle": "おすすめ",
    },
    "en": {
        "advice_header": "Personalized advice",
        "advice_alt": "Personalized advice",
        "carousel_alt": "Recommended medicines",
        "efficacy_label": "Efficacy",
        "reason_label": "Why recommended",
        "score_label": "Match score",
        "usage_prefix": "Precautions",
        "footer_caution": "Follow dosage directions. Consult a doctor or pharmacist if symptoms persist.",
        "intro_template": "Here are {count} {medicine_type} options for you.",
        "rank_prefix": "#",
        "rank_suffix": "",
        "score_high": "High",
        "score_medium": "Medium",
        "score_low": "Low",
        "pharmacist_fallback": "We could not find suitable OTC options. Please consult a doctor or pharmacist.",
        "bullet_fallback_angle": "Recommended",
    },
}


def normalize_line_lang(lang: str | None) -> str:
    if not lang:
        return "ja"
    code = (lang or "ja").strip().lower().split("-")[0]
    if code in _STRINGS:
        return code
    return "ja"


def get_line_ui_strings(lang: str | None) -> dict[str, str]:
    code = normalize_line_lang(lang)
    base = dict(_STRINGS["ja"])
    base.update(_STRINGS.get(code, {}))
    return base


def format_intro(ui: dict[str, str], *, medicine_type: str, count: int) -> str:
    template = ui.get("intro_template", _STRINGS["ja"]["intro_template"])
    mt = medicine_type or "OTC医薬品"
    return template.format(medicine_type=mt, count=count)


def format_rank(ui: dict[str, str], rank: int) -> str:
    return f"{ui.get('rank_prefix', '第')}{rank}{ui.get('rank_suffix', '位')}"


def format_score_label(ui: dict[str, str], level: str, percent: int) -> str:
    level_map = {
        "high": ui.get("score_high", "高"),
        "medium": ui.get("score_medium", "中"),
        "low": ui.get("score_low", "低"),
    }
    label = level_map.get(level, level_map["medium"])
    return f" {label} ({percent}%)"


def carousel_alt_text(ui: dict[str, str], count: int) -> str:
    base = ui.get("carousel_alt", "おすすめの医薬品")
    return f"{base}（{count}件）" if count else base
