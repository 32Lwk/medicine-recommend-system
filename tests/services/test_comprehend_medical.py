"""comprehend_medical.py"""
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture(autouse=True)
def _clear_env(monkeypatch):
    monkeypatch.delenv("COMPREHEND_MEDICAL_ENABLED", raising=False)


def test_merge_skips_line_session(monkeypatch):
    monkeypatch.setenv("COMPREHEND_MEDICAL_ENABLED", "true")
    from src.services.comprehend_medical import merge_comprehend_into_nlu

    nlu = {"symptoms": [], "confidence_score": 0.1}
    out = merge_comprehend_into_nlu(nlu, "頭が痛い", session_id="line:Uabc")
    assert "comprehend_medical" not in out


def test_merge_adds_symptoms_when_low_confidence(monkeypatch):
    monkeypatch.setenv("COMPREHEND_MEDICAL_ENABLED", "true")
    mock_client = MagicMock()
    mock_client.detect_entities_v2.return_value = {
        "Entities": [
            {
                "Text": "頭痛",
                "Category": "MEDICAL_CONDITION",
                "Type": "DX_NAME",
                "Score": 0.91,
            }
        ]
    }
    with patch("boto3.client", return_value=mock_client):
        from src.services.comprehend_medical import merge_comprehend_into_nlu

        nlu = {"symptoms": [], "confidence_score": 0.2}
        out = merge_comprehend_into_nlu(nlu, "頭が痛い", session_id="web-session")
    assert out["symptoms"]
    assert out["symptoms"][0]["name"] == "頭痛"
