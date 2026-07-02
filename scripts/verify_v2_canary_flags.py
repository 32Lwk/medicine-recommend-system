#!/usr/bin/env python3
"""Phase 4b-5b — v2 / PRIMARY / TRIM フラグ検証（FLAGS_OK 相当）。

Usage (PowerShell パターン A — 本番カナリア):
  $env:APP_ENV="production"
  $env:CHAT_PIPELINE_V2="true"
  $env:CHAT_PIPELINE_V2_ALLOWLIST="line:canary-test-01"
  $env:CHAT_PIPELINE_V2_INTENT_ROUTER_PRIMARY="true"
  $env:CHAT_PIPELINE_V2_INTENT_ROUTER_PRIMARY_ALLOWLIST="line:canary-test-01"
  $env:CHAT_PIPELINE_V2_LEGACY_FALLBACK_TRIM="true"
  python scripts/verify_v2_canary_flags.py

Usage (PowerShell パターン B — dev 一括、env 最小):
  $env:APP_ENV="development"
  python scripts/verify_v2_canary_flags.py

Exit 0 = すべて期待どおり。1 = 不一致あり。
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config.app_config import is_development_runtime
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


def _verify_dev_auto_on(canary: dict[str, bool], other: dict[str, bool]) -> list[str]:
    errors: list[str] = []
    for sid, row in ((CANARY_SID, canary), (NON_CANARY_SID, other)):
        if not row["v2"]:
            errors.append(f"{sid}: v2 expected True (dev auto-on)")
        if not row["dispatch"]:
            errors.append(f"{sid}: dispatch expected True (dev auto-on)")
        if not row["primary"]:
            errors.append(f"{sid}: primary expected True (dev auto-on)")
        if not row["trim"]:
            errors.append(f"{sid}: trim expected True (dev auto-on)")
    return errors


def main() -> int:
    app_env = os.getenv("APP_ENV", "")
    allow_v2 = os.getenv("CHAT_PIPELINE_V2_ALLOWLIST", "")
    allow_primary = os.getenv("CHAT_PIPELINE_V2_INTENT_ROUTER_PRIMARY_ALLOWLIST", "")
    trim_global = os.getenv("CHAT_PIPELINE_V2_LEGACY_FALLBACK_TRIM", "")

    print(f"APP_ENV={app_env}")
    print(f"CHAT_PIPELINE_V2_ALLOWLIST={allow_v2!r}")
    print(f"CHAT_PIPELINE_V2_INTENT_ROUTER_PRIMARY_ALLOWLIST={allow_primary!r}")
    print(f"CHAT_PIPELINE_V2_LEGACY_FALLBACK_TRIM={trim_global!r}")
    print()

    canary = _row(CANARY_SID)
    other = _row(NON_CANARY_SID)

    print(f"{'sid':<30} {'v2':>5} {'dispatch':>8} {'primary':>7} {'trim':>5}")
    print(f"{CANARY_SID:<30} {canary['v2']!s:>5} {canary['dispatch']!s:>8} {canary['primary']!s:>7} {canary['trim']!s:>5}")
    print(f"{NON_CANARY_SID:<30} {other['v2']!s:>5} {other['dispatch']!s:>8} {other['primary']!s:>7} {other['trim']!s:>5}")
    print()

    errors: list[str] = []

    if is_development_runtime() and not allow_primary and not allow_v2:
        errors.extend(_verify_dev_auto_on(canary, other))
        if errors:
            print("FLAGS_NG (dev auto-on):")
            for e in errors:
                print(f"  - {e}")
            return 1
        print("FLAGS_OK (dev auto-on)")
        return 0

    # カナリア sid が allowlist に含まれる構成なら primary+trim 期待
    if allow_primary and CANARY_SID in {s.strip() for s in allow_primary.split(",") if s.strip()}:
        if not canary["primary"]:
            errors.append(f"{CANARY_SID}: primary expected True")
        if trim_global.lower() in ("1", "true", "yes", "on") and not canary["trim"]:
            errors.append(f"{CANARY_SID}: trim expected True")
    elif allow_primary:
        if canary["primary"]:
            errors.append(f"{CANARY_SID}: primary expected False (not in PRIMARY_ALLOWLIST)")

    # 非カナリアは primary/trim OFF（production + PRIMARY_ALLOWLIST 非空時）
    if allow_primary and NON_CANARY_SID not in {s.strip() for s in allow_primary.split(",") if s.strip()}:
        if other["primary"]:
            errors.append(f"{NON_CANARY_SID}: primary expected False")
        if other["trim"]:
            errors.append(f"{NON_CANARY_SID}: trim expected False")

    # v2 ALLOWLIST 整合
    if allow_v2:
        allow_set = {s.strip() for s in allow_v2.split(",") if s.strip()}
        if CANARY_SID in allow_set and not canary["v2"]:
            errors.append(f"{CANARY_SID}: v2 expected True")
        if NON_CANARY_SID not in allow_set and other["v2"]:
            errors.append(f"{NON_CANARY_SID}: v2 expected False")

    if errors:
        print("FLAGS_NG:")
        for e in errors:
            print(f"  - {e}")
        return 1

    print("FLAGS_OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
