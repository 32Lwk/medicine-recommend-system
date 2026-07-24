"""保存済み raw HTML から staging / CSV 正本を再生成。"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.pmda.common import (
    RAW_INGREDIENTS_DIR,
    STAGING_INTERACTIONS,
    STAGING_SIDE_EFFECTS,
    backup_csv_files,
    load_common_rx_medications,
    save_json,
    utc_now_iso,
    write_fetch_log,
)
from scripts.pmda.http_client import PmdaLiveSession
from scripts.pmda.merge_into_csv import merge_interactions, merge_side_effects
from scripts.pmda.normalize import dedupe_interactions, dedupe_side_effects
from scripts.pmda.quality_filter import filter_interactions, filter_side_effects
from scripts.pmda.raw_store import raw_stats
from scripts.pmda.validate_pmda_import import validate_all_staging


def reparse_all_raw(*, dry_run: bool = False) -> Dict[str, Any]:
    partners = load_common_rx_medications()
    session = PmdaLiveSession(min_interval_sec=0, batch_size=0)

    ix_rows: List[Dict[str, str]] = []
    se_rows: List[Dict[str, str]] = []
    stats: Dict[str, Any] = {
        "mode": "reparse_from_raw",
        "raw_files": raw_stats(),
        "parsed_ingredients": 0,
        "skipped_no_html": 0,
        "empty_section": 0,
        "interactions_raw": 0,
        "side_effects_raw": 0,
    }

    for path in sorted(RAW_INGREDIENTS_DIR.glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        ingredient = payload.get("ingredient") or ""
        html = payload.get("detail_html") or ""
        if not html:
            stats["skipped_no_html"] += 1
            continue

        section10 = PmdaLiveSession.extract_section_from_html(html, "10")
        section11 = PmdaLiveSession.extract_section_from_html(html, "11")
        if not section10 and not section11:
            stats["empty_section"] += 1
            continue

        stats["parsed_ingredients"] += 1
        if section10:
            parsed_ix = session.parse_interactions_from_html(section10, ingredient, partners)
            stats["interactions_raw"] += len(parsed_ix)
            ix_rows.extend(parsed_ix)
        if section11:
            parsed_se = session.parse_side_effects_from_html(section11, ingredient)
            stats["side_effects_raw"] += len(parsed_se)
            se_rows.extend(parsed_se)

    ix_filtered, ix_filter_stats = filter_interactions(ix_rows)
    se_filtered, se_filter_stats = filter_side_effects(se_rows)
    ix_rows = dedupe_interactions(ix_filtered)
    se_rows = dedupe_side_effects(se_filtered)

    stats["interactions"] = len(ix_rows)
    stats["side_effects"] = len(se_rows)
    stats["filter_interactions"] = ix_filter_stats
    stats["filter_side_effects"] = se_filter_stats

    payload_base = {
        "generated_at": utc_now_iso(),
        "source": "live",
        "live_only": True,
        "reparse_from_raw": True,
    }
    save_json(
        STAGING_INTERACTIONS,
        {**payload_base, "stats": stats, "rows": ix_rows},
    )
    save_json(
        STAGING_SIDE_EFFECTS,
        {**payload_base, "stats": stats, "rows": se_rows},
    )

    validation = validate_all_staging()
    result: Dict[str, Any] = {
        "ok": validation["ok"],
        "stats": stats,
        "validation": {
            "interactions": validation["interactions"],
            "side_effects": validation["side_effects"],
        },
        "dry_run": dry_run,
    }
    if not validation["ok"]:
        result["errors"] = {
            "interactions": validation["interactions"]["errors"],
            "side_effects": validation["side_effects"]["errors"],
        }
        return result

    if dry_run:
        return result

    backup_dir = backup_csv_files()
    ix_merge = merge_interactions(validation["normalized"]["interactions"], live_replace=True)
    se_merge = merge_side_effects(validation["normalized"]["side_effects"], live_replace=True)
    result["backup_dir"] = str(backup_dir)
    result["merge"] = {"interactions": ix_merge, "side_effects": se_merge}
    write_fetch_log("reparse_from_raw", result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Reparse PMDA raw HTML into staging + CSV")
    parser.add_argument("--dry-run", action="store_true", help="staging/validate only, no CSV merge")
    args = parser.parse_args()
    result = reparse_all_raw(dry_run=args.dry_run)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if not result.get("ok"):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
