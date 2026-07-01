"""w1a scope creep CI テスト。"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def test_w1a_scope_check_script_passes():
    root = Path(__file__).resolve().parents[2]
    script = root / "scripts" / "check_w1a_scope.py"
    result = subprocess.run(
        [sys.executable, str(script)],
        cwd=str(root),
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
