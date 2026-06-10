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
        "status_critical_title": "重要なお知らせ",
        "status_caution_title": "ご確認ください",
        "status_notice_title": "追加でお聞きしたいこと",
        "status_info_title": "ご案内",
        "status_error_title": "お知らせ",
        "status_escalation_subtitle": "市販薬の使用は控え、医師にご相談ください。",
        "status_questions_intro": "より適切なご提案のため、次の点を教えてください。",
        "status_hints_label": "次にできること",
        "status_critical_hint_1": "お一人で抱え込まず、専門の相談窓口にご連絡ください。",
        "status_critical_hint_2": "緊急の場合は救急・医療機関へ相談してください。",
        "status_escalation_hint_1": "速やかに医師の診察を受けてください。",
        "status_escalation_hint_2": "市販薬での自己治療は推奨されません。",
        "status_caution_hint_1": "症状をより具体的に入力し直してください。",
        "status_caution_hint_2": "1週間以上続く場合は医療機関を受診してください。",
        "feedback_positive_label": "👍 役に立った",
        "feedback_negative_label": "👎 役に立たなかった",
        "feedback_positive_display": "役に立った",
        "feedback_negative_display": "役に立たなかった",
        "feedback_thank_you": "フィードバックありがとうございます！",
        "feedback_already_submitted": "すでに送信済みです。",
        "feedback_expired": "評価の有効期限が切れました。",
        "feedback_submit_failed": "送信に失敗しました。しばらくして再度お試しください。",
        "processing_busy": "現在処理中です。完了後に再度お送りください。",
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
        "status_critical_title": "Important notice",
        "status_caution_title": "Please note",
        "status_notice_title": "A few more questions",
        "status_info_title": "Information",
        "status_error_title": "Notice",
        "status_escalation_subtitle": "Avoid self-medicating with OTC drugs; consult a doctor.",
        "status_questions_intro": "To recommend safely, please tell us:",
        "status_hints_label": "What you can do next",
        "status_critical_hint_1": "Reach out to a professional support service.",
        "status_critical_hint_2": "In an emergency, contact emergency medical services.",
        "status_escalation_hint_1": "See a doctor promptly.",
        "status_escalation_hint_2": "OTC self-medication is not recommended.",
        "status_caution_hint_1": "Try describing your symptoms more specifically.",
        "status_caution_hint_2": "If symptoms last over a week, see a doctor.",
        "feedback_positive_label": "👍 Helpful",
        "feedback_negative_label": "👎 Not helpful",
        "feedback_positive_display": "Helpful",
        "feedback_negative_display": "Not helpful",
        "feedback_thank_you": "Thank you for your feedback!",
        "feedback_already_submitted": "Already submitted.",
        "feedback_expired": "This feedback link has expired.",
        "feedback_submit_failed": "Could not submit feedback. Please try again later.",
        "processing_busy": "A request is already in progress. Please try again after it completes.",
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
