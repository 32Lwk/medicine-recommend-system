"""rule_based_medicine_recommendation のインポート・引数互換"""
import inspect

from src.core.medicine_logic import rule_based_medicine_recommendation as from_logic
from src.core.rule_based_recommendation import (
    rule_based_medicine_recommendation as from_rbr,
)


def test_both_entrypoints_accept_precomputed_nlu():
    for fn in (from_logic, from_rbr):
        sig = inspect.signature(fn)
        assert "precomputed_nlu" in sig.parameters
