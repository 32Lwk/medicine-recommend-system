"""analyze_comprehend_logs.py"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from analyze_comprehend_logs import _extract_comprehend  # noqa: E402


def test_extract_from_structured_field():
    payload = {
        "comprehend_medical": {
            "entities": [{"category": "MEDICAL_CONDITION", "type": "DX_NAME", "text": "頭痛"}]
        }
    }
    ents = _extract_comprehend(payload)
    assert len(ents) == 1
    assert ents[0]["text"] == "頭痛"


def test_extract_from_log_message():
    payload = {
        "message": 'comprehend_medical {"entities": [{"text": "咳"}]} extra'
    }
    ents = _extract_comprehend(payload)
    assert len(ents) == 1
    assert ents[0]["text"] == "咳"
