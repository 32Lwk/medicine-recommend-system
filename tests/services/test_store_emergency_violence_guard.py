"""Phase 2 (p2-violence-guard): store_emergency_handler の violence 曖昧語 文脈ガード。

「友人と喧嘩しました」等の心理相談文脈が、violence の曖昧語（「喧嘩」等）単体で
緊急誤検知される問題への回帰テスト。フラグ SAFETY_VIOLENCE_CONTEXT_GUARD で制御。
"""
from __future__ import annotations

import sys

from tests._paths import PROJECT_ROOT

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.services.store_emergency_handler import detect_store_emergency


# ---------------------------------------------------------------------------
# フラグ OFF（既定）: 現状維持（曖昧語のみでも従来どおり検出）
# ---------------------------------------------------------------------------

def test_flag_off_ambiguous_kenka_still_detected_as_before(monkeypatch):
    monkeypatch.delenv("SAFETY_VIOLENCE_CONTEXT_GUARD", raising=False)
    result = detect_store_emergency("友人と喧嘩しました")
    assert result is not None
    assert result["primary_type"] == "violence"


# ---------------------------------------------------------------------------
# フラグ ON: 心理相談文脈の誤検知を除外
# ---------------------------------------------------------------------------

def test_flag_on_counseling_context_not_detected(monkeypatch):
    monkeypatch.setenv("SAFETY_VIOLENCE_CONTEXT_GUARD", "true")
    assert detect_store_emergency("友人と喧嘩しました") is None
    assert detect_store_emergency("友達とけんかした") is None
    assert detect_store_emergency("彼氏とケンカしてしまいました") is None


def test_flag_on_counseling_wording_without_strong_signal_not_detected(monkeypatch):
    monkeypatch.setenv("SAFETY_VIOLENCE_CONTEXT_GUARD", "true")
    # 人間関係の悩み相談文脈（strong signal なし）は「相談」等の語の有無に関わらず除外
    assert detect_store_emergency("人間関係で悩んでいて、友人と喧嘩しました") is None
    assert detect_store_emergency("相談です。友人と喧嘩してモヤモヤしています") is None


def test_flag_on_strong_signal_takes_precedence_over_consultation_wording(monkeypatch):
    """強シグナル（実害を示す語）が含まれる場合は、相談口調でも安全側に倒して検知を維持する。"""
    monkeypatch.setenv("SAFETY_VIOLENCE_CONTEXT_GUARD", "true")
    result = detect_store_emergency("相談です。喧嘩して殴られたのですが大丈夫でしょうか")
    assert result is not None


# ---------------------------------------------------------------------------
# フラグ ON でも真の緊急（強シグナル共起）は維持
# ---------------------------------------------------------------------------

def test_flag_on_true_violence_with_strong_signal_still_detected(monkeypatch):
    monkeypatch.setenv("SAFETY_VIOLENCE_CONTEXT_GUARD", "true")
    result = detect_store_emergency("喧嘩していて殴られました")
    assert result is not None
    assert result["primary_type"] == "violence"


def test_flag_on_witness_report_with_help_request_still_detected(monkeypatch):
    """「助けて」は強シグナルのため violence 曖昧語の除外は解除される。

    ただし「助けて」は medical_emergency キーワードでもあるため、
    primary_type は優先度表（medical_emergency > violence）に従い得る。
    ここでは「緊急として検知される（None にならない）」ことのみを検証する。
    """
    monkeypatch.setenv("SAFETY_VIOLENCE_CONTEXT_GUARD", "true")
    result = detect_store_emergency("目の前で喧嘩していて助けてください")
    assert result is not None
    assert "violence" in result["emergency_types"]


def test_flag_on_weapon_involved_kenka_still_detected(monkeypatch):
    monkeypatch.setenv("SAFETY_VIOLENCE_CONTEXT_GUARD", "true")
    result = detect_store_emergency("喧嘩で刃物を持ち出しています")
    assert result is not None


def test_flag_on_explicit_violence_keywords_unaffected(monkeypatch):
    """曖昧語リスト外の明確な暴力キーワードはガードの影響を受けない。"""
    monkeypatch.setenv("SAFETY_VIOLENCE_CONTEXT_GUARD", "true")
    assert detect_store_emergency("殴られています") is not None
    assert detect_store_emergency("暴力を振るわれている") is not None


# ---------------------------------------------------------------------------
# 既存カテゴリの回帰なし（violence 以外は無関係）
# ---------------------------------------------------------------------------

def test_flag_on_other_emergency_types_unaffected(monkeypatch):
    monkeypatch.setenv("SAFETY_VIOLENCE_CONTEXT_GUARD", "true")
    assert detect_store_emergency("大量出血しています") is not None
    assert detect_store_emergency("倒れている人がいます") is not None
    assert detect_store_emergency("ナイフを持っている人がいます") is not None
