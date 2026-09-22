"""R7-G: evaluator — vacuous adversarial assert scan must be 0."""
from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
ADVERSARIAL_FILES = [
    ROOT / "tests/dialogue/routing/test_r7_pure_session_ops_adversarial.py",
    ROOT / "tests/dialogue/routing/test_policy_d2_adversarial_gates.py",
]


def _is_vacuous_if_detected(node: ast.If) -> bool:
    """Detect patterns like: if detected: assert not pure"""
    test = node.test
    # if x: or if snap.signals.crisis_detected:
    name = None
    if isinstance(test, ast.Name):
        name = test.id
    elif isinstance(test, ast.Attribute):
        name = test.attr
    if name is None:
        return False
    if name not in {
        "detected",
        "crisis_detected",
        "medical_examination",
        "security_blocked",
        "policy_block",
        "hit",
    }:
        return False
    # body only contains asserts that depend on the flag — vacuous if test can be False
    return any(isinstance(s, ast.Assert) for s in node.body)


def test_no_vacuous_conditional_asserts_in_adversarial_files():
    vacuous = []
    for path in ADVERSARIAL_FILES:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.If) and _is_vacuous_if_detected(node):
                vacuous.append(f"{path.name}:{node.lineno}")
    assert vacuous == [], f"vacuous adversarial asserts: {vacuous}"


def test_adversarial_files_contain_direct_true_asserts():
    """Hard requirement: assert detected is True appears (or crisis_detected is True)."""
    text = (ROOT / "tests/dialogue/routing/test_r7_pure_session_ops_adversarial.py").read_text(
        encoding="utf-8"
    )
    assert "assert snap.signals.crisis_detected is True" in text
    assert "assert is_pure_session_ops(snap) is False" in text
    assert "assert snap.signals.medical_examination is True" in text
