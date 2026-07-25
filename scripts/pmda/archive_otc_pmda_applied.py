#!/usr/bin/env python3
"""既に CSV へ反映済みの PMDA OTC 更新を raw へ保全し、pmda_* カラムを追加する。

再 live fetch は行わない（大規模コスト回避）。
pmda_薬効分類 / pmda_リスク区分 は過去ランでは HTML 未保全のため空欄のまま追加する。
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.pmda.common import (  # noqa: E402
    OTC_CSV,
    PMDA_DIR,
    product_key,
    update_manifest,
    utc_now_iso,
    write_csv_rows,
)
from scripts.pmda.merge_into_csv import OTC_FIELDS  # noqa: E402
from scripts.pmda.normalize import normalize_otc_product_row  # noqa: E402
from scripts.pmda.queue import get_live_fetch_queue  # noqa: E402
from scripts.pmda.raw_store import RAW_OTC_DIR, otc_raw_stats  # noqa: E402

PMDA_CONTENT_FIELDS = ("効能効果", "用法用量", "年齢制限", "成分")
BASELINE_DEFAULT = PMDA_DIR / "backups" / "20260724" / "otc_medicine_data.csv"


def _load_csv(path: Path) -> Dict[str, Dict[str, str]]:
    rows: Dict[str, Dict[str, str]] = {}
    with path.open(encoding="utf-8-sig", newline="") as f:
        for raw in csv.DictReader(f):
            norm = normalize_otc_product_row(raw)
            if not norm:
                continue
            rows[product_key(norm["製品名"], norm["メーカー名"])] = norm
    return rows


def archive_applied_updates(
    *,
    baseline_path: Path,
    stamp: str,
) -> Dict[str, Any]:
    baseline = _load_csv(baseline_path)
    current = _load_csv(OTC_CSV)
    queue = get_live_fetch_queue().get("otc") or {}
    done = set(queue.get("done") or [])
    failed = set((queue.get("failed") or {}).keys())

    RAW_OTC_DIR.mkdir(parents=True, exist_ok=True)
    archive_dir = PMDA_DIR / "raw" / "otc"
    archive_dir.mkdir(parents=True, exist_ok=True)
    jsonl_path = archive_dir / f"applied_updates_{stamp}.jsonl"
    summary_path = archive_dir / f"applied_updates_{stamp}_summary.json"

    updated_keys: List[str] = []
    field_change_counts = {f: 0 for f in PMDA_CONTENT_FIELDS}
    archived_files = 0

    with jsonl_path.open("w", encoding="utf-8") as out:
        for key, cur in current.items():
            base = baseline.get(key) or {}
            changed: Dict[str, Dict[str, str]] = {}
            for field in PMDA_CONTENT_FIELDS:
                bv = (base.get(field) or "").strip()
                cv = (cur.get(field) or "").strip()
                if bv != cv and cv:
                    changed[field] = {"before": bv, "after": cv}
                    field_change_counts[field] += 1
            if not changed:
                continue
            updated_keys.append(key)
            record = {
                "product_key": key,
                "製品名": cur.get("製品名") or "",
                "メーカー名": cur.get("メーカー名") or "",
                "queue_status": "done" if key in done else ("failed" if key in failed else "unknown"),
                "changed_fields": changed,
                "applied": {f: cur.get(f) or "" for f in PMDA_CONTENT_FIELDS},
                "pmda_薬効分類": cur.get("pmda_薬効分類") or "",
                "pmda_リスク区分": cur.get("pmda_リスク区分") or "",
                "archived_at": utc_now_iso(),
                "note": "Recovered from CSV vs baseline diff; detail_html not available (no re-fetch).",
            }
            out.write(json.dumps(record, ensure_ascii=False) + "\n")

    # 再取得なし保全は jsonl を正本とする（品目 JSON は HTML 付き live 時のみ）。
    archived_files = 0

    summary = {
        "generated_at": utc_now_iso(),
        "baseline": str(baseline_path),
        "csv": str(OTC_CSV),
        "jsonl": str(jsonl_path),
        "products_with_pmda_content_updates": len(updated_keys),
        "field_change_counts": field_change_counts,
        "raw_product_files_written": archived_files,
        "otc_raw_stats": otc_raw_stats(),
        "pmda_taxonomy_columns": {
            "pmda_薬効分類": "added empty (historical HTML not retained; fill on future live fetch)",
            "pmda_リスク区分": "added empty (historical HTML not retained; fill on future live fetch)",
        },
        "queue": {
            "done": len(done),
            "failed": len(failed),
        },
        "note": "Per-product raw JSON under otc_products/ is written on future live fetch (with detail_html).",
    }
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return summary


def ensure_pmda_columns_on_csv() -> Dict[str, Any]:
    """全行に pmda_* カラムを追加（既存値は保持、無ければ空）。"""
    rows: List[Dict[str, str]] = []
    with OTC_CSV.open(encoding="utf-8-sig", newline="") as f:
        for raw in csv.DictReader(f):
            norm = normalize_otc_product_row(raw)
            if norm:
                rows.append(norm)
    count = write_csv_rows(OTC_CSV, OTC_FIELDS, rows)
    update_manifest(otc_medicine_data={"row_count": count, "source": "PMDA OTC Search"})
    nonempty_yakkou = sum(1 for r in rows if (r.get("pmda_薬効分類") or "").strip())
    nonempty_risk = sum(1 for r in rows if (r.get("pmda_リスク区分") or "").strip())
    return {
        "row_count": count,
        "pmda_薬効分類_nonempty": nonempty_yakkou,
        "pmda_リスク区分_nonempty": nonempty_risk,
        "fields": OTC_FIELDS,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Archive applied PMDA OTC updates; add pmda_* columns")
    parser.add_argument("--baseline", type=Path, default=BASELINE_DEFAULT)
    parser.add_argument("--stamp", default="20260725")
    args = parser.parse_args()

    if not args.baseline.is_file():
        print(json.dumps({"ok": False, "reason": f"baseline missing: {args.baseline}"}, ensure_ascii=False))
        return 1

    col_stats = ensure_pmda_columns_on_csv()
    archive_stats = archive_applied_updates(baseline_path=args.baseline, stamp=args.stamp)
    result = {"ok": True, "columns": col_stats, "archive": archive_stats}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
