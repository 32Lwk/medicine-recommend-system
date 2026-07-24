"""Ask 回答サニタイズのテスト。"""
from __future__ import annotations

from src.services.concierge_output_sanitize import sanitize_medicine_ask_output


def test_sanitize_medicine_ask_strips_env_names():
    raw = "BEDROCK_MEDICINE_KB_ID=30BCEJCJHA の KB を参照しました。"
    out = sanitize_medicine_ask_output(raw)
    assert "BEDROCK_MEDICINE_KB_ID" not in out
    assert "30BCEJCJHA" not in out or "KB" not in out


def test_sanitize_medicine_ask_strips_internal_paths():
    raw = "詳細は src/services/bedrock_kb_retrieve.py に記載があります。"
    out = sanitize_medicine_ask_output(raw)
    assert "src/services" not in out
    assert "公開ドキュメント" in out


def test_sanitize_medicine_ask_preserves_medical_content():
    raw = "イブプロフェンは胃腸障害に注意し、用法用量を守ってください。"
    out = sanitize_medicine_ask_output(raw)
    assert "イブプロフェン" in out
    assert "胃腸障害" in out
