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
