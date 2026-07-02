"""カテゴリ別入力ブロック応答のテスト"""
from src.security.input_block_responses import (
    NOTICE_BY_CATEGORY,
    match_input_block,
    should_bypass_input_block_for_counseling,
)
from src.security.aggressive_input import is_aggressive_expression, is_non_absolute_aggressive_expression


def test_rape_bypasses_block():
    assert should_bypass_input_block_for_counseling("レイプ")
    assert match_input_block("レイプ") is None
    assert not is_aggressive_expression("レイプ")[0]


def test_sexual_assault_keywords_bypass():
    for word in ("性被害", "rape", "痴漢"):
        assert match_input_block(word) is None


def test_sex_returns_sexual_content_notice():
    notice = match_input_block("sex")
    assert notice is not None
    assert notice.category == "sexual_content"
    assert notice.kind == "inappropriate_sexual"
    assert notice.message == NOTICE_BY_CATEGORY["sexual_content"]


def test_numeric_slang_returns_sexual_content():
    notice = match_input_block("69")
    assert notice is not None
    assert notice.category == "sexual_content"


def test_kill_threat_returns_threat_abuse():
    notice = match_input_block("殺すぞ")
    assert notice is not None
    assert notice.category == "threat_abuse"
    assert notice.kind == "aggressive_input"


def test_shine_returns_threat_abuse():
    notice = match_input_block("しね")
    assert notice is not None
    assert notice.category == "threat_abuse"


def test_papakatsu_returns_solicitation():
    notice = match_input_block("パパ活")
    assert notice is not None
    assert notice.category == "solicitation"
    assert notice.kind == "inappropriate_solicitation"


def test_ddos_returns_system_abuse():
    notice = match_input_block("ddos攻撃")
    assert notice is not None
    assert notice.category == "system_abuse"
    assert notice.kind == "system_abuse"


def test_symptom_kill_not_blocked():
    assert match_input_block("頭痛が殺す") is None


def test_non_absolute_excludes_absolute_block():
    assert is_aggressive_expression("しね")[0]
    assert not is_non_absolute_aggressive_expression("しね")[0]
    assert is_non_absolute_aggressive_expression("殺すぞ")[0]
