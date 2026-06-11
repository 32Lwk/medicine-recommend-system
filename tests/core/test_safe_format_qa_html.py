"""医薬品Q&A HTML整形・医薬品名検出のテスト"""
import pandas as pd

from src.core.medicine.medicine_response_builder import detect_medicine_name_in_query
from src.services.text_formatter import safe_format_qa_html


def test_safe_format_qa_html_converts_markdown_bold():
    raw = "🔍 **医薬品検索結果**\n\n💊 **1つ目: テスト薬**"
    html = safe_format_qa_html(raw)
    assert "<strong>医薬品検索結果</strong>" in html
    assert "<strong>1つ目: テスト薬</strong>" in html
    assert "**" not in html


def test_detect_medicine_name_skips_efficacy_keyword_only():
    df = pd.DataFrame(
        [
            {
                "製品名": "小柴胡湯",
                "メーカー名": "テスト製薬",
                "効能効果": "風邪の後期の症状",
                "用法用量": "1日3回",
                "年齢制限": "",
                "成分": "サイコ",
                "禁止物質あり": "",
                "医薬品の種類": "漢方",
            }
        ]
    )
    detected = detect_medicine_name_in_query("陸上競技でも使える風邪薬を教えてください。", df)
    assert detected == []
