"""
HTMLフォーマッター

エラー表示、エスカレーション表示など、プレゼンテーション層のHTML生成を担う。
"""

import html
import json
from typing import Dict

# 症状推奨エラー表示用のメッセージ辞書
ERROR_MESSAGES: Dict[str, Dict] = {
    'no_candidates': {
        'title': '⚠️ 医薬品が見つかりませんでした',
        'main_message': '入力された症状に対して、適切な市販薬が見つかりませんでした。',
        'recommendations': [
            '症状をより具体的に記述してください（例：痛みの部位、程度、継続期間など）',
            '症状が1週間以上続いている場合は、医療機関を受診することをお勧めします',
            '重症の症状がある場合は、速やかに医師の診察を受けてください'
        ]
    },
    'rule_based_error': {
        'title': '⚠️ 推奨システムエラー',
        'main_message': '症状の解析中にエラーが発生しました。',
        'recommendations': [
            '症状を別の表現で入力し直してください',
            '具体的な症状名（例：頭痛、発熱、のどの痛みなど）を含めて記述してください',
            '症状が続く場合は、医療機関を受診することをお勧めします'
        ]
    },
    'missing_critical_info': {
        'title': '⚠️ 症状が検出されませんでした',
        'main_message': '入力されたテキストから症状を検出できませんでした。',
        'recommendations': [
            '具体的な症状名を含めて記述してください（例：「頭が痛い」「熱がある」など）',
            '症状の部位や程度も記述すると、より適切な推奨が可能です',
            '症状が続く場合は、医療機関を受診することをお勧めします'
        ]
    },
    'unknown_error': {
        'title': '⚠️ システムエラー',
        'main_message': '推奨システムでエラーが発生しました。',
        'recommendations': [
            '症状を再度入力してください',
            '症状が続く場合は、医療機関を受診することをお勧めします',
            '問題が解決しない場合は、薬剤師または登録販売者にご相談ください'
        ]
    }
}


def format_error_display(
    error_type: str,
    error_details: Dict,
    user_message: str,
    include_feedback_buttons: bool = True
) -> str:
    """
    症状推奨エラー時のHTMLを生成する。

    Args:
        error_type: エラータイプ
        error_details: エラー詳細辞書 (reason, technical_details 等)
        user_message: ユーザー入力メッセージ
        include_feedback_buttons: フィードバックボタンを含めるか

    Returns:
        HTML文字列
    """
    reason = error_details.get('reason', 'ルールベース推奨でエラーが発生しました')
    technical_details = error_details.get('technical_details', '')
    error_info = ERROR_MESSAGES.get(error_type, ERROR_MESSAGES['unknown_error'])

    escaped_reason = html.escape(reason)
    escaped_technical = html.escape(technical_details)
    escaped_user_message = html.escape(user_message)

    error_content = f"""
<div class="recommendation-result error warning-caution" role="region" aria-label="{error_info['title']}" style="background: #fff3cd; border: 2px solid #ffc107; border-radius: 8px; padding: 20px; margin: 15px 0;">
    <h4 style="color: #856404; margin-top: 0;">{error_info['title']}</h4>
    <p style="color: #856404; font-weight: bold; margin: 10px 0;">{error_info['main_message']}</p>
    <p style="color: #856404; margin: 10px 0;"><strong>エラー理由:</strong> {escaped_reason}</p>

    <h5 style="color: #856404; margin-top: 20px; margin-bottom: 10px;">📋 推奨される対応</h5>
    <ul style="color: #856404; margin: 10px 0; padding-left: 20px;">
"""
    for rec in error_info['recommendations']:
        error_content += f"        <li>{rec}</li>\n"

    error_content += f"""    </ul>

    <h5 style="color: #856404; margin-top: 20px; margin-bottom: 10px;">🏥 医師への相談をお勧めします</h5>
    <p style="color: #856404; margin: 10px 0;">
        以下の場合は、速やかに医療機関（病院・クリニック）を受診してください：
    </p>
    <ul style="color: #856404; margin: 10px 0; padding-left: 20px;">
        <li>症状が1週間以上続いている場合</li>
        <li>症状が悪化している場合</li>
        <li>高熱（38.5度以上）が続く場合</li>
        <li>重症の症状がある場合（激しい痛み、呼吸困難、意識障害など）</li>
        <li>妊娠中・授乳中の場合</li>
        <li>7歳未満のお子様の場合</li>
    </ul>

    <details style="margin-top: 20px; padding: 10px; background: #fff; border-radius: 4px; border: 1px solid #dee2e6;">
        <summary style="color: #856404; cursor: pointer; font-weight: bold;">技術的な詳細（デバッグ用）</summary>
        <pre style="color: #856404; margin: 10px 0; font-size: 0.9em; white-space: pre-wrap; word-wrap: break-word;">{escaped_technical}</pre>
    </details>
</div>"""

    if not include_feedback_buttons:
        return error_content

    error_data = {
        'user_message': escaped_user_message,
        'ai_response': error_content,
        'security_score': None,
        'error_type': error_type
    }
    error_json = html.escape(json.dumps(error_data, ensure_ascii=False))

    return error_content + f"""
    <div class="feedback-buttons" style="margin-top: 20px; padding: 15px; background: #f8f9fa; border-radius: 8px; border: 1px solid #dee2e6;">
        <p style="margin: 0 0 10px 0; font-weight: bold; color: #495057;">このエラーメッセージはいかがでしたか？</p>
        <button class="feedback-btn-positive" onclick="handlePositiveFeedback({error_json})" style="background: #28a745; color: white; border: none; padding: 8px 16px; margin-right: 10px; border-radius: 4px; cursor: pointer; font-size: 14px;">
            適切
        </button>
        <button class="feedback-btn-negative" onclick="handleNegativeFeedback({error_json})" style="background: #dc3545; color: white; border: none; padding: 8px 16px; border-radius: 4px; cursor: pointer; font-size: 14px;">
            不適切
        </button>
    </div>
"""


