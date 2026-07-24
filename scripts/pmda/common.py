"""PMDA import 共通ユーティリティ（パス・バックアップ・manifest・成分抽出）。"""
from __future__ import annotations

import csv
import json
import re
import shutil
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data"
PMDA_DIR = DATA_DIR / "pmda"
STAGING_DIR = PMDA_DIR / "staging"
BACKUP_DIR = PMDA_DIR / "backups"
LOG_ANALYSIS_DIR = ROOT / "log" / "analysis"

OTC_CSV = DATA_DIR / "otc_medicine_data.csv"
INTERACTIONS_CSV = DATA_DIR / "medicine_interactions.csv"
SIDE_EFFECTS_CSV = DATA_DIR / "medicine_side_effects.csv"
INGREDIENT_DICT_JSON = DATA_DIR / "ingredient_dictionary.json"
COMMON_RX_JSON = PMDA_DIR / "common_rx_medications.json"
OTC_INGREDIENTS_JSON = PMDA_DIR / "otc_ingredients.json"
MANIFEST_JSON = PMDA_DIR / "manifest.json"

STAGING_INTERACTIONS = STAGING_DIR / "interactions.json"
STAGING_SIDE_EFFECTS = STAGING_DIR / "side_effects.json"
STAGING_OTC = STAGING_DIR / "otc_products.json"
RAW_INGREDIENTS_DIR = PMDA_DIR / "raw" / "ingredients"

USER_AGENT = "medicine-recommend-pmda-import/1.0 (research; +https://github.com/)"

PRIORITY_INGREDIENTS = [
    "ロキソプロフェン",
    "イブプロフェン",
    "アスピリン",
    "アセトアミノフェン",
    "ジクロフェナク",
    "メフェナム酸",
    "ワーファリン",
    "リチウム",
]


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def normalize_text(text: str) -> str:
    return unicodedata.normalize("NFKC", (text or "").strip())


def load_json(path: Path, default: Any = None) -> Any:
    if not path.is_file():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def ensure_pmda_dirs() -> None:
    STAGING_DIR.mkdir(parents=True, exist_ok=True)
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    RAW_INGREDIENTS_DIR.mkdir(parents=True, exist_ok=True)
    LOG_ANALYSIS_DIR.mkdir(parents=True, exist_ok=True)


def backup_csv_files(tag: Optional[str] = None) -> Path:
    """import 前に data/*.csv を退避。"""
    ensure_pmda_dirs()
    stamp = tag or datetime.now().strftime("%Y%m%d")
    dest = BACKUP_DIR / stamp
    dest.mkdir(parents=True, exist_ok=True)
    for name in (
        "otc_medicine_data.csv",
        "medicine_interactions.csv",
        "medicine_side_effects.csv",
        "ingredient_dictionary.json",
    ):
        src = DATA_DIR / name
        if src.is_file():
            shutil.copy2(src, dest / name)
    return dest


def load_manifest() -> Dict[str, Any]:
    default = {
        "otc_medicine_data": {"row_count": 0, "last_import": None, "source": "PMDA OTC Search"},
        "medicine_interactions": {
            "row_count": 0,
            "last_import": None,
            "pair_policy": "otc_plus_common_rx",
        },
        "medicine_side_effects": {"row_count": 0, "last_import": None},
    }
    existing = load_json(MANIFEST_JSON, default)
    if isinstance(existing, dict):
        for key, val in default.items():
            existing.setdefault(key, val)
        return existing
    return default


def update_manifest(**sections: Dict[str, Any]) -> Dict[str, Any]:
    manifest = load_manifest()
    preserved_queue = manifest.get("live_fetch_queue")
    preserved_live_fetch = manifest.get("live_fetch")
    now = utc_now_iso()
    for key, meta in sections.items():
        entry = dict(manifest.get(key) or {})
        entry.update(meta)
        entry["last_import"] = now
        manifest[key] = entry
    if preserved_queue is not None:
        manifest["live_fetch_queue"] = preserved_queue
    if preserved_live_fetch is not None:
        manifest["live_fetch"] = preserved_live_fetch
    save_json(MANIFEST_JSON, manifest)
    return manifest


def split_ingredients(raw: str) -> List[str]:
    """OTC CSV の成分列を個別成分名に分割。"""
    text = normalize_text(raw)
    if not text:
        return []
    parts = re.split(r"[\n\r、,/／・]+", text)
    out: List[str] = []
    seen: Set[str] = set()
    for part in parts:
        name = normalize_text(part)
        if not name or len(name) < 2:
            continue
        if name in seen:
            continue
        seen.add(name)
        out.append(name)
    return out


