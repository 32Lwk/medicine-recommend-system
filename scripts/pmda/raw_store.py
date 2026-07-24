"""PMDA iyakuSearch 取得 HTML の永続化（再パース用 raw 正本）。"""
from __future__ import annotations

import hashlib
import json
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

from scripts.pmda.common import PMDA_DIR, normalize_text, utc_now_iso

RAW_DIR = PMDA_DIR / "raw" / "ingredients"
RAW_INDEX = PMDA_DIR / "raw" / "index.json"


def _ingredient_key(ingredient: str) -> str:
    return normalize_text(ingredient)


def raw_file_path(ingredient: str) -> Path:
    key = _ingredient_key(ingredient)
    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()[:20]
    return RAW_DIR / f"{digest}.json"


def _load_index() -> Dict[str, str]:
    if not RAW_INDEX.is_file():
        return {}
    try:
        data = json.loads(RAW_INDEX.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    if isinstance(data, dict) and isinstance(data.get("by_ingredient"), dict):
        return {normalize_text(k): str(v) for k, v in data["by_ingredient"].items()}
    return {}


def _save_index(by_ingredient: Dict[str, str]) -> None:
    RAW_INDEX.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "updated_at": utc_now_iso(),
        "count": len(by_ingredient),
        "by_ingredient": dict(sorted(by_ingredient.items())),
    }
    RAW_INDEX.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _update_index(ingredient: str, path: Path) -> None:
    idx = _load_index()
    idx[_ingredient_key(ingredient)] = path.name
    _save_index(idx)


def has_raw(ingredient: str) -> bool:
    path = raw_file_path(ingredient)
    if not path.is_file():
        return False
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return False
    return _ingredient_key(str(data.get("ingredient") or "")) == _ingredient_key(ingredient)


def load_raw(ingredient: str) -> Optional[Dict[str, Any]]:
    path = raw_file_path(ingredient)
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def save_ingredient_raw(
    ingredient: str,
    *,
    detail_html: str = "",
    detail_fname: str = "",
    result_list_html: str = "",
    section10: str = "",
    section11: str = "",
    status: str = "ok",
    reason: str = "",
) -> Path:
    """成分ごとの fetch 結果を atomic write。"""
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    path = raw_file_path(ingredient)
    payload: Dict[str, Any] = {
        "ingredient": _ingredient_key(ingredient),
        "fetched_at": utc_now_iso(),
        "status": status,
        "reason": reason,
        "detail_fname": detail_fname or "",
        "detail_html": detail_html or "",
        "result_list_html": result_list_html or "",
        "section10_text": section10 or "",
        "section11_text": section11 or "",
    }
    fd, tmp_name = tempfile.mkstemp(dir=RAW_DIR, suffix=".tmp")
    tmp_path = Path(tmp_name)
    try:
        with open(fd, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
            f.write("\n")
        tmp_path.replace(path)
    finally:
        if tmp_path.is_file():
            tmp_path.unlink(missing_ok=True)
    _update_index(ingredient, path)
    return path


def list_missing_raw(ingredients: List[str]) -> List[str]:
    return [x for x in ingredients if not has_raw(x)]


def raw_stats() -> Dict[str, int]:
    idx = _load_index()
    on_disk = len(list(RAW_DIR.glob("*.json"))) if RAW_DIR.is_dir() else 0
    return {"indexed": len(idx), "files": on_disk}
