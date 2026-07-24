"""PMDA 副作用 fetch → staging/side_effects.json。"""
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
    STAGING_SIDE_EFFECTS,
    extract_otc_ingredients,
    load_json,
    record_live_fetch_session,
    save_json,
    utc_now_iso,
    write_fetch_log,
    write_live_fetch_log,
    write_otc_ingredients_json,
)
from scripts.pmda.expand_side_effects import expand_side_effects_from_catalog  # noqa: E402
from scripts.pmda.fetch_interactions import PRIORITY_INGREDIENTS  # noqa: E402
from scripts.pmda.http_client import PmdaFetchAborted, PmdaLiveSession  # noqa: E402
from scripts.pmda.normalize import dedupe_side_effects, normalize_side_effect_row  # noqa: E402


def load_fixture_rows(fixture_path: Path) -> List[Dict[str, Any]]:
    data = load_json(fixture_path, [])
    if isinstance(data, dict) and isinstance(data.get("rows"), list):
        return data["rows"]
    if isinstance(data, list):
        return data
    return []


def fetch_side_effects(
    *,
    live: bool = False,
    limit: int | None = None,
    fixture_path: Path | None = None,
    min_interval: float = 3.0,
    batch_size: int = 30,
    live_only: bool = False,
) -> Dict[str, Any]:
    write_otc_ingredients_json()
    rows: List[Dict[str, Any]] = []
    stats: Dict[str, Any] = {
        "requested": 0,
        "hits": 0,
        "errors": 0,
        "mode": "catalog_expansion",
        "abort_reason": "",
    }

    if live:
        stats["mode"] = "live"
        ingredients = list(PRIORITY_INGREDIENTS)
        if limit:
            ingredients = ingredients[:limit]
        batch_limit = limit or batch_size
        ingredients = ingredients[:batch_limit]
        stats["requested"] = len(ingredients)

        session = PmdaLiveSession(min_interval_sec=min_interval, batch_size=batch_size)
        try:
            with session:
                for ingredient in ingredients:
                    if session.aborted:
                        break
                    html = session.fetch_packins_section(ingredient, "11")
                    if html:
                        rows.extend(session.parse_side_effects_from_html(html, ingredient))
        except PmdaFetchAborted as exc:
            stats["abort_reason"] = str(exc)
        stats["hits"] = session.stats.hits
        stats["errors"] = session.stats.errors
        stats["cache_hits"] = session.stats.cache_hits
        stats["empty_html"] = session.stats.empty_html
        stats["http_requests"] = session.stats.requested
        if session.stats.aborted:
            stats["abort_reason"] = session.stats.abort_reason
        record_live_fetch_session(stats=stats, aborted=session.stats.aborted, abort_reason=stats.get("abort_reason", ""))
        write_live_fetch_log({"source": "side_effects", "stats": stats})
    else:
        rows.extend(expand_side_effects_from_catalog())
        if fixture_path:
            rows.extend(load_fixture_rows(fixture_path))
            stats["mode"] = "fixture"

    normalized = dedupe_side_effects(
        [normalize_side_effect_row(r) for r in rows if normalize_side_effect_row(r)]
    )
    payload = {
        "generated_at": utc_now_iso(),
        "source": stats["mode"],
        "stats": stats,
        "rows": normalized,
        "live_only": live_only,
    }
    save_json(STAGING_SIDE_EFFECTS, payload)
    write_fetch_log("side_effects_import", {"stats": stats, "staging_count": len(normalized)})
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch PMDA side effects into staging JSON")
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--fixture", type=Path, default=None)
    parser.add_argument("--min-interval", type=float, default=3.0)
    parser.add_argument("--live-batch-size", type=int, default=30)
    parser.add_argument("--live-only", action="store_true")
    args = parser.parse_args()

    fixture = args.fixture
    if fixture is None and not args.live:
        default_fixture = ROOT / "tests" / "fixtures" / "pmda" / "side_effects_staging.json"
        if default_fixture.is_file():
            fixture = default_fixture

    result = fetch_side_effects(
        live=args.live,
        limit=args.limit,
        fixture_path=fixture,
        min_interval=args.min_interval,
        batch_size=args.live_batch_size,
        live_only=args.live_only,
    )
    print(json.dumps({"staging": str(STAGING_SIDE_EFFECTS), "stats": result["stats"]}, ensure_ascii=False, indent=2))
    return 1 if result["stats"].get("abort_reason") else 0


if __name__ == "__main__":
    raise SystemExit(main())
