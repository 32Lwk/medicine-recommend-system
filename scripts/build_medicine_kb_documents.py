#!/usr/bin/env python3
"""CSV から Medicine Managed KB 用 Markdown + metadata.json を生成。

Usage:
  python scripts/build_medicine_kb_documents.py
  python scripts/build_medicine_kb_documents.py --output build/medicine

出力は sync-medicine-kb-to-s3.sh 経由で S3 medicine/ へアップロードする。
"""
from __future__ import annotations

import argparse
import ast
import csv
import hashlib
import json
import math
import re
import shutil
import sys
import unicodedata
from pathlib import Path
from typing import Any, Dict

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DATA_DIR = ROOT / "data"
DEFAULT_OUT = ROOT / "build" / "medicine"

METADATA_MAX_BYTES = 1024


def _normalize(text: str) -> str:
    return unicodedata.normalize("NFKC", (text or "").strip())


def _safe_str(val: Any) -> str:
    if val is None:
        return ""
    if isinstance(val, float) and math.isnan(val):
        return ""
    return str(val).strip()


def kb_product_slug(product_name: str, manufacturer: str) -> str:
    name = _normalize(product_name)
    mfr = _normalize(manufacturer)
    raw = f"{name}-{mfr}" if mfr else name
    slug = re.sub(r"\s+", "-", raw)
    slug = re.sub(r"[^\w\-一-龥ぁ-んァ-ヶ]", "", slug)
    slug = slug.strip("-")
    if len(slug) >= 2:
        return slug[:120]
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]
    return f"p-{digest}"


def _slug_key(base: str) -> str:
    s = base.lower()
    s = re.sub(r"[^\w\-一-龥ぁ-んァ-ヶ]", "-", s)
    s = re.sub(r"-+", "-", s).strip("-")
    return s[:80] or "item"


def allocate_unique_slug(base: str, used: Dict[str, int]) -> str:
    key = _slug_key(base)
    count = used.get(key, 0)
    used[key] = count + 1
    if count == 0:
        return key
    return f"{key}-{count + 1}"


def _truncate_metadata(meta: Dict[str, Any], max_bytes: int = METADATA_MAX_BYTES) -> Dict[str, Any]:
    wrapped = {"metadataAttributes": meta}
    if len(json.dumps(wrapped, ensure_ascii=False).encode("utf-8")) <= max_bytes:
        return meta
    trimmed = dict(meta)
    for drop_key in ("manufacturer", "medicine_type"):
        trimmed.pop(drop_key, None)
        wrapped = {"metadataAttributes": trimmed}
        if len(json.dumps(wrapped, ensure_ascii=False).encode("utf-8")) <= max_bytes:
            return trimmed
    for k, v in list(trimmed.items()):
        if isinstance(v, str) and len(v) > 40:
            trimmed[k] = v[:40]
    return trimmed


