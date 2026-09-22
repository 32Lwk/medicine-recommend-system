"""危機キーワード検出の単体テスト"""
from src.core.crisis_detection import detect_crisis_keywords


def test_nodo_throat_symptoms_not_crisis():
    has, keywords = detect_crisis_keywords("nodoが痛く熱があります")
    assert not has
    assert keywords == []


def test_od_overdose_still_detected():
    has, keywords = detect_crisis_keywords("薬をODしたい")
    assert has
    assert "OD" in keywords


def test_standalone_od_detected():
    has, keywords = detect_crisis_keywords("OD してしまった")
    assert has
    assert "OD" in keywords


def test_physical_limit_not_crisis():
    has, keywords = detect_crisis_keywords("在宅ワークで肩こりが限界")
    assert not has
    assert keywords == []


def test_emotional_limit_still_crisis():
    has, keywords = detect_crisis_keywords("もう限界、消えたい")
    assert has
    assert "限界" in keywords


def test_colloquial_help_headache_not_crisis():
    has, keywords = detect_crisis_keywords("助けて…頭痛すぎて仕事にならない")
    assert not has
    assert keywords == []


def test_explicit_crisis_negation_still_detected_fail_safe():
    """Option A: crisis negation softening removed from Jev boundary repair.

    Phrases that still contain crisis tokens (e.g. 死にたい気持ちはない) remain
    positive. 「死にたくない」 alone has no crisis token substring and stays
    negative under traditional keyword matching.
    """
    has, keywords = detect_crisis_keywords("死にたい気持ちはない")
    assert has
    assert "死にたい" in keywords or "死にたい気持ち" in keywords
    has2, _ = detect_crisis_keywords("今は死にたくない")
    assert not has2


def test_affirmative_crisis_still_detected():
    has, keywords = detect_crisis_keywords("死にたい")
    assert has
    assert "死にたい" in keywords
