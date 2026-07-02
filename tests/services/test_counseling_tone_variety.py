"""Phase 2 (p2-counseling, Subtask B): counseling トーン多様化。

「応援しています」等の定型句反復を抑制するプロンプト抽象化・直近使用検出・
エラーフォールバックのローテーションを検証する。
"""
from __future__ import annotations

import sys

from tests._paths import PROJECT_ROOT

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.services.counseling.counseling_prompts import get_counseling_prompt_template
from src.services.counseling.counseling_generator import (
    _build_avoid_phrases_hint,
    _pick_supportive_closing_phrase,
)
from src.services.counseling.counseling_processor import _pick_session_closing_phrase


# ---------------------------------------------------------------------------
# get_counseling_prompt_template: tone_variety 分岐
# ---------------------------------------------------------------------------

def test_tone_variety_off_keeps_literal_examples():
    """既定 False: 従来のリテラル例文（「応援しています」等）を含む現状維持テンプレ。"""
    template = get_counseling_prompt_template("general_emotional", tone_variety=False)
    assert "応援しています" in template["user_prompt_template"]


def test_tone_variety_on_removes_literal_repeatable_examples():
    """True: リテラル定型句例示を含まない抽象化テンプレ + avoid_phrases_hint プレースホルダ。"""
    template = get_counseling_prompt_template("general_emotional", tone_variety=True)
    assert "応援しています" not in template["user_prompt_template"]
    assert "大丈夫ですよ" not in template["user_prompt_template"]
    assert "{avoid_phrases_hint}" in template["user_prompt_template"]


def test_tone_variety_does_not_affect_medical_templates():
    """医療系（anxiety 等）テンプレートは tone_variety の影響を受けない。"""
    off = get_counseling_prompt_template("anxiety", tone_variety=False)
    on = get_counseling_prompt_template("anxiety", tone_variety=True)
    assert off == on


def test_template_format_with_avoid_phrases_hint_placeholder():
    """avoid_phrases_hint を渡した format() がエラーなく完了すること。"""
    template = get_counseling_prompt_template("general_emotional", tone_variety=True)
    formatted = template["user_prompt_template"].format(
        history_context="",
        user_text="つらいです",
        symptom_type="general_emotional",
        avoid_phrases_hint="",
    )
    assert "つらいです" in formatted


# ---------------------------------------------------------------------------
# _build_avoid_phrases_hint
# ---------------------------------------------------------------------------

def test_avoid_phrases_hint_empty_when_disabled():
    history = [{"type": "bot", "content": "応援しています。"}]
    assert _build_avoid_phrases_hint(history, enabled=False) == ""


def test_avoid_phrases_hint_empty_when_no_recent_usage():
    history = [{"type": "bot", "content": "つらいですね、無理しないでください。"}]
    assert _build_avoid_phrases_hint(history, enabled=True) == ""


def test_avoid_phrases_hint_detects_recent_stock_phrase():
    history = [
        {"type": "user", "content": "疲れました"},
        {"type": "bot", "content": "応援しています。少しずつでいいですよ。"},
    ]
    hint = _build_avoid_phrases_hint(history, enabled=True)
    assert "応援しています" in hint
    assert "別の言い回し" in hint


def test_avoid_phrases_hint_only_scans_recent_window():
    """直近6件より前の使用は検出対象外（ウィンドウ制限）。"""
    old = [{"type": "bot", "content": "応援しています。"}]
    filler = [{"type": "user", "content": f"入力{i}"} for i in range(10)]
    history = old + filler
    assert _build_avoid_phrases_hint(history, enabled=True) == ""


# ---------------------------------------------------------------------------
# エラーフォールバックの定型句ローテーション
# ---------------------------------------------------------------------------

def test_stateless_closing_phrase_flag_off_is_fixed(monkeypatch):
    monkeypatch.delenv("UX_COUNSELING_TONE_VARIETY", raising=False)
    assert _pick_supportive_closing_phrase() == "応援しています。"


def test_stateless_closing_phrase_flag_on_varies(monkeypatch):
    monkeypatch.setenv("UX_COUNSELING_TONE_VARIETY", "true")
    phrases = {_pick_supportive_closing_phrase() for _ in range(30)}
    # ランダム選択のため、30回試行すれば複数バリエーションが出現するはず
    assert len(phrases) > 1


def test_session_closing_phrase_flag_off_is_fixed(monkeypatch):
    monkeypatch.delenv("UX_COUNSELING_TONE_VARIETY", raising=False)
    session = {"counseling_mode": {}}
    assert _pick_session_closing_phrase(session) == "応援しています。"


def test_session_closing_phrase_flag_on_avoids_recent(monkeypatch):
    monkeypatch.setenv("UX_COUNSELING_TONE_VARIETY", "true")
    session = {"counseling_mode": {"recent_tone_phrases": ["応援しています。"]}}
    chosen = _pick_session_closing_phrase(session)
    assert chosen != "応援しています。"
    # ローテーション履歴が更新される
    assert session["counseling_mode"]["recent_tone_phrases"][-1] == chosen


def test_session_closing_phrase_tracks_history_across_calls(monkeypatch):
    monkeypatch.setenv("UX_COUNSELING_TONE_VARIETY", "true")
    session = {"counseling_mode": {}}
    first = _pick_session_closing_phrase(session)
    second = _pick_session_closing_phrase(session)
    # 直近2件は互いに重複しない（候補が尽きない限り）
    assert first != second
