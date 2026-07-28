"""PMDA 成分 fetch — Cursor Cloud Agent 並列シャード（manifest 競合回避）。"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from scripts.pmda.common import save_json, utc_now_iso
from scripts.pmda.queue import (
    get_live_fetch_queue,
    init_live_fetch_queue,
    save_live_fetch_queue,
)

SHARD_DIR = Path(__file__).resolve().parents[2] / "data" / "pmda" / "shards"


def ingredient_shard(ingredient: str, shard_count: int) -> int:
    """成分名を安定ハッシュでシャード ID に割当（0 .. shard_count-1）。"""
    if shard_count < 1:
        return 0
    digest = hashlib.sha256(ingredient.encode("utf-8")).hexdigest()
    return int(digest[:8], 16) % shard_count


def _shard_path(shard_id: int, shard_count: int) -> Path:
    return SHARD_DIR / f"ingredient_shard_{shard_id}_of_{shard_count}.json"


def _empty_shard(shard_id: int, shard_count: int) -> Dict[str, Any]:
    return {
        "shard_id": shard_id,
        "shard_count": shard_count,
        "generated_at": utc_now_iso(),
        "pending": [],
        "done": [],
        "failed": {},
    }


def load_shard(shard_id: int, shard_count: int) -> Dict[str, Any]:
    path = _shard_path(shard_id, shard_count)
    if not path.is_file():
        return _empty_shard(shard_id, shard_count)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return _empty_shard(shard_id, shard_count)
    data.setdefault("pending", [])
    data.setdefault("done", [])
    data.setdefault("failed", {})
    return data


def save_shard(data: Dict[str, Any]) -> Path:
    SHARD_DIR.mkdir(parents=True, exist_ok=True)
    shard_id = int(data["shard_id"])
    shard_count = int(data["shard_count"])
    path = _shard_path(shard_id, shard_count)
    data["updated_at"] = utc_now_iso()
    save_json(path, data)
    return path


def prepare_ingredient_shards(
    shard_count: int,
    *,
    requeue_failed: bool = False,
) -> Dict[str, Any]:
    """グローバルキューから pending をシャード分割。各 Cloud Agent が独立ファイルを更新。"""
    if shard_count < 1:
        raise ValueError("shard_count must be >= 1")

    init_live_fetch_queue(["interactions", "side_effects"])
    queue = get_live_fetch_queue()
    if requeue_failed:
        bucket = queue["interactions"]
        failed = dict(bucket.get("failed") or {})
        pending = list(bucket.get("pending") or [])
        for name in failed.keys():
            if name not in pending:
                pending.append(name)
        bucket["failed"] = {}
        bucket["pending"] = pending
        queue["interactions"] = bucket
        se_bucket = queue["side_effects"]
        se_failed = dict(se_bucket.get("failed") or {})
        se_pending = list(se_bucket.get("pending") or [])
        for name in se_failed.keys():
            if name not in se_pending:
                se_pending.append(name)
        se_bucket["failed"] = {}
        se_bucket["pending"] = se_pending
        queue["side_effects"] = se_bucket
        save_live_fetch_queue(queue)

    pending: List[str] = list(queue["interactions"].get("pending") or [])
    shards: List[Dict[str, Any]] = [
        _empty_shard(i, shard_count) for i in range(shard_count)
    ]
    for name in pending:
        sid = ingredient_shard(name, shard_count)
        shards[sid]["pending"].append(name)

    paths: List[str] = []
    counts: List[int] = []
    for shard in shards:
        shard["pending"] = sorted(set(shard["pending"]))
        paths.append(str(save_shard(shard)))
        counts.append(len(shard["pending"]))

    # グローバル pending をシャードに移したので空にする（done/failed は保持）
    bucket = queue["interactions"]
    bucket["pending"] = []
    queue["interactions"] = bucket
    se_bucket = queue["side_effects"]
    se_bucket["pending"] = []
    queue["side_effects"] = se_bucket
    save_live_fetch_queue(queue)

    return {
        "shard_count": shard_count,
        "total_pending": len(pending),
        "per_shard": counts,
        "paths": paths,
        "requeue_failed": requeue_failed,
    }


def pop_shard_batch(shard_id: int, shard_count: int, *, max_items: int = 1) -> List[str]:
    data = load_shard(shard_id, shard_count)
    pending: List[str] = list(data.get("pending") or [])
    batch = pending[:max_items]
    data["pending"] = pending[len(batch) :]
    save_shard(data)
    return batch


def mark_shard_done(shard_id: int, shard_count: int, items: List[str]) -> None:
    if not items:
        return
    data = load_shard(shard_id, shard_count)
    done = set(data.get("done") or [])
    done.update(items)
    data["done"] = sorted(done)
    failed = dict(data.get("failed") or {})
    for item in items:
        failed.pop(item, None)
    data["failed"] = failed
    data["pending"] = [x for x in (data.get("pending") or []) if x not in set(items)]
    save_shard(data)


def mark_shard_failed(shard_id: int, shard_count: int, item: str, reason: str) -> None:
    data = load_shard(shard_id, shard_count)
    failed = dict(data.get("failed") or {})
    failed[item] = reason
    data["failed"] = failed
    data["pending"] = [x for x in (data.get("pending") or []) if x != item]
    if item not in (data.get("done") or []):
        done = set(data.get("done") or [])
        done.discard(item)
        data["done"] = sorted(done)
    save_shard(data)


def shard_stats(shard_id: int, shard_count: int) -> Dict[str, Any]:
    data = load_shard(shard_id, shard_count)
    pending = len(data.get("pending") or [])
    done = len(data.get("done") or [])
    failed = len(data.get("failed") or {})
    total = pending + done + failed
    return {
        "shard_id": shard_id,
        "shard_count": shard_count,
        "pending": pending,
        "done": done,
        "failed": failed,
        "total": total,
        "pct_done": round(100.0 * done / total, 1) if total else 0.0,
    }


def merge_shards_to_manifest(shard_count: int) -> Dict[str, Any]:
    """全シャードの done/failed をグローバル manifest に統合（コーディネータ 1 回）。"""
    queue = get_live_fetch_queue()
    ix_done = set(queue["interactions"].get("done") or [])
    se_done = set(queue["side_effects"].get("done") or [])
    ix_failed = dict(queue["interactions"].get("failed") or {})
    se_failed = dict(queue["side_effects"].get("failed") or {})

    for sid in range(shard_count):
        data = load_shard(sid, shard_count)
        ix_done.update(data.get("done") or [])
        se_done.update(data.get("done") or [])
        for name, reason in (data.get("failed") or {}).items():
            ix_failed[name] = reason
            se_failed[name] = reason

    queue["interactions"]["done"] = sorted(ix_done)
    queue["interactions"]["failed"] = ix_failed
    queue["interactions"]["pending"] = []
    queue["side_effects"]["done"] = sorted(se_done)
    queue["side_effects"]["failed"] = se_failed
    queue["side_effects"]["pending"] = []
    save_live_fetch_queue(queue)

    return {
        "shard_count": shard_count,
        "interactions_done": len(ix_done),
        "interactions_failed": len(ix_failed),
        "side_effects_done": len(se_done),
        "side_effects_failed": len(se_failed),
    }
