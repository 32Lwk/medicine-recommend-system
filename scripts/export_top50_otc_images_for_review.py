#!/usr/bin/env python3
"""top50_plan.json の全品目画像を CDN からレビュー用フォルダへ一括ダウンロード。"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

import requests

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEFAULT_PLAN = ROOT / "log" / "analysis" / "otc_image_sync_top50" / "top50_plan.json"
DEFAULT_OUT = ROOT / "log" / "analysis" / "otc_image_review_top50"
CDN_BASE = "https://images.yutok.dev/otc/"


def _load_versions() -> dict[str, str]:
    path = ROOT / "data" / "otc_image_versions.json"
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        return {str(k): str(v) for k, v in raw.items() if v}
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        return {}


def _cdn_url(slug: str, version: str | None) -> str:
    encoded = quote(slug, safe="")
    url = f"{CDN_BASE}{encoded}.webp"
    if version:
        url = f"{url}?v={version}"
    return url


def _content_hash(body: bytes) -> str:
    return hashlib.sha256(body).hexdigest()[:8]


def _safe_filename(rank: int, slug: str) -> str:
    safe = slug.replace("/", "-").replace("\\", "-")
    return f"{rank:02d}_{safe}.webp"


def export_for_review(
    plan_path: Path,
    out_dir: Path,
    *,
    overwrite: bool = False,
) -> dict:
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    if not isinstance(plan, list):
        raise ValueError(f"plan must be a list: {plan_path}")

    images_dir = out_dir / "images"
    images_dir.mkdir(parents=True, exist_ok=True)

    versions = _load_versions()
    session = requests.Session()
    session.headers["User-Agent"] = "Mozilla/5.0 medicine-recommend/1.0 otc-review-export"

    items: list[dict] = []
    hash_groups: dict[str, list[str]] = defaultdict(list)

    for rank, row in enumerate(plan, start=1):
        slug = str(row.get("slug") or "").strip()
        product_name = str(row.get("product_name") or "").strip()
        manufacturer = str(row.get("manufacturer") or "").strip()
        version = versions.get(slug, "")
        url = _cdn_url(slug, version or None)
        dest = images_dir / _safe_filename(rank, slug)

        entry: dict = {
            "rank": rank,
            "product_name": product_name,
            "manufacturer": manufacturer,
            "slug": slug,
            "medicine_type": row.get("medicine_type", ""),
            "recommendation_count": row.get("recommendation_count", 0),
            "image_version": version,
            "cdn_url": url,
            "local_file": str(dest.relative_to(out_dir)).replace("\\", "/"),
            "status": "pending",
        }

        if dest.is_file() and not overwrite:
            body = dest.read_bytes()
            entry["status"] = "skipped_exists"
            entry["bytes"] = len(body)
            entry["content_hash"] = _content_hash(body)
            items.append(entry)
            hash_groups[entry["content_hash"]].append(slug)
            continue

        try:
            resp = session.get(url, timeout=60)
            resp.raise_for_status()
            body = resp.content
            dest.write_bytes(body)
            entry["status"] = "downloaded"
            entry["bytes"] = len(body)
            entry["content_hash"] = _content_hash(body)
        except requests.RequestException as exc:
            entry["status"] = "error"
            entry["error"] = str(exc)

        items.append(entry)
        if entry.get("content_hash"):
            hash_groups[entry["content_hash"]].append(slug)

    duplicate_groups = [
        {"content_hash": h, "slugs": slugs}
        for h, slugs in sorted(hash_groups.items(), key=lambda x: (-len(x[1]), x[0]))
        if len(slugs) > 1
    ]

    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "plan_source": str(plan_path.relative_to(ROOT)).replace("\\", "/"),
        "output_dir": str(out_dir.relative_to(ROOT)).replace("\\", "/"),
        "total": len(items),
        "downloaded": sum(1 for i in items if i["status"] == "downloaded"),
        "skipped_exists": sum(1 for i in items if i["status"] == "skipped_exists"),
        "errors": sum(1 for i in items if i["status"] == "error"),
        "duplicate_hash_groups_in_top50": len(duplicate_groups),
        "items": items,
        "duplicate_hash_groups": duplicate_groups,
    }

    manifest_path = out_dir / "manifest.json"
    manifest_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    _write_review_md(out_dir / "REVIEW.md", summary)
    return summary


def _write_review_md(path: Path, summary: dict) -> None:
    lines = [
        "# OTC 画像レビュー — top50",
        "",
        f"- 生成日時 (UTC): {summary['generated_at']}",
        f"- 品目数: {summary['total']}",
        f"- ダウンロード: {summary['downloaded']} / スキップ: {summary['skipped_exists']} / エラー: {summary['errors']}",
        f"- top50 内の同一 hash グループ: {summary['duplicate_hash_groups_in_top50']}",
        "",
        "## レビュー手順",
        "",
        "1. `images/` フォルダを開き、ファイル名（`01_スラッグ.webp`）とパッケージ表記を照合",
        "2. 問題がある行の **確認** 列に `NG`、問題なければ `OK` を記入",
        "3. NG の場合は `memo` 列に正しい製品名や備考を記入",
        "",
        "## 品目一覧",
        "",
        "| # | 製品名 | スラッグ | 推奨回数 | hash | 確認 | memo |",
        "|---|--------|----------|----------|------|------|------|",
    ]
    for item in summary["items"]:
        rank = item["rank"]
        name = item["product_name"].replace("|", "\\|")
        slug = item["slug"].replace("|", "\\|")
        count = item.get("recommendation_count", 0)
        h = item.get("content_hash", "")
        status = item["status"]
        if status == "error":
            lines.append(f"| {rank} | {name} | `{slug}` | {count} | — | **ERROR** | {item.get('error', '')} |")
        else:
            img = Path(item.get("local_file", "")).name
            lines.append(
                f"| {rank} | {name} | `{slug}` | {count} | `{h}` |  | [{img}](images/{img}) |"
            )

    if summary.get("duplicate_hash_groups"):
        lines.extend(
            [
                "",
                "## 同一 hash（要目視確認）",
                "",
                "別製品なのに同じ画像の可能性があります。",
                "",
            ]
        )
        for group in summary["duplicate_hash_groups"]:
            slugs = "、".join(f"`{s}`" for s in group["slugs"])
            lines.append(f"- `{group['content_hash']}`: {slugs}")

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Export top50 OTC images for manual review")
    parser.add_argument("--plan", type=Path, default=DEFAULT_PLAN)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--overwrite", action="store_true", help="Re-download even if file exists")
    args = parser.parse_args()

    if not args.plan.is_file():
        print(f"plan not found: {args.plan}", file=sys.stderr)
        return 1

    summary = export_for_review(args.plan, args.out_dir, overwrite=args.overwrite)
    print(
        json.dumps(
            {
                "output": str(args.out_dir.relative_to(ROOT)),
                "total": summary["total"],
                "downloaded": summary["downloaded"],
                "skipped_exists": summary["skipped_exists"],
                "errors": summary["errors"],
                "duplicate_hash_groups": summary["duplicate_hash_groups_in_top50"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 1 if summary["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
