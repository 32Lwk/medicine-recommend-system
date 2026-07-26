#!/usr/bin/env python3
"""missing104 / not_found 再試行 — マルチソース解決 + R2 アップロード。"""
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

from scripts.otc_image_multi_source import resolve_multi_source
from scripts.sync_otc_images_from_matsukiyo import MatsukiyoClient, save_local_webp, upload_to_r2
from scripts.sync_top50_otc_images import DEFAULT_LOCAL, _load_env, download_as_webp_from_url, r2_exists

DEFAULT_IN = ROOT / "log" / "analysis" / "otc_image_sync_bulk" / "missing104_retry.json"
DEFAULT_OUT = ROOT / "log" / "analysis" / "otc_image_sync_bulk"


def load_items(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return data if isinstance(data, list) else data.get("items", [])


def process_retry_item(
    item: dict[str, Any],
    client: MatsukiyoClient,
    *,
    upload: bool,
    local_dir: Path,
) -> dict[str, Any]:
    name = str(item["product_name"])
    mfr = str(item.get("manufacturer", ""))
    slug = str(item.get("slug", ""))
    result = dict(item)
    result["processed_at"] = datetime.now(timezone.utc).isoformat()

    if slug and r2_exists(slug):
        result["status"] = "skipped_exists"
        result["r2_url"] = f"https://images.yutok.dev/otc/{slug}.webp"
        return result

    official = str(item.get("official_url") or item.get("source_image_url") or "")
    extra = [u for u in item.get("candidate_urls") or [] if u]

    best = resolve_multi_source(
        name,
        mfr,
        client=client,
        official_url=official,
        extra_urls=extra,
    )
    if not best or not best.image_url:
        result["status"] = "not_found"
        result["note"] = "multi_source: no candidates"
        return result

    result["source"] = best.source
    result["source_image_url"] = best.image_url
    result["source_label"] = best.source_label
    result["review_score"] = best.review_score
    result["review_reasons"] = best.review_reasons
    result["match_score"] = best.score

    if not best.approved:
        result["status"] = "review_rejected"
        result["note"] = "; ".join(best.review_reasons) or "score_below_threshold"
        review_dir = local_dir.parent / "review_rejected"
        review_dir.mkdir(parents=True, exist_ok=True)
        try:
            body = download_as_webp_from_url(
                best.image_url,
                client.session if best.source == "matsukiyo" else None,
            )
            (review_dir / f"{slug}.webp").write_bytes(body)
        except Exception:
            pass
        return result

    try:
        body = download_as_webp_from_url(
            best.image_url,
            client.session if best.source == "matsukiyo" else None,
        )
    except Exception as exc:
        result["status"] = "download_error"
        result["note"] = str(exc)
        return result

    local_path = save_local_webp(local_dir, slug, body)
    result["local_path"] = str(local_path)

    if upload:
        try:
            result["r2_url"] = upload_to_r2(slug, body)
            result["status"] = "uploaded"
        except Exception as exc:
            result["status"] = "upload_error"
            result["note"] = str(exc)
    else:
        result["status"] = "review_approved"

    return result


def summarize(results: list[dict[str, Any]]) -> dict[str, Any]:
    from collections import Counter

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total": len(results),
        "uploaded": sum(1 for r in results if r.get("status") == "uploaded"),
        "skipped_exists": sum(1 for r in results if r.get("status") == "skipped_exists"),
        "not_found": sum(1 for r in results if r.get("status") == "not_found"),
        "review_rejected": sum(1 for r in results if r.get("status") == "review_rejected"),
        "errors": sum(
            1 for r in results if str(r.get("status", "")).endswith("error")
        ),
        "by_source": dict(Counter(r.get("source") for r in results if r.get("status") == "uploaded")),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Retry OTC images with multi-source resolver")
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--local-dir", type=Path, default=DEFAULT_LOCAL)
    parser.add_argument("--label", type=str, default="retry")
    parser.add_argument("--upload", action="store_true", default=True)
    parser.add_argument("--no-upload", action="store_true")
    parser.add_argument("--delay", type=float, default=1.0)
    args = parser.parse_args()
    _load_env()

    items = load_items(args.plan)
    upload = args.upload and not args.no_upload
    client = MatsukiyoClient(delay_sec=args.delay)
    results: list[dict[str, Any]] = []

    for i, item in enumerate(items, 1):
        print(f"[{i}/{len(items)}] {item.get('product_name')}")
        results.append(process_retry_item(item, client, upload=upload, local_dir=args.local_dir))
        time.sleep(args.delay)

    out_path = args.out_dir / f"results_{args.label}.json"
    args.out_dir.mkdir(parents=True, exist_ok=True)
    summary = summarize(results)
    out_path.write_text(
        json.dumps({"summary": summary, "items": results}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
