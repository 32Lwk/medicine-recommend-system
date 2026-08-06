#!/usr/bin/env bash
# Zip Lambda handler + scripts/lambda/common for deploy.
#
# Usage:
#   bundle_lambda_zip HANDLER_DIR OUTPUT_ZIP
#
bundle_lambda_zip() {
  local handler_dir="$1"
  local zip_file="$2"
  local lib_dir common_dir
  lib_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  common_dir="$(cd "${lib_dir}/../lambda/common" && pwd)"
  local py_handler py_common py_zip
  py_handler="$(to_win_path "$handler_dir")"
  py_common="$(to_win_path "$common_dir")"
  py_zip="$(to_win_path "$zip_file")"
  python3 - "$py_handler" "$py_common" "$py_zip" <<'PY'
import sys, zipfile
from pathlib import Path

handler_dir = Path(sys.argv[1])
common_dir = Path(sys.argv[2])
zip_path = Path(sys.argv[3])

with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
    zf.write(handler_dir / "handler.py", "handler.py")
    for path in sorted(common_dir.rglob("*.py")):
        arc = Path("common") / path.relative_to(common_dir)
        zf.write(path, arc.as_posix())
PY
}
