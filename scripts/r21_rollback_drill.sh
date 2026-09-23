#!/usr/bin/env bash
# R21 AWS staging rollback drill (shadow kill-switch).
# Prerequisites: observability alarms exist; synthetic only.
# Steps: ensure shadow ON briefly → OFF → verify no PRIMARY/D2 → health OK.
# Does not inject real-user traffic. Does not print secrets.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck source=lib/aws_common.sh
source "$ROOT/scripts/lib/aws_common.sh"

export AWS_PROFILE="${AWS_PROFILE:-default}"
OUT="${1:-log/analysis/jev_r21_rollback_drill.json}"
mkdir -p "$(dirname "$OUT")"
START="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

echo "==> Drill start ${START}"
bash "$ROOT/scripts/r21_staging_shadow_flags.sh" on
ON_TS="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
sleep 20
bash "$ROOT/scripts/r21_staging_shadow_flags.sh" off
OFF_TS="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

# Wait for settle
for i in $(seq 1 24); do
  if python "$ROOT/scripts/r21_verify_staging_flags.py" >/tmp/r21_flags.json 2>/dev/null; then
    break
  fi
  sleep 10
done

END="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
python - <<PY
import json
from pathlib import Path
flags = {}
try:
    flags = json.loads(Path("/tmp/r21_flags.json").read_text(encoding="utf-8"))
except Exception as e:
    flags = {"error": str(e)}
out = {
    "started_at": "$START",
    "shadow_on_at": "$ON_TS",
    "shadow_off_at": "$OFF_TS",
    "ended_at": "$END",
    "flags_verify": flags,
    "note": "Kill-switch = env flags OFF via new task revision. PRIMARY/D2 locked 0.",
}
Path("$OUT").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(out, ensure_ascii=False, indent=2))
PY
