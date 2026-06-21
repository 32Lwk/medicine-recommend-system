"""triage_agent.keyword_pre_triage の緊急キーワード拡張テスト"""
from src.agents.triage_agent import keyword_pre_triage


def test_heart_pain_keyword():
    result = keyword_pre_triage("心臓が痛い")
    assert result is not None
    assert result["category"] == "Emergency"
    assert result["pre_triage"] is True


def test_sudden_severe_headache():
    result = keyword_pre_triage("突然の激しい頭痛がします")
    assert result is not None
    assert result["category"] == "Emergency"


def test_non_emergency_not_matched():
    assert keyword_pre_triage("頭が少し痛い") is None
