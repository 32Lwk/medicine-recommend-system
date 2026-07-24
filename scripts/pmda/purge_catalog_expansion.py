"""catalog expansion 行を PMDA live 行存在時に削除。"""
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
    INTERACTIONS_CSV,
    SIDE_EFFECTS_CSV,
    backup_csv_files,
    load_manifest,
    normalize_text,
    read_csv_rows,
    update_manifest,
    write_csv_rows,
)
from scripts.pmda.http_client import PMDA_LIVE_SOURCE_LABELS  # noqa: E402
from scripts.pmda.merge_into_csv import INTERACTION_FIELDS, SIDE_EFFECT_FIELDS  # noqa: E402
from scripts.pmda.normalize import (  # noqa: E402
    normalize_interaction_row,
    normalize_side_effect_row,
    pair_key,
)
from scripts.pmda.queue import QUEUE_SOURCES, get_live_fetch_queue  # noqa: E402

EXPANSION_MARKERS = (
    "review recommended",
    "catalog expansion",
    "catalog pair expansion",
    "catalog ingredient expansion",
)


def _is_expansion_source(source: str) -> bool:
    text = (source or "").lower()
    return any(marker in text for marker in EXPANSION_MARKERS)


def _queue_complete() -> bool:
    queue = get_live_fetch_queue()
    for source in QUEUE_SOURCES:
        bucket = queue.get(source) or {}
        pending = bucket.get("pending") or []
        if pending:
            return False
    return True


def purge_interactions(*, dry_run: bool = False) -> Dict[str, Any]:
    rows = read_csv_rows(INTERACTIONS_CSV)
    pmda_keys: Set[str] = set()
    kept: List[Dict[str, str]] = []
    removed = 0
    for row in rows:
        norm = normalize_interaction_row(row)
        if not norm:
            continue
        key = pair_key(norm["成分A"], norm["成分B"])
        if norm.get("出典") in PMDA_LIVE_SOURCE_LABELS:
            pmda_keys.add(key)
    for row in rows:
        norm = normalize_interaction_row(row)
        if not norm:
            kept.append(row)
            continue
        key = pair_key(norm["成分A"], norm["成分B"])
        if key in pmda_keys and _is_expansion_source(norm.get("出典", "")):
            removed += 1
            continue
        kept.append(norm)
    if not dry_run:
        count = write_csv_rows(INTERACTIONS_CSV, INTERACTION_FIELDS, kept)
        update_manifest(medicine_interactions={"row_count": count, "pair_policy": "otc_plus_common_rx"})
    return {"before": len(rows), "after": len(rows) - removed, "removed": removed}


def purge_side_effects(*, dry_run: bool = False) -> Dict[str, Any]:
    rows = read_csv_rows(SIDE_EFFECTS_CSV)
    pmda_ingredients: Set[str] = set()
    kept: List[Dict[str, str]] = []
    removed = 0
    for row in rows:
        norm = normalize_side_effect_row(row)
        if not norm:
            continue
        if norm.get("出典") in PMDA_LIVE_SOURCE_LABELS:
            pmda_ingredients.add(normalize_text(norm["成分名"]))
    for row in rows:
        norm = normalize_side_effect_row(row)
        if not norm:
            kept.append(row)
            continue
        ing_key = normalize_text(norm["成分名"])
        if ing_key in pmda_ingredients and _is_expansion_source(norm.get("出典", "")):
            removed += 1
            continue
        kept.append(norm)
    if not dry_run:
        count = write_csv_rows(SIDE_EFFECTS_CSV, SIDE_EFFECT_FIELDS, kept)
        update_manifest(medicine_side_effects={"row_count": count})
    return {"before": len(rows), "after": len(rows) - removed, "removed": removed}


def run_purge(*, dry_run: bool = False, force: bool = False) -> Dict[str, Any]:
    if not force and not _queue_complete():
        manifest = load_manifest()
        queue = manifest.get("live_fetch_queue") or {}
        pending_counts = {s: len((queue.get(s) or {}).get("pending") or []) for s in QUEUE_SOURCES}
        return {
            "ok": False,
            "reason": "live fetch queue not complete",
            "pending": pending_counts,
        }
    backup = None if dry_run else str(backup_csv_files())
    ix = purge_interactions(dry_run=dry_run)
    se = purge_side_effects(dry_run=dry_run)
    return {
        "ok": True,
        "dry_run": dry_run,
        "backup_dir": backup,
        "interactions": ix,
        "side_effects": se,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Purge catalog expansion rows superseded by PMDA live data")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force", action="store_true", help="Allow purge before queue complete (tests only)")
    args = parser.parse_args()
    result = run_purge(dry_run=args.dry_run, force=args.force)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
