#!/usr/bin/env python3
"""一括 OTC 画像同期（bulk_plan / batch JSON → 審査 → R2）。"""
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None  # type: ignore

from scripts.sync_otc_images_from_matsukiyo import MatsukiyoClient
from scripts.sync_top50_otc_images import (
    DEFAULT_LOCAL,
    _load_env,
    process_item,
    r2_exists,
)

DEFAULT_OUT = ROOT / "log" / "analysis" / "otc_image_sync_bulk"
DEFAULT_PLAN = DEFAULT_OUT / "bulk_plan.json"


def load_items(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, list):
        return data
    return list(data.get("items", []))


def write_results(out_dir: Path, results: list[dict[str, Any]], *, label: str) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"results_{label}.json"
    path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def summarize(results: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total": len(results),
        "uploaded": sum(1 for r in results if r.get("status") == "uploaded"),
        "skipped_exists": sum(1 for r in results if r.get("status") == "skipped_exists"),
        "not_found": sum(1 for r in results if r.get("status") == "not_found"),
        "review_rejected": sum(1 for r in results if r.get("status") == "review_rejected"),
        "download_error": sum(1 for r in results if r.get("status") == "download_error"),
        "upload_error": sum(1 for r in results if r.get("status") == "upload_error"),
        "errors": sum(
            1 for r in results if str(r.get("status", "")).endswith("error")
        ),
    }


def merge_results(out_dir: Path) -> dict[str, Any]:
    merged: list[dict[str, Any]] = []
    for p in sorted(out_dir.glob("results_batch_*.json")):
        merged.extend(json.loads(p.read_text(encoding="utf-8")))
    summary = {**summarize(merged), "items": merged}
    (out_dir / "results_all.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Bulk sync OTC images to R2")
    parser.add_argument("--plan", type=Path, default=DEFAULT_PLAN)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--local-dir", type=Path, default=DEFAULT_LOCAL)
    parser.add_argument("--batch", type=int, default=0, help="1-4 batch index")
    parser.add_argument("--upload", action="store_true", default=True)
    parser.add_argument("--no-upload", action="store_true")
    parser.add_argument("--merge-only", action="store_true")
    parser.add_argument("--delay", type=float, default=0.8)
    args = parser.parse_args()
    _load_env()

    if args.merge_only:
        s = merge_results(args.out_dir)
        print(json.dumps({k: s[k] for k in s if k != "items"}, ensure_ascii=False, indent=2))
        return 0

    if args.batch:
        plan_path = args.out_dir / f"batch_{args.batch}.json"
    else:
        plan_path = args.plan
    items = load_items(plan_path)
    upload = args.upload and not args.no_upload
    client = MatsukiyoClient(delay_sec=args.delay)
    results: list[dict[str, Any]] = []

    for i, item in enumerate(items, 1):
        slug = item.get("slug", "")
        if slug and r2_exists(slug):
            item = dict(item)
            item["status"] = "skipped_exists"
            item["r2_url"] = f"https://images.yutok.dev/otc/{slug}.webp"
            results.append(item)
            print(f"[{i}/{len(items)}] skip exists {item.get('product_name')}")
            continue
        print(f"[{i}/{len(items)}] {item.get('product_name')} ({item.get('source')})")
        results.append(process_item(item, client, upload=upload, local_dir=args.local_dir))
        time.sleep(args.delay)

    label = f"batch_{args.batch}" if args.batch else "all"
    write_results(args.out_dir, results, label=label)
    print(json.dumps(summarize(results), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
