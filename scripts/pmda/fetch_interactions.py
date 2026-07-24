"""PMDA 相互作用 fetch → staging/interactions.json。"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Set

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.pmda.common import (  # noqa: E402
    PRIORITY_INGREDIENTS,
    STAGING_INTERACTIONS,
    extract_otc_ingredients,
    load_common_rx_medications,
    load_json,
    record_live_fetch_session,
    save_json,
    utc_now_iso,
    write_fetch_log,
    write_live_fetch_log,
    write_otc_ingredients_json,
)
from scripts.pmda.expand_interactions import expand_interactions_from_catalog  # noqa: E402
from scripts.pmda.http_client import PmdaFetchAborted, PmdaLiveSession  # noqa: E402
from scripts.pmda.normalize import dedupe_interactions, normalize_interaction_row  # noqa: E402
from scripts.pmda.queue import mark_queue_done, mark_queue_failed, pop_queue_batch, restore_queue_pending  # noqa: E402


def load_fixture_rows(fixture_path: Path) -> List[Dict[str, Any]]:
    data = load_json(fixture_path, [])
    if isinstance(data, dict) and isinstance(data.get("rows"), list):
        return data["rows"]
    if isinstance(data, list):
        return data
    return []


def build_unique_ingredient_queue(
    *,
    max_ingredients: int | None = None,
    max_otc: int | None = None,
) -> List[str]:
    """live fetch 対象: 優先成分 + OTC カタログ成分（重複排除）。"""
    seen: Set[str] = set()
    ordered: List[str] = []
    for name in PRIORITY_INGREDIENTS + extract_otc_ingredients(limit=max_otc):
        key = name.strip()
        if not key or key in seen:
            continue
        seen.add(key)
        ordered.append(key)
        if max_ingredients and len(ordered) >= max_ingredients:
            break
    return ordered


def fetch_interactions(
    *,
    live: bool = False,
    limit: int | None = None,
    fixture_path: Path | None = None,
    max_otc: int | None = None,
    min_interval: float = 3.0,
    batch_size: int = 30,
    live_only: bool = False,
    resume: bool = False,
    ingredient_batch: int = 30,
) -> Dict[str, Any]:
    write_otc_ingredients_json()
    rows: List[Dict[str, Any]] = []
    stats: Dict[str, Any] = {
        "requested_ingredients": 0,
        "requested_pairs": 0,
        "cache_hits": 0,
        "hits": 0,
        "errors": 0,
        "mode": "catalog_expansion",
        "abort_reason": "",
        "queue_done": [],
        "queue_failed": [],
        "queue_no_data": [],
    }

    if live:
        stats["mode"] = "live"
        partners = load_common_rx_medications()
        if resume:
            ingredients = pop_queue_batch("interactions", max_items=ingredient_batch)
        else:
            ingredients = build_unique_ingredient_queue(max_ingredients=limit or ingredient_batch, max_otc=max_otc)
        stats["requested_ingredients"] = len(ingredients)
        stats["requested_pairs"] = len(ingredients) * len(partners)

        session = PmdaLiveSession(min_interval_sec=min_interval, batch_size=batch_size)
        done_items: List[str] = []
        pending_restore: List[str] = list(ingredients)
        try:
            with session:
                for ingredient in ingredients:
                    if session.aborted:
                        break
                    pending_restore.remove(ingredient)
                    section_html = session.fetch_packins_section(ingredient, "10")
                    if session.stats.aborted:
                        pending_restore.insert(0, ingredient)
                        break
                    if section_html:
                        parsed = session.parse_interactions_from_html(section_html, ingredient, partners)
                        if parsed:
                            rows.extend(parsed)
                        if resume:
                            done_items.append(ingredient)
                            if not parsed:
                                stats["queue_no_data"].append(ingredient)
                    elif resume:
                        mark_queue_failed("interactions", ingredient, "empty_section")
                        stats["queue_failed"].append(ingredient)
        except PmdaFetchAborted as exc:
            stats["abort_reason"] = str(exc)
        if resume and session.stats.aborted and pending_restore:
            restore_queue_pending("interactions", pending_restore)
        if resume and done_items:
            mark_queue_done("interactions", done_items)
            stats["queue_done"] = done_items
        stats["cache_hits"] = session.stats.cache_hits
        stats["hits"] = session.stats.hits
        stats["errors"] = session.stats.errors
        stats["requested"] = session.stats.requested
        stats["empty_html"] = session.stats.empty_html
        if session.stats.aborted:
            stats["abort_reason"] = session.stats.abort_reason
        record_live_fetch_session(stats=stats, aborted=session.stats.aborted, abort_reason=stats.get("abort_reason", ""))
        write_live_fetch_log({"source": "interactions", "stats": stats})
    else:
        rows.extend(expand_interactions_from_catalog())
        if fixture_path:
            rows.extend(load_fixture_rows(fixture_path))
            stats["mode"] = "fixture"

    normalized = dedupe_interactions(
        [normalize_interaction_row(r) for r in rows if normalize_interaction_row(r)]
    )
    payload = {
        "generated_at": utc_now_iso(),
        "source": stats["mode"],
        "stats": stats,
        "rows": normalized,
        "live_only": live_only,
    }
    save_json(STAGING_INTERACTIONS, payload)
    write_fetch_log("interactions_import", {"stats": stats, "staging_count": len(normalized)})
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch PMDA drug interactions into staging JSON")
    parser.add_argument("--live", action="store_true", help="Query PMDA (rate-limited)")
    parser.add_argument("--limit", type=int, default=None, help="Max unique ingredients (live mode)")
    parser.add_argument("--fixture", type=Path, default=None, help="Fixture JSON path")
    parser.add_argument("--max-otc", type=int, default=80, help="Max OTC ingredients for queue")
    parser.add_argument("--min-interval", type=float, default=3.0, help="Min seconds between requests")
    parser.add_argument("--live-batch-size", type=int, default=30, help="Max HTTP requests per session")
    parser.add_argument("--live-only", action="store_true", help="Staging contains live rows only")
    parser.add_argument("--resume", action="store_true", help="Pop batch from manifest queue")
    parser.add_argument("--ingredient-batch", type=int, default=10, help="Ingredients per resume session")
    args = parser.parse_args()

    fixture = args.fixture
    if fixture is None and not args.live:
        default_fixture = ROOT / "tests" / "fixtures" / "pmda" / "interactions_staging.json"
        if default_fixture.is_file():
            fixture = default_fixture

    result = fetch_interactions(
        live=args.live,
        limit=args.limit,
        fixture_path=fixture,
        max_otc=args.max_otc,
        min_interval=args.min_interval,
        batch_size=args.live_batch_size,
        live_only=args.live_only,
        resume=args.resume,
        ingredient_batch=args.ingredient_batch,
    )
    print(json.dumps({"staging": str(STAGING_INTERACTIONS), "stats": result["stats"]}, ensure_ascii=False, indent=2))
    return 1 if result["stats"].get("abort_reason") else 0


if __name__ == "__main__":
    raise SystemExit(main())
