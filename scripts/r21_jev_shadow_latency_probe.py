#!/usr/bin/env python3
"""R21 Jev-only shadow latency probe (local synthetic).

Reuses measure_jev_shadow_latency_breakdown phases; writes R21-dated artifact.
Does not enable Primary / Shadow production flags.

Usage:
  python scripts/r21_jev_shadow_latency_probe.py --repeats 8
"""
from __future__ import annotations

import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = (
    ROOT
    / "log"
    / "analysis"
    / f"jev_r21_latency_breakdown_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.json"
)


def main() -> int:
    script = ROOT / "scripts" / "measure_jev_shadow_latency_breakdown.py"
    repeats = "8"
    for i, a in enumerate(sys.argv[1:], 1):
        if a == "--repeats" and i + 1 < len(sys.argv):
            repeats = sys.argv[i + 1]
    cmd = [
        sys.executable,
        str(script),
        "--repeats",
        repeats,
        "--output-json",
        str(OUT),
    ]
    print("running:", " ".join(cmd), file=sys.stderr)
    return subprocess.call(cmd)


if __name__ == "__main__":
    raise SystemExit(main())
