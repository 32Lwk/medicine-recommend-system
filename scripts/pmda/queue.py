"""PMDA live fetch キュー・セッションガード・品名正規化。"""
from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from scripts.pmda.common import (
    MANIFEST_JSON,
    OTC_CSV,
    PRIORITY_INGREDIENTS,
    extract_otc_ingredients,
    load_json,
    load_manifest,
    normalize_text,
    product_key,
    read_csv_rows,
    save_json,
    write_live_fetch_log,
)
from scripts.pmda.normalize import normalize_otc_product_row

JST = timezone(timedelta(hours=9))
QUEUE_SOURCES = ("interactions", "side_effects", "otc")

# 剤形・容量除去（OTC 検索用）。「散」「末」単体は漢方名を壊すため含めない。
_DOSAGE_FORM_RE = re.compile(
    r"(錠剤|錠|カプセル|液|シロップ|顆粒|細粒|微粒|散剤|パップ|テープ|パッチ|ゲル|スプレー|"
    r"坐剤|軟膏|クリーム|ローション|内服液|内用|外用|浣腸|パステル)$"
)
_CAPACITY_RE = re.compile(r"(\d+\s*(錠|包|mL|ml|g|％|%|本|個|枚|袋|セット))+$")
_BRACKET_ANNOT_RE = re.compile(r"[<〈《\[（(「][^>〉》\]）)」]*[>〉》\]）)」]")
_SPACE_RE = re.compile(r"\s+")


def empty_queue_bucket() -> Dict[str, Any]:
    return {"pending": [], "done": [], "failed": {}}


