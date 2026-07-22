#!/usr/bin/env python3
"""v2 / PRIMARY / TRIM フラグ検証（FLAGS_OK 相当）。

Usage (production — 未設定で v2 + PRIMARY + TRIM すべて ON):
  APP_ENV=production python scripts/verify_v2_canary_flags.py

Usage (dev):
  APP_ENV=development python scripts/verify_v2_canary_flags.py

Exit 0 = すべて期待どおり。1 = 不一致あり。
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config.llm_flags import (
    is_chat_pipeline_v2_for_session,
    is_intent_router_dispatch_enabled,
    is_intent_router_primary_enabled,
    is_legacy_fallback_trim_enabled,
)

CANARY_SID = os.getenv("CANARY_TEST_SID", "line:canary-test-01")
NON_CANARY_SID = os.getenv("NON_CANARY_TEST_SID", "line:non-canary-test-99")


def _row(sid: str) -> dict[str, bool]:
    return {
        "v2": is_chat_pipeline_v2_for_session(sid),
        "dispatch": is_intent_router_dispatch_enabled(sid),
        "primary": is_intent_router_primary_enabled(sid),
        "trim": is_legacy_fallback_trim_enabled(sid),
    }


def main() -> int:
    app_env = os.getenv("APP_ENV", "")
    trim_global = os.getenv("CHAT_PIPELINE_V2_LEGACY_FALLBACK_TRIM", "")
    primary_global = os.getenv("CHAT_PIPELINE_V2_INTENT_ROUTER_PRIMARY", "")
    v2_global = os.getenv("CHAT_PIPELINE_V2", "")

    print(f"APP_ENV={app_env}")
    print(f"CHAT_PIPELINE_V2={v2_global!r}")
    print(f"CHAT_PIPELINE_V2_INTENT_ROUTER_PRIMARY={primary_global!r}")
    print(f"CHAT_PIPELINE_V2_LEGACY_FALLBACK_TRIM={trim_global!r}")
    print()

    canary = _row(CANARY_SID)
    other = _row(NON_CANARY_SID)

    print(f"{'sid':<30} {'v2':>5} {'dispatch':>8} {'primary':>7} {'trim':>5}")
    print(f"{CANARY_SID:<30} {canary['v2']!s:>5} {canary['dispatch']!s:>8} {canary['primary']!s:>7} {canary['trim']!s:>5}")
    print(f"{NON_CANARY_SID:<30} {other['v2']!s:>5} {other['dispatch']!s:>8} {other['primary']!s:>7} {other['trim']!s:>5}")
    print()

    errors: list[str] = []
    for sid, row in ((CANARY_SID, canary), (NON_CANARY_SID, other)):
        if not row["v2"]:
            errors.append(f"{sid}: v2 expected True")
        if not row["dispatch"]:
            errors.append(f"{sid}: dispatch expected True")
        if not row["primary"]:
            errors.append(f"{sid}: primary expected True")
        if not row["trim"]:
            errors.append(f"{sid}: trim expected True")

    if errors:
        print("FLAGS_NG:")
        for e in errors:
            print(f"  - {e}")
        return 1

    print("FLAGS_OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
