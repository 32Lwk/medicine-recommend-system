#!/usr/bin/env python3
"""
Wave 1a スコープクリープ検査。

chat_post_pipeline / chat_orchestrator / chat_triage に v2 以外の
category routing 変更が紛れ込んでいないか、禁止パターンを簡易チェックする。
CI: python scripts/check_w1a_scope.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

W1A_GUARDED_FILES = (
    ROOT / "src/handlers/chat/chat_post_pipeline.py",
    ROOT / "src/handlers/chat_orchestrator.py",
    ROOT / "src/handlers/chat/chat_triage.py",
)

# Wave 1b まで chat_post_pipeline に routing 本体 import 禁止（shadow のみ可）
FORBIDDEN_ADDITIONS = (
    re.compile(r"from src\.dialogue\.routing\.(?!shadow)"),
    re.compile(r"IntentRouter"),
    re.compile(r"try_intent_router"),
)

ALLOWED_DIALOGUE_IMPORTS = (
    "src.dialogue.pipeline",
    "src.dialogue.session_ops",
    "src.dialogue.adapters.web_sse",
    "src.dialogue.routing.shadow",
    "src.dialogue.dispatcher",
    "src.dialogue.sync_legacy",
    "src.dialogue.history",
    "config.llm_flags",
)


def check_file(path: Path) -> list[str]:
    errors: list[str] = []
    if not path.is_file():
        return errors
    text = path.read_text(encoding="utf-8")
    for pattern in FORBIDDEN_ADDITIONS:
        if pattern.search(text):
            errors.append(f"{path.relative_to(ROOT)}: forbidden pattern {pattern.pattern}")
    if path.name == "chat_post_pipeline.py":
        for line in text.splitlines():
            if "src.dialogue" in line and "import" in line:
                if not any(a in line for a in ALLOWED_DIALOGUE_IMPORTS):
                    if "dialogue" in line:
                        errors.append(
                            f"{path.relative_to(ROOT)}: unexpected dialogue import: {line.strip()}"
                        )
    return errors


def main() -> int:
    all_errors: list[str] = []
    for path in W1A_GUARDED_FILES:
        all_errors.extend(check_file(path))
    if all_errors:
        print("w1a scope creep detected:")
        for err in all_errors:
            print(f"  - {err}")
        return 1
    print("w1a scope check passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
