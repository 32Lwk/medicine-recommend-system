"""
HTMLフォーマッター

エラー表示、エスカレーション表示など、プレゼンテーション層のHTML生成を担う。
チャット内のエラー・注意・通知UIは chat-status-card コンポーネントで統一する。
"""

import html
import json
from typing import Dict, List, Optional

ERROR_MESSAGES: Dict[str, Dict] = {
    'no_candidates': {
        'title': '医薬品が見つかりませんでした',
        'main_message': '入力された症状に対して、適切な市販薬が見つかりませんでした。',
        'recommendations': [
            '症状をより具体的に記述してください（例：痛みの部位、程度、継続期間など）',
            '症状が1週間以上続いている場合は、医療機関を受診することをお勧めします',
            '重症の症状がある場合は、速やかに医師の診察を受けてください',
        ],
    },
    'rule_based_error': {
        'title': '推奨システムエラー',
        'main_message': '症状の解析中にエラーが発生しました。',
        'recommendations': [
            '症状を別の表現で入力し直してください',
            '具体的な症状名（例：頭痛、発熱、のどの痛みなど）を含めて記述してください',
            '症状が続く場合は、医療機関を受診することをお勧めします',
        ],
    },
    'missing_critical_info': {
        'title': '症状が検出されませんでした',
        'main_message': '入力されたテキストから症状を検出できませんでした。',
        'recommendations': [
            '具体的な症状名を含めて記述してください（例：「頭が痛い」「熱がある」など）',
            '症状の部位や程度も記述すると、より適切な推奨が可能です',
            '症状が続く場合は、医療機関を受診することをお勧めします',
        ],
    },
    'unknown_error': {
        'title': 'システムエラー',
        'main_message': '推奨システムでエラーが発生しました。',
        'recommendations': [
            '症状を再度入力してください',
            '症状が続く場合は、医療機関を受診することをお勧めします',
            '問題が解決しない場合は、薬剤師または登録販売者にご相談ください',
        ],
    },
}

_MEDICAL_ADVICE_ITEMS = [
    '症状が1週間以上続いている場合',
    '症状が悪化している場合',
    '高熱（38.5度以上）が続く場合',
    '重症の症状がある場合（激しい痛み、呼吸困難、意識障害など）',
    '妊娠中・授乳中の場合',
    '7歳未満のお子様の場合',
]

_VARIANT_ICONS = {
    'error': '⚠️',
    'caution': '⚠️',
    'notice': 'ℹ️',
    'security': '🚨',
    'critical': '⚠️',
}


def _feedback_json(feedback_data: Dict) -> str:
    return html.escape(json.dumps(feedback_data, ensure_ascii=False))


def _list_html(items: List[str], class_name: str = 'chat-status-card__list') -> str:
    if not items:
        return ''
    lis = ''.join(f'<li>{html.escape(item)}</li>' for item in items)
    return f'<ul class="{class_name}">{lis}</ul>'


def format_status_card(
    variant: str,
    title: str,
    body_html: str = '',
    hints: Optional[List[str]] = None,
    subtitle: str = '',
    technical_details: str = '',
    extra_sections_html: str = '',
    footer_html: str = '',
    aria_label: Optional[str] = None,
) -> str:
    """統一ステータスカード。footer_html でフィードバックを同一カード内に収める。"""
    icon = _VARIANT_ICONS.get(variant, '⚠️')
    escaped_title = html.escape(title)
    label = html.escape(aria_label or title)
    subtitle_html = (
        f'<p class="chat-status-card__subtitle">{html.escape(subtitle)}</p>'
        if subtitle else ''
    )
    hints_html = _list_html(hints or [], 'chat-status-card__hints')
    tech_html = ''
    if technical_details:
        escaped_tech = html.escape(technical_details)
        tech_html = (
            '<details class="chat-status-card__details">'
            '<summary>詳細情報（サポート用）</summary>'
            f'<pre class="chat-status-card__tech">{escaped_tech}</pre>'
            '</details>'
        )
    footer_block = (
        f'<div class="chat-status-card__footer">{footer_html}</div>'
        if footer_html else ''
    )

    return (
        f'<div class="chat-status-card chat-status-card--{variant}" '
        f'role="alert" aria-label="{label}">'
        f'<div class="chat-status-card__header">'
        f'<span class="chat-status-card__icon" aria-hidden="true">{icon}</span>'
        f'<h4 class="chat-status-card__title">{escaped_title}</h4>'
        f'</div>'
        f'{subtitle_html}'
        f'<div class="chat-status-card__body">'
        f'{body_html}'
        f'{hints_html}'
        f'{extra_sections_html}'
        f'</div>'
        f'{tech_html}'
        f'{footer_block}'
        f'</div>'
    )


def format_feedback_buttons(
    feedback_data: Dict,
    question: str = 'このメッセージは役に立ちましたか？',
    include_bug_report: bool = False,
    bug_report_attrs: str = '',
) -> str:
    """カード内フッター用フィードバック。"""
    feedback_json = _feedback_json(feedback_data)
    bug_btn = ''
    if include_bug_report:
        bug_btn = (
            f'<button type="button" class="bug-report-btn chat-status-card__btn '
            f'chat-status-card__btn--report" onclick="handleSecurityReportFromButton(this)" '
            f'{bug_report_attrs}>不具合を報告</button>'
        )
    return (
        f'<div class="feedback-buttons chat-status-card__feedback">'
        f'<p class="feedback-question chat-status-card__footer-prompt">{html.escape(question)}</p>'
        f'<div class="feedback-buttons-container chat-status-card__actions">'
        f'<button type="button" class="feedback-btn-positive chat-status-card__btn '
        f'chat-status-card__btn--positive" onclick="handlePositiveFeedback({feedback_json})">'
        f'役に立った</button>'
        f'<button type="button" class="feedback-btn-negative chat-status-card__btn '
        f'chat-status-card__btn--negative" onclick="handleNegativeFeedback({feedback_json})">'
        f'役に立たなかった</button>'
        f'{bug_btn}'
        f'</div>'
        f'</div>'
    )