def write_doc_pair(base_path: Path, md_body: str, metadata: Dict[str, Any]) -> None:
    base_path.parent.mkdir(parents=True, exist_ok=True)
    md_path = base_path.with_suffix(".md")
    md_path.write_text(md_body, encoding="utf-8")
    meta = _truncate_metadata(metadata)
    meta_path = Path(f"{md_path}.metadata.json")
    meta_path.write_text(
        json.dumps({"metadataAttributes": meta}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def build_products(out_root: Path) -> int:
    import pandas as pd

    df = pd.read_csv(DATA_DIR / "otc_medicine_data.csv")
    used: Dict[str, int] = {}
    count = 0
    for _, row in df.iterrows():
        product_name = _safe_str(row.get("製品名"))
        if not product_name:
            continue
        manufacturer = _safe_str(row.get("メーカー名"))
        slug = allocate_unique_slug(kb_product_slug(product_name, manufacturer), used)
        classification = _safe_str(row.get("分類"))
        medicine_type = _safe_str(row.get("医薬品の種類"))
        efficacy = _safe_str(row.get("効能効果"))
        usage = _safe_str(row.get("用法用量"))
        age = _safe_str(row.get("年齢制限"))
        ingredients = _safe_str(row.get("成分"))
        doping = _safe_str(row.get("禁止物質あり"))
        competition = _safe_str(row.get("競技会区分"))
        conditions = _safe_str(row.get("条件"))

        md = f"""# {product_name}

- **メーカー**: {manufacturer or "—"}
- **分類**: {classification or "—"}
- **医薬品の種類**: {medicine_type or "—"}

## 効能効果

{efficacy or "（記載なし）"}

## 用法用量

{usage or "（記載なし）"}

## 成分

{ingredients or "（記載なし）"}

## 年齢制限

{age or "（記載なし）"}

## ドーピング

- **禁止物質**: {doping or "—"}
- **競技会区分**: {competition or "—"}
- **条件**: {conditions or "—"}
"""
        meta = {
            "domain": "medicine",
            "doc_type": "product",
            "product_name": product_name[:80],
            "manufacturer": manufacturer[:40],
            "classification": classification[:20],
            "medicine_type": medicine_type[:30],
        }
        write_doc_pair(out_root / "products" / slug, md, meta)
        count += 1
    return count


def build_interactions(out_root: Path) -> int:
    used: Dict[str, int] = {}
    count = 0
    with (DATA_DIR / "medicine_interactions.csv").open(encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            a = _safe_str(row.get("成分A"))
            b = _safe_str(row.get("成分B"))
            level = _safe_str(row.get("相互作用レベル"))
            desc = _safe_str(row.get("説明"))
            if not a or not b:
                continue
            slug = allocate_unique_slug(f"{a}-{b}", used)
            md = f"""# 相互作用: {a} × {b}

- **相互作用レベル**: {level}
- **説明**: {desc}

## 成分A

{a}

## 成分B

{b}
"""
            meta = {
                "domain": "medicine",
                "doc_type": "interaction",
                "ingredient_a": a[:40],
                "ingredient_b": b[:40],
                "risk_level": level[:10],
            }
            write_doc_pair(out_root / "interactions" / slug, md, meta)
            count += 1
    return count


def build_side_effects(out_root: Path) -> int:
    used: Dict[str, int] = {}
    count = 0
    with (DATA_DIR / "medicine_side_effects.csv").open(encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            ingredient = _safe_str(row.get("成分名"))
            level = _safe_str(row.get("副作用レベル"))
            symptoms = _safe_str(row.get("副作用症状"))
            contraind = _safe_str(row.get("禁忌条件"))
            if not ingredient:
                continue
            slug = allocate_unique_slug(ingredient, used)
            md = f"""# 副作用: {ingredient}

- **副作用レベル**: {level}
- **副作用症状**: {symptoms}
- **禁忌条件**: {contraind}

## 成分

{ingredient}
"""
            meta = {
                "domain": "medicine",
                "doc_type": "side_effect",
                "ingredient": ingredient[:40],
                "side_effect_level": level[:10],
            }
            write_doc_pair(out_root / "side_effects" / slug, md, meta)
            count += 1
    return count


def _load_kanpo_rules() -> Dict[str, Any]:
    text = (DATA_DIR / "kanpo_medicine.csv").read_text(encoding="utf-8")
    eq_idx = text.find("=")
    if eq_idx < 0:
        return {}
    return ast.literal_eval(text[eq_idx + 1 :].strip())


def build_kanpo(out_root: Path) -> int:
    rules = _load_kanpo_rules()
    used: Dict[str, int] = {}
    count = 0
    for name, rule in rules.items():
        if not isinstance(rule, dict):
            continue
        slug = allocate_unique_slug(name, used)
        primary = rule.get("primary_symptoms") or []
        inappropriate = rule.get("inappropriate_symptoms") or []
        md = f"""# 漢方: {name}

## 証・条件

{rule.get("sho_condition") or "—"}

## 適応症状

{", ".join(primary) if primary else "—"}

## 不適症状

{", ".join(inappropriate) if inappropriate else "—"}

## ペナルティ係数

{rule.get("penalty", "—")}
"""
        meta = {"domain": "medicine", "doc_type": "kanpo", "kanpo_name": name[:40]}
        write_doc_pair(out_root / "kanpo" / slug, md, meta)
        count += 1
    return count


def build_efficacy(out_root: Path) -> int:
    used: Dict[str, int] = {}
    count = 0
    with (DATA_DIR / "summarized_efficacy_data.csv").open(encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            product = _safe_str(row.get("製品名"))
            summary = _safe_str(row.get("Summarized Efficacy"))
            if not product:
                continue
            slug = allocate_unique_slug(product, used)
            md = f"""# 効能要約: {product}

## 製品名

{product}

## Summarized Efficacy

{summary or "（記載なし）"}
"""
            meta = {"domain": "medicine", "doc_type": "efficacy", "product_name": product[:80]}
            write_doc_pair(out_root / "efficacy" / slug, md, meta)
            count += 1
    return count


def copy_raw_csv(out_root: Path) -> int:
    raw_dir = out_root / "raw" / "data"
    raw_dir.mkdir(parents=True, exist_ok=True)
    n = 0
    for csv_path in sorted(DATA_DIR.glob("*.csv")):
        (raw_dir / csv_path.name).write_bytes(csv_path.read_bytes())
        n += 1
    return n


def _remove_stale_metadata(out_root: Path) -> None:
    """旧命名 (*.metadata.json) を削除し Bedrock 規約 (*.md.metadata.json) のみ残す。"""
    for stale in out_root.rglob("*.metadata.json"):
        if stale.name.endswith(".md.metadata.json"):
            continue
        stale.unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build Medicine KB markdown documents")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUT)
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Remove output directory before build",
    )
    args = parser.parse_args()

    if args.clean and args.output.exists():
        shutil.rmtree(args.output)

    stats = {
        "products": build_products(args.output),
        "interactions": build_interactions(args.output),
        "side_effects": build_side_effects(args.output),
        "kanpo": build_kanpo(args.output),
        "efficacy": build_efficacy(args.output),
        "raw_csv": copy_raw_csv(args.output),
    }
    _remove_stale_metadata(args.output)
    print(json.dumps({"output": str(args.output), "counts": stats}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
