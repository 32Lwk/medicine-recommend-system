"""validate_turn_expects ユニットテスト。"""
from __future__ import annotations

from scripts.validate_turn_expects import validate_turn_expects_file
from tests._paths import PROJECT_ROOT


def test_golden_pr_fixture_validates():
    path = PROJECT_ROOT / "tests" / "fixtures" / "v2_e2e_golden_pr.yaml"
    result = validate_turn_expects_file(path)
    assert result["ok"], result["errors"]
