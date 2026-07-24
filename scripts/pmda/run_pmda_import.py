#!/usr/bin/env python3
"""PMDA import オーケストレータ: fetch → validate → merge。"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.pmda.common import (  # noqa: E402
    STAGING_INTERACTIONS,
    STAGING_OTC,
    STAGING_SIDE_EFFECTS,
    backup_csv_files,
    ensure_pmda_dirs,
    load_json,
    write_live_fetch_log,
)
from scripts.pmda.fetch_interactions import fetch_interactions  # noqa: E402
from scripts.pmda.fetch_otc import fetch_otc_diff  # noqa: E402
from scripts.pmda.fetch_side_effects import fetch_side_effects  # noqa: E402
from scripts.pmda.merge_into_csv import merge_interactions, merge_otc_products, merge_side_effects  # noqa: E402
from scripts.pmda.queue import check_live_fetch_guards, init_live_fetch_queue  # noqa: E402
from scripts.pmda.validate_pmda_import import validate_all_staging  # noqa: E402


def run_import(
    *,
    sources: list[str],
    live: bool = False,
    dry_run: bool = False,
    limit: int | None = None,
    fixture_dir: Path | None = None,
    min_interval: float = 3.0,
    live_batch_size: int = 30,
    skip_fetch: bool = False,
    resume: bool = False,
    ingredient_batch: int = 10,
    force: bool = False,
    allow_daytime: bool = False,
) -> dict:
    ensure_pmda_dirs()
    fixture_dir = fixture_dir or (ROOT / "tests" / "fixtures" / "pmda")

    if live:
        ok, reason = check_live_fetch_guards(force=force, allow_daytime=allow_daytime)
        if not ok:
            return {"ok": False, "stage": "guard", "reason": reason}

    fetch_stats = {}
    if not skip_fetch:
        if "interactions" in sources:
            fixture = fixture_dir / "interactions_staging.json"
            fetch_stats["interactions"] = fetch_interactions(
                live=live,
                limit=limit,
                fixture_path=None if live else fixture,
                min_interval=min_interval,
                batch_size=live_batch_size,
                live_only=live,
                resume=resume,
                ingredient_batch=ingredient_batch,
            )["stats"]
        if "side_effects" in sources:
            fixture = fixture_dir / "side_effects_staging.json"
            fetch_stats["side_effects"] = fetch_side_effects(
                live=live,
                limit=limit,
                fixture_path=None if live else fixture,
                min_interval=min_interval,
                batch_size=live_batch_size,
                live_only=live,
                resume=resume,
                ingredient_batch=ingredient_batch,
            )["stats"]
        if "otc" in sources:
            fixture = fixture_dir / "otc_staging.json"
            otc_batch = min(live_batch_size, 10)
            fetch_stats["otc"] = fetch_otc_diff(
                live=live,
                limit=limit or (otc_batch if live else 100),
                fixture_path=None if live else fixture,
                min_interval=min_interval,
                batch_size=otc_batch,
                resume=resume,
            )["stats"]

        if live:
            write_live_fetch_log({"stage": "fetch_complete", "sources": sources, "fetch_stats": fetch_stats})

    validation = validate_all_staging()
    if not validation["ok"]:
        return {
            "ok": False,
            "stage": "validate",
            "fetch_stats": fetch_stats,
            "validation": validation,
        }

    if dry_run:
        return {
            "ok": True,
            "dry_run": True,
            "fetch_stats": fetch_stats,
            "validation": {
                "interactions": validation["interactions"],
                "side_effects": validation["side_effects"],
                "otc_products": validation["otc_products"],
            },
        }

    backup_dir = backup_csv_files()
    merge_stats = {}
    norm = validation["normalized"]
    staging_ix = load_json(STAGING_INTERACTIONS, {})
    staging_se = load_json(STAGING_SIDE_EFFECTS, {})
    live_replace_ix = isinstance(staging_ix, dict) and staging_ix.get("live_only")
    live_replace_se = isinstance(staging_se, dict) and staging_se.get("live_only")
    if "interactions" in sources:
        merge_stats["interactions"] = merge_interactions(
            norm["interactions"],
            live_replace=bool(live_replace_ix),
        )
    if "side_effects" in sources:
        merge_stats["side_effects"] = merge_side_effects(
            norm["side_effects"],
            live_replace=bool(live_replace_se),
        )
    if "otc" in sources:
        merge_stats["otc"] = merge_otc_products(norm["otc_products"])

    return {
        "ok": True,
        "dry_run": False,
        "backup_dir": str(backup_dir),
        "fetch_stats": fetch_stats,
        "validation": {
            "interactions": validation["interactions"],
            "side_effects": validation["side_effects"],
            "otc_products": validation["otc_products"],
        },
        "merge_stats": merge_stats,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run PMDA data import pipeline")
    parser.add_argument(
        "--sources",
        default="interactions,side_effects,otc",
        help="Comma-separated: interactions,side_effects,otc",
    )
    parser.add_argument("--live", action="store_true", help="Fetch from PMDA websites")
    parser.add_argument("--dry-run", action="store_true", help="Validate only, no CSV merge")
    parser.add_argument("--limit", type=int, default=None, help="Live fetch limit per source")
    parser.add_argument("--fixture-dir", type=Path, default=None)
    parser.add_argument("--min-interval", type=float, default=3.0, help="Min seconds between HTTP requests")
    parser.add_argument("--live-batch-size", type=int, default=30, help="Max HTTP requests per live session")
    parser.add_argument("--skip-fetch", action="store_true", help="Validate/merge existing staging only")
    parser.add_argument("--resume", action="store_true", help="Resume from manifest queue")
    parser.add_argument("--init-queue", action="store_true", help="Rebuild live_fetch_queue in manifest")
    parser.add_argument("--ingredient-batch", type=int, default=10, help="Ingredients per resume session")
    parser.add_argument("--force", action="store_true", help="Skip all guards (tests only)")
    parser.add_argument("--allow-daytime", action="store_true", help="Skip JST time window guard (4h gap still enforced)")
    args = parser.parse_args()

    sources = [s.strip() for s in args.sources.split(",") if s.strip()]
    if args.init_queue:
        queue = init_live_fetch_queue(sources=sources)
        print(json.dumps({"ok": True, "live_fetch_queue": queue}, ensure_ascii=False, indent=2))
        if not args.live and not args.dry_run and not args.skip_fetch:
            return 0

    result = run_import(
        sources=sources,
        live=args.live,
        dry_run=args.dry_run,
        limit=args.limit,
        fixture_dir=args.fixture_dir,
        min_interval=args.min_interval,
        live_batch_size=args.live_batch_size,
        skip_fetch=args.skip_fetch,
        resume=args.resume,
        ingredient_batch=args.ingredient_batch,
        force=args.force,
        allow_daytime=args.allow_daytime,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
