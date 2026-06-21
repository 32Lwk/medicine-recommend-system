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
        "symptoms_label": "推定症状",
        "personal_advice_label": "あなたへのひとこと",
        "candidate_summary_label": "候補の概要",
        "medicines_intro_label": "おすすめの市販薬",
        "medicines_summary_with_symptoms": "{symptoms}に合わせて、{medicine_type}を{count}つご提案します。",
        "medicines_summary_no_symptoms": "{medicine_type}を{count}つご提案します。",
        "medicines_same_family_hint": "いずれも{family}の製品です。用法用量を守ってお選びください。",
        "medicines_group_suffix": "があります。体質や症状に合うものをお選びください。",
        "medicines_group_joiner": "と",
        "medicines_difference_fallback": "成分や作用に違いがあります。下のカードで各製品の特徴をご確認ください。",
        "medicines_carousel_hint": "各製品の効能・用法・注意点は下のカードでご確認いただけます。",
        "personalized_advice_fallback": "{symptoms}の症状ですね。お身体の状態を考慮して、安全に使える市販薬を選んでいます。",
        "ingredients_label": "主な成分",
        "web_detail_hint": "※ 成分重複の詳細・使用上の注意・スコア内訳は下の「詳細をブラウザで見る」から確認できます。",
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
        "web_continue_label": "詳細をブラウザで見る",
        "web_continue_title": "詳細をブラウザで確認",
        "web_continue_body": "これまでの相談内容と推奨結果をブラウザに引き継ぎます（30分・1回限り）。",
        "web_continue_details": "Webでは成分重複警告、使用上の注意、スコア内訳、追加質問への回答などを確認できます。",
        "web_handoff_failed": "引き継ぎを開始できませんでした。しばらくしてから再度お試しください。",
        "pharmacist_requested_message": "薬剤師対応を要請しました。しばらくお待ちください。",
        "pharmacist_confirm_title": "薬剤師に相談",
        "pharmacist_confirm_body": (
            "「薬剤師要請」は将来的な実装を想定したデモ機能であり、"
            "実際に薬剤師が応答・返信する体制が常時稼働しているわけではありません。"
            "それでも要請しますか？"
        ),
        "pharmacist_confirm_yes": "要請する",
        "pharmacist_confirm_no": "キャンセル",
        "pharmacist_confirm_aborted": "キャンセルしました。",
        "pharmacist_request_failed": "要請に失敗しました。",
        "pharmacist_cancel_label": "要請を取り消す",
        "pharmacist_cancelled_message": "薬剤師要請を取り消しました。引き続き AI がお答えします。",
        "pharmacist_cancel_not_pending": "薬剤師要請は見つかりませんでした。",
        "pharmacist_return_ai_label": "AI自動応答に戻す",
        "pharmacist_return_ai_message": "AI 自動応答に戻しました。症状やご質問をお送りください。",
        "pharmacist_return_not_available": "操作できませんでした。",
        "pharmacist_return_still_pending": "薬剤師確認中です。「要請を取り消す」を選んでください。",
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
        "symptoms_label": "Estimated symptoms",
        "personal_advice_label": "Personal note",
        "candidate_summary_label": "Candidate summary",
        "medicines_intro_label": "Recommended OTC options",
        "medicines_summary_with_symptoms": "For {symptoms}, here are {count} {medicine_type} options.",
        "medicines_summary_no_symptoms": "Here are {count} {medicine_type} options.",
        "medicines_same_family_hint": "All are {family} products. Follow dosage directions when choosing.",
        "medicines_group_suffix": " are included. Pick what fits your body and symptoms.",
        "medicines_group_joiner": " and ",
        "medicines_difference_fallback": "They differ in ingredients and effects. See the cards below for details.",
        "medicines_carousel_hint": "See each product's efficacy, usage, and precautions in the cards below.",
        "personalized_advice_fallback": "We understand {symptoms} can be tough. These OTC options were chosen with your safety in mind.",
        "ingredients_label": "Main ingredients",
        "web_detail_hint": "See overlap warnings, precautions, and score details via “View details in browser” below.",
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
        "web_continue_label": "View details in browser",
        "web_continue_title": "View full details on the web",
        "web_continue_body": "Transfer this chat and recommendations to your browser (30 min, one-time).",
        "web_continue_details": "On the web you can review overlap warnings, usage notes, score breakdowns, and follow-up answers.",
    },
    "ko": {
        "web_continue_label": "브라우저에서 계속",
        "web_continue_title": "웹에서 대화 이어가기",
        "web_continue_body": "지금까지의 상담과 추천 결과를 브라우저로 이어갑니다(30분·1회 한정).",
    },
    "zh": {
        "web_continue_label": "在浏览器中继续",
        "web_continue_title": "在网页上继续对话",
        "web_continue_body": "将迄今的咨询内容与推荐结果转移到浏览器（30分钟·仅限一次）。",
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


def format_medicines_summary(
    ui: dict[str, str],
    *,
    medicine_type: str,
    count: int,
    symptoms: list[str],
) -> str:
    mt = medicine_type or "OTC医薬品"
    if symptoms:
        template = ui.get(
            "medicines_summary_with_symptoms",
            _STRINGS["ja"]["medicines_summary_with_symptoms"],
        )
        return template.format(symptoms="・".join(symptoms[:4]), medicine_type=mt, count=count)
    template = ui.get(
        "medicines_summary_no_symptoms",
        _STRINGS["ja"]["medicines_summary_no_symptoms"],
    )
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