def extract_otc_ingredients(limit: Optional[int] = None) -> List[str]:
    """otc_medicine_data.csv からユニーク成分一覧を生成。"""
    seen: Set[str] = set()
    ordered: List[str] = []
    with OTC_CSV.open(encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            for ing in split_ingredients(row.get("成分", "")):
                if ing not in seen:
                    seen.add(ing)
                    ordered.append(ing)
                    if limit and len(ordered) >= limit:
                        return ordered
    return ordered


def write_otc_ingredients_json(ingredients: Optional[List[str]] = None) -> Path:
    items = ingredients if ingredients is not None else extract_otc_ingredients()
    payload = {
        "generated_at": utc_now_iso(),
        "count": len(items),
        "ingredients": items,
    }
    save_json(OTC_INGREDIENTS_JSON, payload)
    return OTC_INGREDIENTS_JSON


def load_common_rx_medications() -> List[str]:
    data = load_json(COMMON_RX_JSON, [])
    if isinstance(data, list):
        return [normalize_text(x) for x in data if normalize_text(x)]
    return []


def product_key(product_name: str, manufacturer: str) -> str:
    return f"{normalize_text(product_name)}||{normalize_text(manufacturer)}"


def read_csv_rows(path: Path) -> List[Dict[str, str]]:
    if not path.is_file():
        return []
    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def write_csv_rows(path: Path, fieldnames: List[str], rows: Iterable[Dict[str, str]]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in fieldnames})
            count += 1
    return count


def write_fetch_log(name: str, payload: Dict[str, Any]) -> Path:
    ensure_pmda_dirs()
    stamp = datetime.now().strftime("%Y%m%d")
    path = LOG_ANALYSIS_DIR / f"pmda_{name}_{stamp}.json"
    existing = load_json(path, {})
    if not isinstance(existing, dict):
        existing = {}
    existing.setdefault("runs", []).append(payload)
    save_json(path, existing)
    return path


def write_live_fetch_log(payload: Dict[str, Any]) -> Path:
    ensure_pmda_dirs()
    stamp = datetime.now().strftime("%Y%m%d")
    path = LOG_ANALYSIS_DIR / f"pmda_live_fetch_{stamp}.json"
    existing = load_json(path, {})
    if not isinstance(existing, dict):
        existing = {"runs": []}
    existing.setdefault("runs", []).append(payload)
    save_json(path, existing)
    return path


def check_live_fetch_cooldown(*, cooldown_hours: float = 24.0) -> Tuple[bool, str]:
    """前回 abort から cooldown_hours 未満なら live fetch 禁止。"""
    manifest = load_manifest()
    live_meta = manifest.get("live_fetch") or {}
    if not live_meta.get("last_abort_at"):
        return True, ""
    try:
        last = datetime.fromisoformat(str(live_meta["last_abort_at"]).replace("Z", "+00:00"))
    except ValueError:
        return True, ""
    now = datetime.now(timezone.utc)
    if last.tzinfo is None:
        last = last.replace(tzinfo=timezone.utc)
    elapsed_h = (now - last).total_seconds() / 3600.0
    if elapsed_h < cooldown_hours:
        reason = str(live_meta.get("last_abort_reason") or "unknown")
        return False, f"cooldown active ({elapsed_h:.1f}h < {cooldown_hours}h): {reason}"
    return True, ""


def record_live_fetch_session(
    *,
    stats: Dict[str, Any],
    aborted: bool = False,
    abort_reason: str = "",
) -> None:
    manifest = load_manifest()
    preserved_queue = manifest.get("live_fetch_queue")
    now = utc_now_iso()
    live_meta = dict(manifest.get("live_fetch") or {})
    live_meta["last_live_fetch_at"] = now
    live_meta["last_session_end_at"] = now
    live_meta["last_stats"] = stats
    if aborted:
        live_meta["last_abort_at"] = now
        live_meta["last_abort_reason"] = abort_reason or stats.get("abort_reason") or "aborted"
    manifest["live_fetch"] = live_meta
    if preserved_queue is not None:
        manifest["live_fetch_queue"] = preserved_queue
    save_json(MANIFEST_JSON, manifest)