def get_live_fetch_queue(manifest: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    manifest = manifest or load_manifest()
    queue = manifest.get("live_fetch_queue")
    if not isinstance(queue, dict):
        queue = {}
    for source in QUEUE_SOURCES:
        bucket = queue.get(source)
        if not isinstance(bucket, dict):
            queue[source] = empty_queue_bucket()
            continue
        bucket.setdefault("pending", [])
        bucket.setdefault("done", [])
        bucket.setdefault("failed", {})
    return queue


def save_live_fetch_queue(queue: Dict[str, Any]) -> None:
    manifest = load_manifest()
    manifest["live_fetch_queue"] = queue
    save_json(MANIFEST_JSON, manifest)


def _all_otc_product_keys() -> List[str]:
    keys: List[str] = []
    for row in read_csv_rows(OTC_CSV):
        norm = normalize_otc_product_row(row)
        if norm:
            keys.append(product_key(norm["製品名"], norm["メーカー名"]))
    return keys


def init_live_fetch_queue(
    sources: Optional[List[str]] = None,
    *,
    done_ingredients: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """pending/done/failed キューを (再)構築。既存 done は保持。"""
    sources = sources or list(QUEUE_SOURCES)
    queue = get_live_fetch_queue()
    all_ingredients = extract_otc_ingredients()
    default_done = set(normalize_text(x) for x in (done_ingredients or PRIORITY_INGREDIENTS))

    if "interactions" in sources:
        bucket = queue["interactions"]
        done = set(bucket.get("done") or []) | default_done
        failed = set((bucket.get("failed") or {}).keys())
        pending = [x for x in all_ingredients if x not in done and x not in failed]
        queue["interactions"] = {"pending": pending, "done": sorted(done), "failed": bucket.get("failed") or {}}

    if "side_effects" in sources:
        bucket = queue["side_effects"]
        done = set(bucket.get("done") or []) | default_done
        failed = set((bucket.get("failed") or {}).keys())
        pending = [x for x in all_ingredients if x not in done and x not in failed]
        queue["side_effects"] = {"pending": pending, "done": sorted(done), "failed": bucket.get("failed") or {}}

    if "otc" in sources:
        bucket = queue["otc"]
        all_keys = _all_otc_product_keys()
        done = set(bucket.get("done") or [])
        failed = set((bucket.get("failed") or {}).keys())
        pending = [k for k in all_keys if k not in done and k not in failed]
        queue["otc"] = {"pending": pending, "done": sorted(done), "failed": bucket.get("failed") or {}}

    save_live_fetch_queue(queue)
    return queue


def restore_queue_pending(source: str, items: List[str]) -> None:
    """abort 時: 未処理分を pending 先頭へ戻す。"""
    if not items:
        return
    queue = get_live_fetch_queue()
    bucket = queue[source]
    pending = list(bucket.get("pending") or [])
    for item in reversed(items):
        if item not in pending:
            pending.insert(0, item)
    bucket["pending"] = pending
    queue[source] = bucket
    save_live_fetch_queue(queue)


def pop_queue_batch(source: str, max_items: int = 30) -> List[str]:
    queue = get_live_fetch_queue()
    bucket = queue.get(source) or empty_queue_bucket()
    pending: List[str] = list(bucket.get("pending") or [])
    batch = pending[:max_items]
    bucket["pending"] = pending[len(batch) :]
    queue[source] = bucket
    save_live_fetch_queue(queue)
    return batch


def mark_queue_done(source: str, items: List[str]) -> None:
    if not items:
        return
    queue = get_live_fetch_queue()
    bucket = queue[source]
    done = set(bucket.get("done") or [])
    done.update(items)
    bucket["done"] = sorted(done)
    failed = dict(bucket.get("failed") or {})
    item_set = set(items)
    for item in items:
        failed.pop(item, None)
    bucket["failed"] = failed
    bucket["pending"] = [x for x in (bucket.get("pending") or []) if x not in item_set]
    queue[source] = bucket
    save_live_fetch_queue(queue)


def mark_queue_failed(source: str, item: str, reason: str) -> None:
    queue = get_live_fetch_queue()
    bucket = queue[source]
    failed = dict(bucket.get("failed") or {})
    failed[item] = {"reason": reason, "at": datetime.now(timezone.utc).replace(microsecond=0).isoformat()}
    bucket["failed"] = failed
    pending = [x for x in (bucket.get("pending") or []) if x != item]
    bucket["pending"] = pending
    queue[source] = bucket
    save_live_fetch_queue(queue)


def requeue_failed(source: str, item: str) -> None:
    queue = get_live_fetch_queue()
    bucket = queue[source]
    failed = dict(bucket.get("failed") or {})
    if item in failed:
        del failed[item]
    pending = list(bucket.get("pending") or [])
    if item not in pending:
        pending.insert(0, item)
    bucket["pending"] = pending
    bucket["failed"] = failed
    queue[source] = bucket
    save_live_fetch_queue(queue)


def migrate_failed_to_done(source: str, *, reason: str) -> Dict[str, Any]:
    """failed のうち指定 reason を done へ移動（no_interaction_rows 修復用）。"""
    queue = get_live_fetch_queue()
    bucket = queue[source]
    failed = dict(bucket.get("failed") or {})
    done = set(bucket.get("done") or [])
    migrated: List[str] = []
    for item, meta in list(failed.items()):
        if (meta.get("reason") or "") == reason:
            done.add(item)
            del failed[item]
            migrated.append(item)
    bucket["done"] = sorted(done)
    bucket["failed"] = failed
    queue[source] = bucket
    save_live_fetch_queue(queue)
    return {"source": source, "reason": reason, "migrated": migrated, "count": len(migrated)}


def _today_jst() -> str:
    return now_jst().strftime("%Y-%m-%d")


def get_sessions_today() -> Dict[str, Any]:
    manifest = load_manifest()
    live_meta = manifest.get("live_fetch") or {}
    sessions = dict(live_meta.get("sessions_today") or {})
    if sessions.get("date") != _today_jst():
        return {"date": _today_jst(), "count": 0}
    return {"date": _today_jst(), "count": int(sessions.get("count") or 0)}


def record_session_today() -> Dict[str, Any]:
    manifest = load_manifest()
    live_meta = dict(manifest.get("live_fetch") or {})
    sessions = get_sessions_today()
    sessions["count"] += 1
    live_meta["sessions_today"] = sessions
    manifest["live_fetch"] = live_meta
    save_json(MANIFEST_JSON, manifest)
    return sessions


def check_daily_session_limit(*, max_sessions: int = 2, force: bool = False, ignore_daily_limit: bool = False) -> Tuple[bool, str]:
    if force or ignore_daily_limit:
        return True, ""
    sessions = get_sessions_today()
    if sessions["count"] >= max_sessions:
        return False, f"daily session limit reached ({sessions['count']}/{max_sessions} on {sessions['date']} JST)"
    return True, ""


def queue_stats(source: str) -> Dict[str, Any]:
    queue = get_live_fetch_queue()
    bucket = queue.get(source) or empty_queue_bucket()
    pending = len(bucket.get("pending") or [])
    done = len(bucket.get("done") or [])
    failed = len(bucket.get("failed") or {})
    total = pending + done + failed
    return {
        "source": source,
        "pending": pending,
        "done": done,
        "failed": failed,
        "total": total,
        "pct_done": round(100.0 * done / total, 1) if total else 0.0,
    }


def estimate_sessions_remaining(source: str, items_per_session: int) -> int:
    stats = queue_stats(source)
    pending = stats["pending"]
    if pending <= 0:
        return 0
    return (pending + items_per_session - 1) // items_per_session


def now_jst() -> datetime:
    return datetime.now(JST)


def check_live_fetch_time_window(*, allow_daytime: bool = False, force: bool = False) -> Tuple[bool, str]:
    if force or allow_daytime:
        return True, ""
    hour = now_jst().hour
    if hour >= 22 or hour < 6:
        return True, ""
    return False, f"outside JST live window (now {now_jst():%H:%M} JST, allowed 22:00-06:00; use --allow-daytime)"


def check_live_fetch_session_gap(*, min_hours: float = 4.0, force: bool = False, ignore_session_gap: bool = False) -> Tuple[bool, str]:
    if force or ignore_session_gap:
        return True, ""
    manifest = load_manifest()
    live_meta = manifest.get("live_fetch") or {}
    if live_meta.get("last_abort_at"):
        return check_live_fetch_cooldown_from_manifest(live_meta, cooldown_hours=24.0)
    last_end = live_meta.get("last_session_end_at")
    if not last_end:
        return True, ""
    try:
        last = datetime.fromisoformat(str(last_end).replace("Z", "+00:00"))
    except ValueError:
        return True, ""
    now = datetime.now(timezone.utc)
    if last.tzinfo is None:
        last = last.replace(tzinfo=timezone.utc)
    elapsed_h = (now - last).total_seconds() / 3600.0
    if elapsed_h < min_hours:
        return False, f"session gap too short ({elapsed_h:.1f}h < {min_hours}h)"
    return True, ""


def check_live_fetch_cooldown_from_manifest(
    live_meta: Dict[str, Any], *, cooldown_hours: float
) -> Tuple[bool, str]:
    last_abort = live_meta.get("last_abort_at")
    if not last_abort:
        return True, ""
    try:
        last = datetime.fromisoformat(str(last_abort).replace("Z", "+00:00"))
    except ValueError:
        return True, ""
    now = datetime.now(timezone.utc)
    if last.tzinfo is None:
        last = last.replace(tzinfo=timezone.utc)
    elapsed_h = (now - last).total_seconds() / 3600.0
    if elapsed_h < cooldown_hours:
        reason = str(live_meta.get("last_abort_reason") or "aborted")
        return False, f"abort cooldown ({elapsed_h:.1f}h < {cooldown_hours}h): {reason}"
    return True, ""


def check_live_fetch_guards(
    *,
    allow_daytime: bool = False,
    force: bool = False,
    ignore_session_gap: bool = False,
    ignore_daily_limit: bool = False,
) -> Tuple[bool, str]:
    ok, reason = check_live_fetch_time_window(allow_daytime=allow_daytime, force=force)
    if not ok:
        return ok, reason
    ok, reason = check_live_fetch_session_gap(force=force, ignore_session_gap=ignore_session_gap)
    if not ok:
        return ok, reason
    ok, reason = check_daily_session_limit(force=force, ignore_daily_limit=ignore_daily_limit)
    if not ok:
        return ok, reason
    manifest = load_manifest()
    live_meta = manifest.get("live_fetch") or {}
    if live_meta.get("last_abort_at"):
        return check_live_fetch_cooldown_from_manifest(live_meta, cooldown_hours=24.0)
    return True, ""


def record_session_end(*, aborted: bool = False, stats: Optional[Dict[str, Any]] = None) -> None:
    manifest = load_manifest()
    live_meta = dict(manifest.get("live_fetch") or {})
    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    live_meta["last_session_end_at"] = now
    if stats:
        live_meta["last_stats"] = stats
    if not aborted:
        live_meta.pop("last_abort_at", None)
        live_meta.pop("last_abort_reason", None)
    manifest["live_fetch"] = live_meta
    save_json(MANIFEST_JSON, manifest)


def normalize_product_search_name(product_name: str) -> str:
    """OTC 検索用: NFKC + 括弧注釈/剤形/容量除去。"""
    text = normalize_text(product_name)
    text = _BRACKET_ANNOT_RE.sub("", text)
    text = _SPACE_RE.sub("", text)
    text = _CAPACITY_RE.sub("", text).strip()
    text = _DOSAGE_FORM_RE.sub("", text).strip()
    return text


def compact_product_name(product_name: str) -> str:
    """マッチ比較用: 空白除去・括弧種別統一・注釈除去。"""
    text = normalize_text(product_name)
    text = text.replace("<", "〈").replace(">", "〉").replace("[", "〈").replace("]", "〉")
    text = text.replace("《", "〈").replace("》", "〉").replace("「", "〈").replace("」", "〉")
    text = _BRACKET_ANNOT_RE.sub("", text)
    text = _SPACE_RE.sub("", text)
    return text


def product_search_name_variants(product_name: str) -> List[str]:
    """検索フォールバック用の候補（先頭ほど具体的）。"""
    variants: List[str] = []

    def _add(value: str) -> None:
        text = normalize_text(value)
        if text and text not in variants:
            variants.append(text)

    raw = normalize_text(product_name)
    _add(raw)
    no_br = _BRACKET_ANNOT_RE.sub("", raw)
    _add(no_br)
    _add(_SPACE_RE.sub("", no_br))
    _add(normalize_product_search_name(product_name))
    _add(normalize_product_search_name(no_br))

    # 末尾の規格コード（G / S / 10 / 40 等）を段階的に落とす
    core = _SPACE_RE.sub("", no_br)
    for _ in range(2):
        nxt = re.sub(r"[\d０-９]+$", "", core)
        nxt = re.sub(r"[A-Za-z]+$", "", nxt)
        # 浣腸+容量 → 浣腸 を残す中間形
        m_enema = re.match(r"(.+浣腸)\d+$", core)
        if m_enema:
            _add(m_enema.group(1))
        nxt = _DOSAGE_FORM_RE.sub("", nxt).strip()
        if nxt == core:
            break
        core = nxt
        _add(core)
        _add(normalize_product_search_name(core))

    return variants[:5]


def product_key_to_row(key: str) -> Dict[str, str]:
    if "||" not in key:
        return {"製品名": key, "メーカー名": ""}
    name, mfr = key.split("||", 1)
    return {"製品名": name, "メーカー名": mfr}


def append_live_batch_log(payload: Dict[str, Any]) -> None:
    stamp = datetime.now().strftime("%Y%m%d")
    write_live_fetch_log({"batch": payload, "logged_at": datetime.now(timezone.utc).isoformat()})


def sync_side_effects_queue_from_interactions() -> Dict[str, Any]:
    """interactions done を side_effects に反映（統合 fetch 前の整合）。"""
    queue = get_live_fetch_queue()
    ix_done = set(queue["interactions"].get("done") or [])
    se = queue["side_effects"]
    se_done = set(se.get("done") or []) | ix_done
    se_failed = dict(se.get("failed") or {})
    se_pending = [x for x in (se.get("pending") or []) if x not in se_done and x not in se_failed]
    se["done"] = sorted(se_done)
    se["pending"] = se_pending
    queue["side_effects"] = se
    save_live_fetch_queue(queue)
    return {"interactions_done": len(ix_done), "side_effects_done": len(se_done), "side_effects_pending": len(se_pending)}


def requeue_done_missing_raw(*, include_failed: bool = False) -> Dict[str, Any]:
    """raw 未保存の done（必要なら failed）を pending 先頭へ戻す。"""
    from scripts.pmda.raw_store import has_raw

    queue = get_live_fetch_queue()
    ix = queue["interactions"]
    done = list(ix.get("done") or [])
    pending = list(ix.get("pending") or [])
    failed = dict(ix.get("failed") or {})

    requeued: List[str] = []
    kept_done: List[str] = []
    for item in done:
        if not has_raw(item):
            requeued.append(item)
        else:
            kept_done.append(item)

    failed_requeued: List[str] = []
    if include_failed:
        for item, meta in list(failed.items()):
            if has_raw(item):
                continue
            if (meta.get("reason") or "") != "empty_section":
                continue
            failed_requeued.append(item)
            del failed[item]

    requeued_set = set(requeued) | set(failed_requeued)
    new_pending = requeued + failed_requeued + [x for x in pending if x not in requeued_set]

    ix["done"] = sorted(kept_done)
    ix["pending"] = new_pending
    ix["failed"] = failed
    queue["interactions"] = ix

    se = queue["side_effects"]
    se_failed = dict(se.get("failed") or {})
    for item in requeued_set:
        se_failed.pop(item, None)
    se["done"] = sorted(kept_done)
    se["pending"] = [x for x in new_pending if x not in se_failed]
    se["failed"] = se_failed
    queue["side_effects"] = se

    save_live_fetch_queue(queue)
    return {
        "requeued_from_done": requeued,
        "requeued_from_failed": failed_requeued,
        "requeued_total": len(requeued_set),
        "kept_done": len(kept_done),
        "pending_total": len(new_pending),
    }


def write_local_ingredients_progress(payload: Dict[str, Any]) -> None:
    from scripts.pmda.common import LOG_ANALYSIS_DIR

    stamp = datetime.now().strftime("%Y%m%d")
    path = LOG_ANALYSIS_DIR / f"pmda_local_ingredients_{stamp}.json"
    existing = load_json(path, {"runs": []}) if path.is_file() else {"runs": []}
    if not isinstance(existing, dict):
        existing = {"runs": []}
    existing.setdefault("runs", []).append(
        {"logged_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(), **payload}
    )
    save_json(path, existing)


def write_cloud_otc_progress(payload: Dict[str, Any]) -> None:
    from scripts.pmda.common import LOG_ANALYSIS_DIR

    stamp = datetime.now().strftime("%Y%m%d")
    path = LOG_ANALYSIS_DIR / f"pmda_cloud_otc_{stamp}.json"
    existing = load_json(path, {"runs": []}) if path.is_file() else {"runs": []}
    if not isinstance(existing, dict):
        existing = {"runs": []}
    existing.setdefault("runs", []).append(
        {"logged_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(), **payload}
    )
    save_json(path, existing)
