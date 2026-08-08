"""validate_e2e_corpus.py — smoke."""
from __future__ import annotations

from pathlib import Path

from scripts.validate_e2e_corpus import validate_corpus

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CORPUS = PROJECT_ROOT / "tests" / "fixtures" / "v2_e2e_corpus_pr500.yaml"


def test_pr500_corpus_passes_validation():
    result = validate_corpus(CORPUS, expected_total=500)
    assert result["ok"], result["errors"][:5]
