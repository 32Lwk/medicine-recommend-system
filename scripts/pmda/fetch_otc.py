"""PMDA 市販薬差分 fetch → staging/otc_products.json。"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.pmda.common import (  # noqa: E402
    LOG_ANALYSIS_DIR,
    OTC_CSV,
    STAGING_OTC,
    load_json,
    product_key,
    read_csv_rows,
    save_json,
    utc_now_iso,
    write_fetch_log,
    write_live_fetch_log,
)
from scripts.pmda.http_client import PmdaFetchAborted, PmdaLiveSession  # noqa: E402
from scripts.pmda.normalize import normalize_otc_product_row  # noqa: E402
from scripts.pmda.queue import (  # noqa: E402
    mark_queue_done,
    mark_queue_failed,
    pop_queue_batch,
    product_key_to_row,
    restore_queue_pending,
)


def load_fixture_rows(fixture_path: Path) -> List[Dict[str, Any]]:
    data = load_json(fixture_path, [])
    if isinstance(data, dict) and isinstance(data.get("rows"), list):
        return data["rows"]
    if isinstance(data, list):
        return data
    return []


def select_diff_candidates(limit: int = 100) -> List[Dict[str, str]]:
    rows = read_csv_rows(OTC_CSV)
    candidates: List[Dict[str, str]] = []
    for row in rows:
        norm = normalize_otc_product_row(row)
        if norm:
            candidates.append(norm)
        if len(candidates) >= limit:
            break
    return candidates


def _write_otc_orphans(not_found: List[Dict[str, str]]) -> Path | None:
    if not not_found:
        return None
    stamp = datetime.now().strftime("%Y%m%d")
    path = LOG_ANALYSIS_DIR / f"pmda_otc_orphans_{stamp}.json"
    existing = load_json(path, {"orphans": []})
    if not isinstance(existing, dict):
        existing = {"orphans": []}
    existing.setdefault("orphans", []).extend(not_found)
    save_json(path, existing)
    return path


def fetch_otc_diff(
    *,
    live: bool = False,
    limit: int = 100,
    fixture_path: Path | None = None,
    min_interval: float = 3.0,
    batch_size: int = 10,
    resume: bool = False,
) -> Dict[str, Any]:
    rows: List[Dict[str, Any]] = []
    stats: Dict[str, Any] = {
        "requested": 0,
        "hits": 0,
        "errors": 0,
        "mode": "live" if live else "fixture",
        "abort_reason": "",
        "queue_done": [],
        "queue_failed": [],
    }
    diff_log: List[Dict[str, str]] = []
    orphans: List[Dict[str, str]] = []
    candidates: List[Dict[str, str]] = []

    if fixture_path:
        rows.extend(load_fixture_rows(fixture_path))
        stats["mode"] = "fixture"

    if live:
        if resume:
            keys = pop_queue_batch("otc", max_items=batch_size)
            candidates = [product_key_to_row(k) for k in keys]
        else:
            candidates = select_diff_candidates(limit=limit)
        stats["requested"] = len(candidates)

        session = PmdaLiveSession(min_interval_sec=min_interval, batch_size=batch_size)
        done_items: List[str] = []
        pending_restore: List[str] = [product_key(c["製品名"], c.get("メーカー名", "")) for c in candidates]
        try:
            with session:
                for product in candidates:
                    if session.aborted:
                        break
                    key = product_key(product["製品名"], product.get("メーカー名", ""))
                    pending_restore.remove(key)
                    name = product["製品名"]
                    parsed = session.fetch_and_parse_otc_product(name)
                    if session.stats.aborted:
                        pending_restore.insert(0, key)
                        break
                    if parsed:
                        merged = dict(product)
                        for field in ("効能効果", "用法用量", "年齢制限", "成分"):
                            if parsed.get(field):
                                merged[field] = parsed[field]
                        rows.append(merged)
                        diff_log.append(
                            {
                                "product_name": name,
                                "manufacturer": product.get("メーカー名", ""),
                                "pmda_hit": parsed.get("_pmda_title", "")[:120],
                                "status": "found",
                            }
                        )
                        if resume:
                            done_items.append(key)
                    else:
                        stats["errors"] += 1
                        orphan = {
                            "product_name": name,
                            "manufacturer": product.get("メーカー名", ""),
                            "status": "not_found",
                        }
                        diff_log.append(orphan)
                        orphans.append(orphan)
                        if resume:
                            mark_queue_failed("otc", key, "not_found")
                            stats["queue_failed"].append(key)
        except PmdaFetchAborted as exc:
            stats["abort_reason"] = str(exc)
        if resume and session.stats.aborted and pending_restore:
            restore_queue_pending("otc", pending_restore)
        if resume and done_items:
            mark_queue_done("otc", done_items)
            stats["queue_done"] = done_items
        stats["hits"] = session.stats.hits
        stats["errors"] = stats.get("errors", 0) or session.stats.errors
        if session.stats.aborted:
            stats["abort_reason"] = session.stats.abort_reason
        write_live_fetch_log({"source": "otc", "stats": stats, "diff_log": diff_log})
        _write_otc_orphans(orphans)
    elif not fixture_path:
        candidates = select_diff_candidates(limit=limit)
        rows.extend(candidates[: min(limit, len(candidates))])

    normalized = [normalize_otc_product_row(r) for r in rows if normalize_otc_product_row(r)]
    payload = {
        "generated_at": utc_now_iso(),
        "source": stats["mode"],
        "stats": stats,
        "diff_log": diff_log,
        "rows": normalized,
        "live_only": live,
    }
    save_json(STAGING_OTC, payload)
    write_fetch_log("otc_diff", {"stats": stats, "diff_count": len(diff_log), "staging_count": len(normalized)})
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch PMDA OTC diff into staging JSON")
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--fixture", type=Path, default=None)
    parser.add_argument("--min-interval", type=float, default=3.0)
    parser.add_argument("--live-batch-size", type=int, default=10)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()

    fixture = args.fixture
    if fixture is None and not args.live:
        default_fixture = ROOT / "tests" / "fixtures" / "pmda" / "otc_staging.json"
        if default_fixture.is_file():
            fixture = default_fixture

    result = fetch_otc_diff(
        live=args.live,
        limit=args.limit,
        fixture_path=fixture,
        min_interval=args.min_interval,
        batch_size=args.live_batch_size,
        resume=args.resume,
    )
    print(json.dumps({"staging": str(STAGING_OTC), "stats": result["stats"]}, ensure_ascii=False, indent=2))
    return 1 if result["stats"].get("abort_reason") else 0


if __name__ == "__main__":
    raise SystemExit(main())
