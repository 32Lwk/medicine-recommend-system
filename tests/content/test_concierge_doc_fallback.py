"""concierge_doc_fallback.py"""
from src.content.concierge_doc_fallback import (
    build_doc_excerpt_answer,
    extract_doc_bullet_excerpt,
)


def test_extract_doc_bullet_excerpt():
    body = """# 概要
- セルフメディケーションを支援
- β版（試験運用）

## 背景
1. ドラッグストア現場の課題
"""
    items = extract_doc_bullet_excerpt(body)
    assert "セルフメディケーション" in " ".join(items)
    assert len(items) >= 2


def test_build_doc_excerpt_answer_min_length():
    body = "- セルフメディケーションを支援する β 版ツール\n- 診断・処方は行わない"
    out = build_doc_excerpt_answer("アプリ概要", body, user_text="背景は？")
    assert "セルフメディケーション" in out
    assert "ℹ️" in out
