"""統合成分 live fetch: §10 + §11 を 1 detail GET で取得し両キューを更新。"""
from __future__ import annotations

from typing import Any, Dict, List, Tuple

from scripts.pmda.common import (
    STAGING_INTERACTIONS,
    STAGING_SIDE_EFFECTS,
    load_common_rx_medications,
    record_live_fetch_session,
    save_json,
    utc_now_iso,
)
from scripts.pmda.http_client import PmdaFetchAborted, PmdaLiveSession
from scripts.pmda.normalize import dedupe_interactions, dedupe_side_effects, normalize_interaction_row, normalize_side_effect_row
from scripts.pmda.raw_store import save_ingredient_raw
from scripts.pmda.queue import (
    mark_queue_done,
    mark_queue_failed,
    pop_queue_batch,
    restore_queue_pending,
)


def process_ingredient(
    session: PmdaLiveSession,
    ingredient: str,
    partners: List[str],
) -> Dict[str, Any]:
    """1 成分を fetch + parse。キュー更新は呼び出し側。"""
    result: Dict[str, Any] = {
        "ingredient": ingredient,
        "ix_rows": [],
        "se_rows": [],
        "status": "done",
        "reason": "",
        "no_data_ix": False,
        "no_data_se": False,
        "raw_saved": False,
    }
    try:
        section10, section11, raw_meta = session.fetch_ingredient_sections(ingredient)
    except PmdaFetchAborted as exc:
        result["status"] = "aborted"
        result["reason"] = str(exc)
        return result

    if session.stats.aborted:
        result["status"] = "aborted"
        result["reason"] = session.stats.abort_reason
        return result

    save_ingredient_raw(
        ingredient,
        detail_html=raw_meta.get("detail_html") or "",
        detail_fname=raw_meta.get("detail_fname") or "",
        result_list_html=raw_meta.get("result_list_html") or "",
        section10=section10,
        section11=section11,
        status="ok" if (section10 or section11) else "empty_section",
        reason="" if (section10 or section11) else "empty_section",
    )
    result["raw_saved"] = True

    if not section10 and not section11:
        result["status"] = "failed"
        result["reason"] = "empty_section"
        return result

    if section10:
        parsed_ix = session.parse_interactions_from_html(section10, ingredient, partners)
        result["ix_rows"] = parsed_ix
        result["no_data_ix"] = not parsed_ix
    else:
        result["no_data_ix"] = True

    if section11:
        parsed_se = session.parse_side_effects_from_html(section11, ingredient)
        result["se_rows"] = parsed_se
        result["no_data_se"] = not parsed_se
    else:
        result["no_data_se"] = True

    return result


def update_queues_for_ingredient(result: Dict[str, Any]) -> None:
    ingredient = result["ingredient"]
    status = result["status"]
    if status == "done":
        mark_queue_done("interactions", [ingredient])
        mark_queue_done("side_effects", [ingredient])
    elif status == "failed":
        reason = result.get("reason") or "failed"
        mark_queue_failed("interactions", ingredient, reason)
        mark_queue_failed("side_effects", ingredient, reason)


def write_staging_batch(
    ix_rows: List[Dict[str, Any]],
    se_rows: List[Dict[str, Any]],
    stats: Dict[str, Any],
) -> None:
    save_json(
        STAGING_INTERACTIONS,
        {
            "generated_at": utc_now_iso(),
            "source": "live",
            "stats": stats,
            "rows": dedupe_interactions([normalize_interaction_row(r) for r in ix_rows if normalize_interaction_row(r)]),
            "live_only": True,
        },
    )
    save_json(
        STAGING_SIDE_EFFECTS,
        {
            "generated_at": utc_now_iso(),
            "source": "live",
            "stats": stats,
            "rows": dedupe_side_effects([normalize_side_effect_row(r) for r in se_rows if normalize_side_effect_row(r)]),
            "live_only": True,
        },
    )


def merge_staging_to_csv() -> Dict[str, Any]:
    from scripts.pmda.merge_into_csv import merge_interactions, merge_side_effects
    from scripts.pmda.validate_pmda_import import validate_all_staging

    validation = validate_all_staging()
    if not validation["ok"]:
        return {"ok": False, "validation": validation}
    norm = validation["normalized"]
    return {
        "ok": True,
        "interactions": merge_interactions(norm["interactions"], live_replace=True),
        "side_effects": merge_side_effects(norm["side_effects"], live_replace=True),
    }
