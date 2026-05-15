"""html_formatter 統一UIコンポーネントのテスト"""

from src.services.html_formatter import (
    format_diagnosis_notification,
    format_error_display,
    format_escalation_display,
    format_medicine_type_notice,
    format_status_card,
    format_system_error,
)


def test_format_status_card_variants():
    html = format_status_card(
        variant='error',
        title='テストエラー',
        subtitle='サブタイトル',
        hints=['ヒント1'],
    )
    assert 'chat-status-card--error' in html
    assert 'chat-status-card__title' in html
    assert 'テストエラー' in html
    assert 'ヒント1' in html


def test_format_error_display_includes_feedback():
    html = format_error_display(
        error_type='no_candidates',
        error_details={'reason': '候補なし', 'technical_details': 'debug'},
        user_message='頭痛',
    )
    assert 'chat-status-card--caution' in html
    assert 'feedback-buttons' in html
    assert '候補なし' in html


def test_format_system_error_no_technical_jargon():
    html = format_system_error()
    assert 'chat-status-card--error' in html
    assert '一時的なエラー' in html


def test_format_diagnosis_notification():
    html = format_diagnosis_notification(
        '診断メッセージ',
        {'user_message': 'u', 'ai_response': 'a'},
        bug_report_attrs='data-user-message="u"',
    )
    assert 'chat-status-card--notice' in html
    assert '診断名が含まれています' in html
    assert 'chat-status-card__footer' in html
    assert 'bug-report-btn' in html
    assert html.count('chat-status-card chat-status-card--notice') == 1
    assert 'chat-status-card--notice chat-response' not in html
    assert html.index('chat-status-card__footer') > html.index('chat-status-card__body')


def test_format_medicine_type_notice():
    html = format_medicine_type_notice(
        '相談メッセージ',
        {'user_message': 'u', 'ai_response': 'a'},
    )
    assert 'chat-status-card--caution' in html
    assert '症状から医薬品を選べませんでした' in html
    assert 'chat-status-card__footer' in html


def test_format_escalation_display():
    html = format_escalation_display(
        doctor_consultation='医師に相談',
        medicine_type='解熱',
        algorithm='rule_based',
        user_message='熱',
    )
    assert 'chat-status-card--critical' in html
    assert '重要な注意事項' in html
