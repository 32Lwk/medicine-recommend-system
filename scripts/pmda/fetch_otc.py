"""PMDA 市販薬差分 fetch → staging/otc_products.json。"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.pmda.common import (  # noqa: E402
    OTC_CSV,
    STAGING_OTC,
    load_json,
    normalize_text,
    product_key,
    read_csv_rows,
    save_json,
    utc_now_iso,
    write_fetch_log,
)
from scripts.pmda.http_client import PmdaFetchAborted, PmdaLiveSession  # noqa: E402
from scripts.pmda.normalize import normalize_otc_product_row  # noqa: E402


def load_fixture_rows(fixture_path: Path) -> List[Dict[str, Any]]:
    data = load_json(fixture_path, [])
    if isinstance(data, dict) and isinstance(data.get("rows"), list):
        return data["rows"]
    if isinstance(data, list):
        return data
    return []


def select_diff_candidates(limit: int = 100) -> List[Dict[str, str]]:
    """初回は baseline からサンプル品目を選ぶ（差分 fetch 対象）。"""
    rows = read_csv_rows(OTC_CSV)
    candidates: List[Dict[str, str]] = []
    for row in rows:
        norm = normalize_otc_product_row(row)
        if norm:
            candidates.append(norm)
        if len(candidates) >= limit:
            break
    return candidates


def fetch_otc_diff(
    *,
    live: bool = False,
    limit: int = 100,
    fixture_path: Path | None = None,
    min_interval: float = 3.0,
    batch_size: int = 10,
) -> Dict[str, Any]:
    rows: List[Dict[str, Any]] = []
    stats = {"requested": 0, "hits": 0, "errors": 0, "mode": "live" if live else "fixture"}

    if fixture_path:
        rows.extend(load_fixture_rows(fixture_path))
        stats["mode"] = "fixture"

    candidates = select_diff_candidates(limit=limit)
    diff_log: List[Dict[str, str]] = []

    if live:
        stats["requested"] = min(limit, len(candidates))
        session = PmdaLiveSession(min_interval_sec=min_interval, batch_size=batch_size)
        try:
            with session:
                for product in candidates[:limit]:
                    if session.aborted:
                        break
                    name = product["製品名"]
                    html = session.fetch_otc_search(name)
                    if html:
                        hits = PmdaLiveSession.extract_links(html, "https://www.pmda.go.jp/PmdaSearch/otcSearch/")
                        product_hits = [
                            h
                            for h in hits
                            if name in h["text"] or normalize_text(name) in h["text"]
                        ]
                        if product_hits:
                            stats["hits"] += 1
                            diff_log.append(
                                {
                                    "product_name": name,
                                    "manufacturer": product.get("メーカー名", ""),
                                    "pmda_hit": product_hits[0]["text"][:120],
                                    "status": "found",
                                }
                            )
                            rows.append(product)
                        else:
                            stats["errors"] += 1
                            diff_log.append(
                                {
                                    "product_name": name,
                                    "manufacturer": product.get("メーカー名", ""),
                                    "status": "not_found",
                                }
                            )
                    else:
                        stats["errors"] += 1
        except PmdaFetchAborted as exc:
            stats["abort_reason"] = str(exc)
        if session.stats.aborted:
            stats["abort_reason"] = session.stats.abort_reason
    else:
        rows.extend(candidates[: min(limit, len(candidates))])

    normalized = [normalize_otc_product_row(r) for r in rows if normalize_otc_product_row(r)]
    payload = {
        "generated_at": utc_now_iso(),
        "source": stats["mode"],
        "stats": stats,
        "diff_log": diff_log,
        "rows": normalized,
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
    )
    print(json.dumps({"staging": str(STAGING_OTC), "stats": result["stats"]}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