def format_escalation_display(
    doctor_consultation: str,
    medicine_type: str,
    algorithm: str,
    user_message: str,
    include_feedback_buttons: bool = True
) -> str:
    """
    エスカレーションが必要な場合のHTMLを生成する。

    Args:
        doctor_consultation: 医師への相談メッセージ
        medicine_type: 医薬品の種類
        algorithm: アルゴリズム名
        user_message: ユーザー入力メッセージ
        include_feedback_buttons: フィードバックボタンを含めるか

    Returns:
        HTML文字列
    """
    escaped_user_message = html.escape(user_message)
    escalation_content = f"""
<div class="recommendation-result escalation warning-critical" role="region" aria-label="重要な注意事項">
    <h4>⚠️ 重要な注意事項</h4>
    <p class="escalation-warning"><strong>{doctor_consultation}</strong></p>
    <p><strong>医薬品の種類:</strong> {medicine_type}</p>
    <p><strong>アルゴリズム:</strong> {algorithm}</p>

    <h4>🏥 推奨される対応</h4>
    <ul>
        <li>速やかに医師の診察を受けてください</li>
        <li>市販薬での自己治療は推奨されません</li>
        <li>症状が悪化する場合は救急医療機関へ</li>
    </ul>
</div>"""

    if not include_feedback_buttons:
        return escalation_content

    escalation_data = {
        'user_message': escaped_user_message,
        'ai_response': escalation_content,
        'security_score': None
    }
    escalation_json = html.escape(json.dumps(escalation_data, ensure_ascii=False))

    return escalation_content + f"""
    <div class="feedback-buttons" style="margin-top: 20px; padding: 15px; background: #f8f9fa; border-radius: 8px; border: 1px solid #dee2e6;">
        <p style="margin: 0 0 10px 0; font-weight: bold; color: #495057;">この重要な注意事項はいかがでしたか？</p>
        <button class="feedback-btn-positive" onclick="handlePositiveFeedback({escalation_json})" style="background: #28a745; color: white; border: none; padding: 8px 16px; margin-right: 10px; border-radius: 4px; cursor: pointer; font-size: 14px;">
            適切
        </button>
        <button class="feedback-btn-negative" onclick="handleNegativeFeedback({escalation_json})" style="background: #dc3545; color: white; border: none; padding: 8px 16px; border-radius: 4px; cursor: pointer; font-size: 14px;">
            不適切
        </button>
    </div>
"""
