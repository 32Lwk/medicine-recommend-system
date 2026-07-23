#!/usr/bin/env python3
"""manifest.json の uploaded 画像を CDN からローカル static/otc/ に同期する。"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "log" / "analysis" / "otc_image_sync" / "manifest.json"
DEFAULT_LOCAL_DIR = ROOT / "static" / "otc"


def export_local(
    manifest_path: Path,
    local_dir: Path,
    *,
    overwrite: bool = False,
) -> tuple[int, int]:
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    local_dir.mkdir(parents=True, exist_ok=True)
    ok = skip = 0
    session = requests.Session()
    session.headers["User-Agent"] = "medicine-recommend/1.0"

    for row in data.get("items", []):
        if row.get("status") != "uploaded":
            continue
        slug = str(row.get("slug") or "").strip()
        url = str(row.get("r2_url") or "").strip()
        if not slug or not url:
            continue
        dest = local_dir / f"{slug}.webp"
        if dest.is_file() and not overwrite:
            skip += 1
            continue
        r = session.get(url, timeout=60)
        r.raise_for_status()
        dest.write_bytes(r.content)
        ok += 1
        print(f"saved {dest.relative_to(ROOT)}", flush=True)

    index = {
        "source_manifest": str(manifest_path.relative_to(ROOT)),
        "local_dir": str(local_dir.relative_to(ROOT)),
        "files": sorted(p.name for p in local_dir.glob("*.webp")),
    }
    (local_dir / "index.json").write_text(
        json.dumps(index, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return ok, skip


def main() -> int:
    parser = argparse.ArgumentParser(description="Export uploaded OTC images to static/otc/")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--local-dir", type=Path, default=DEFAULT_LOCAL_DIR)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    if not args.manifest.is_file():
        print(f"manifest not found: {args.manifest}", file=sys.stderr)
        return 1
    ok, skip = export_local(args.manifest, args.local_dir, overwrite=args.overwrite)
    print(f"Done. saved={ok} skipped={skip} dir={args.local_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