def format_diagnosis_notification(
    diagnosis_message_html: str,
    feedback_data: Dict,
    bug_report_attrs: str = '',
) -> str:
    """診断名検出時の通知（1枚のカード）。"""
    hints = [
        '診断名が分かっている場合は、市販薬の選び方は医師または薬剤師にご相談ください',
        'お近くの医療機関・薬局でも相談できます',
    ]
    footer = format_feedback_buttons(
        feedback_data,
        question='このご案内は分かりやすかったですか？',
        include_bug_report=True,
        bug_report_attrs=bug_report_attrs,
    )
    return format_status_card(
        variant='notice',
        title='診断名が含まれています',
        subtitle='市販薬の自動推奨は行えません。医療機関への相談をお勧めします。',
        body_html=f'<div class="chat-status-card__message">{diagnosis_message_html}</div>',
        hints=hints,
        footer_html=footer,
        aria_label='診断名が含まれています',
    )


def format_medicine_type_notice(
    consultation_html: str,
    feedback_data: Dict,
    bug_report_attrs: str = '',
) -> str:
    """医薬品種類が判定できない場合の通知。"""
    hints = [
        '症状をより具体的に入力してください（例：「頭が痛い」「のどが痛い」）',
        '1週間以上続く場合は医療機関を受診してください',
    ]
    footer = format_feedback_buttons(
        feedback_data,
        question='このご案内は分かりやすかったですか？',
        include_bug_report=True,
        bug_report_attrs=bug_report_attrs,
    )
    return format_status_card(
        variant='caution',
        title='症状から医薬品を選べませんでした',
        subtitle='入力内容を変えるか、薬剤師にご相談ください。',
        body_html=f'<div class="chat-status-card__message">{consultation_html}</div>',
        hints=hints,
        footer_html=footer,
    )


def format_system_error(
    title: str = '一時的なエラーが発生しました',
    message: str = '処理中に問題が発生しました。しばらく時間をおいてからもう一度お試しください。',
    hints: Optional[List[str]] = None,
) -> str:
    default_hints = [
        'しばらく時間をおいて、もう一度お試しください',
        '症状をより具体的に入力してください（例：「頭が痛い」「熱がある」）',
        '問題が続く場合は、薬剤師にご相談ください',
    ]
    return format_status_card(
        variant='error',
        title=title,
        subtitle=message,
        hints=hints or default_hints,
    )


def format_error_display(
    error_type: str,
    error_details: Dict,
    user_message: str,
    include_feedback_buttons: bool = True,
) -> str:
    reason = error_details.get('reason', 'ルールベース推奨でエラーが発生しました')
    technical_details = error_details.get('technical_details', '')
    error_info = ERROR_MESSAGES.get(error_type, ERROR_MESSAGES['unknown_error'])
    escaped_user_message = html.escape(user_message)
    escaped_reason = html.escape(reason)

    body = (
        f'<p class="chat-status-card__message">{html.escape(error_info["main_message"])}</p>'
        f'<p class="chat-status-card__reason"><strong>状況:</strong> {escaped_reason}</p>'
    )
    extra = (
        '<section class="chat-status-card__section">'
        '<h5 class="chat-status-card__section-title">次にできること</h5>'
        + _list_html(error_info['recommendations'])
        + '</section>'
        '<section class="chat-status-card__section">'
        '<h5 class="chat-status-card__section-title">医師への相談をお勧めします</h5>'
        '<p class="chat-status-card__section-desc">'
        '次のいずれかに当てはまる場合は、医療機関（病院・クリニック）を受診してください。'
        '</p>'
        + _list_html(_MEDICAL_ADVICE_ITEMS)
        + '</section>'
    )
    footer = ''
    if include_feedback_buttons:
        footer = format_feedback_buttons(
            {
                'user_message': escaped_user_message,
                'ai_response': error_info['main_message'],
                'security_score': None,
                'error_type': error_type,
            },
            question='このご案内は分かりやすかったですか？',
        )

    return format_status_card(
        variant='caution',
        title=error_info['title'],
        body_html=body,
        extra_sections_html=extra,
        technical_details=technical_details,
        footer_html=footer,
    )


def format_escalation_display(
    doctor_consultation: str,
    medicine_type: str,
    algorithm: str,
    user_message: str,
    include_feedback_buttons: bool = True,
) -> str:
    escaped_user_message = html.escape(user_message)
    escaped_consultation = html.escape(doctor_consultation)
    body = (
        f'<p class="chat-status-card__message escalation-warning">'
        f'<strong>{escaped_consultation}</strong></p>'
        f'<p class="chat-status-card__meta"><strong>医薬品の種類:</strong> '
        f'{html.escape(medicine_type)}</p>'
    )
    hints = [
        '速やかに医師の診察を受けてください',
        '市販薬での自己治療は推奨されません',
        '症状が悪化する場合は救急医療機関へ',
    ]
    footer = ''
    if include_feedback_buttons:
        footer = format_feedback_buttons(
            {
                'user_message': escaped_user_message,
                'ai_response': escaped_consultation,
                'security_score': None,
            },
            question='この重要な注意事項は分かりやすかったですか？',
        )
    return format_status_card(
        variant='critical',
        title='重要な注意事項',
        subtitle='市販薬の使用は控え、医師にご相談ください。',
        body_html=body,
        hints=hints,
        footer_html=footer,
    )
