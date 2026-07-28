#!/usr/bin/env python3
"""CSV から Medicine Managed KB 用 Markdown + metadata.json を生成。

Usage:
  python scripts/build_medicine_kb_documents.py
  python scripts/build_medicine_kb_documents.py --output build/medicine
  python scripts/build_medicine_kb_documents.py --output build/medicine --clean

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
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DATA_DIR = ROOT / "data"
DEFAULT_OUT = ROOT / "build" / "medicine"

# Bedrock metadata 制限（docs: 1KB / 35 keys）
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
    """{product_name}-{manufacturer} を NFKC 正規化。空なら hash。"""
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


def _metadata_byte_size(meta: Dict[str, Any]) -> int:
    return len(json.dumps({"metadataAttributes": meta}, ensure_ascii=False).encode("utf-8"))


def _stringify_metadata_values(meta: Dict[str, Any]) -> Dict[str, str]:
    """Bedrock metadataAttributes は string 型のみ — bool/数値を文字列化。"""
    out: Dict[str, str] = {}
    for key, value in meta.items():
        if value is None:
            continue
        if isinstance(value, bool):
            out[key] = "true" if value else "false"
        else:
            out[key] = str(value)
    return out


def _truncate_metadata(meta: Dict[str, Any], max_bytes: int = METADATA_MAX_BYTES) -> Dict[str, Any]:
    """metadataAttributes を 1KB 以内に収める。"""
    if _metadata_byte_size(meta) <= max_bytes:
        return meta

    trimmed = dict(meta)
    for drop_key in ("synonyms", "manufacturer", "medicine_type", "usage_excerpt", "efficacy_excerpt"):
        trimmed.pop(drop_key, None)
        if _metadata_byte_size(trimmed) <= max_bytes:
            return trimmed

    if "synonyms" in trimmed and isinstance(trimmed["synonyms"], str):
        syns = trimmed["synonyms"]
        while syns and _metadata_byte_size({**trimmed, "synonyms": syns}) > max_bytes:
            parts = syns.split(",")
            if len(parts) <= 1:
                trimmed.pop("synonyms", None)
                break
            syns = ",".join(parts[:-1])
        if "synonyms" in trimmed:
            trimmed["synonyms"] = syns

    if _metadata_byte_size(trimmed) <= max_bytes:
        return trimmed

    for k, v in list(trimmed.items()):
        if isinstance(v, str) and len(v) > 40:
            trimmed[k] = v[:40]
    return trimmed


def write_doc_pair(base_path: Path, md_body: str, metadata: Dict[str, Any]) -> None:
    base_path.parent.mkdir(parents=True, exist_ok=True)
    md_path = base_path.with_suffix(".md")
    md_path.write_text(md_body, encoding="utf-8")
    meta = _truncate_metadata(_stringify_metadata_values(metadata))
    meta_path = Path(f"{md_path}.metadata.json")
    meta_path.write_text(
        json.dumps({"metadataAttributes": meta}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _lookup_synonyms(names: List[str]) -> str:
    from src.services.ingredient_synonym_registry import lookup_synonyms_for_names

    return lookup_synonyms_for_names(names)


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

## 用法・用量

{usage or "（記載なし）"}

## 成分

{ingredients or "（記載なし）"}

## 年齢制限

{age or "（記載なし）"}

## ドーピング・競技会区分

- **禁止物質**: {doping or "—"}
- **競技会区分**: {competition or "—"}
- **条件**: {conditions or "—"}
"""
        has_age = bool(age and age not in ("（記載なし）", "—", "nan"))
        has_doping = bool(
            (doping and "禁止" in doping)
            or (competition and competition not in ("—", ""))
        )
        from src.services.ingredient_synonym_registry import (
            brand_hints_for_product,
            lookup_synonyms_for_names,
            split_ingredient_field,
        )

        ingredient_parts = split_ingredient_field(ingredients)
        synonym_blob = lookup_synonyms_for_names(
            [product_name, *ingredient_parts, *brand_hints_for_product(product_name)]
        )
        if synonym_blob:
            md = f"{md}\n\n## 検索用同義語\n\n{synonym_blob}\n"
        meta: Dict[str, Any] = {
            "domain": "medicine",
            "doc_type": "product",
            "product_name": product_name[:80],
            "manufacturer": manufacturer[:40],
            "classification": classification[:20],
            "medicine_type": medicine_type[:30],
            "has_age_restriction": has_age,
            "has_doping_info": has_doping,
        }
        if synonym_blob:
            meta["synonyms"] = synonym_blob[:200]
        write_doc_pair(out_root / "products" / slug, md, meta)
        count += 1
    return count


def build_interactions(out_root: Path, _synonym_map: Dict[str, List[str]] | None = None) -> int:
    used: Dict[str, int] = {}
    count = 0
    with (DATA_DIR / "medicine_interactions.csv").open(encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            a = _safe_str(row.get("成分A"))
            b = _safe_str(row.get("成分B"))
            level = _safe_str(row.get("相互作用レベル"))
            desc = _safe_str(row.get("説明"))
            source = _safe_str(row.get("出典"))
            if not a or not b:
                continue
            slug = allocate_unique_slug(f"{a}-{b}", used)
            md = f"""# 相互作用: {a} × {b}

- **相互作用レベル**: {level}
- **説明**: {desc}
{f"- **出典**: {source}" if source else ""}

## 成分A

{a}

## 成分B

{b}
"""
            meta: Dict[str, Any] = {
                "domain": "medicine",
                "doc_type": "interaction",
                "ingredient_a": a[:40],
                "ingredient_b": b[:40],
                "risk_level": level[:10],
            }
            synonyms = _lookup_synonyms([a, b])
            if synonyms:
                md = f"{md}\n\n## 検索用同義語\n\n{synonyms}\n"
                meta["synonyms"] = synonyms
            write_doc_pair(out_root / "interactions" / slug, md, meta)
            count += 1
    return count


def build_side_effects(out_root: Path, _synonym_map: Dict[str, List[str]] | None = None) -> int:
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
            meta: Dict[str, Any] = {
                "domain": "medicine",
                "doc_type": "side_effect",
                "ingredient": ingredient[:40],
                "side_effect_level": level[:10],
            }
            synonyms = _lookup_synonyms([ingredient])
            if synonyms:
                md = f"{md}\n\n## 検索用同義語\n\n{synonyms}\n"
                meta["synonyms"] = synonyms
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
    """生 CSV をローカル build/raw に退避（S3/KB には載せない — 5-0-3）。"""
    raw_dir = out_root / "raw" / "data"
    raw_dir.mkdir(parents=True, exist_ok=True)
    n = 0
    for csv_path in sorted(DATA_DIR.glob("*.csv")):
        (raw_dir / csv_path.name).write_bytes(csv_path.read_bytes())
        n += 1
    return n


def build_topics(out_root: Path) -> int:
    """汎用問い向けトピックガイド MD（Phase 1.5）。"""
    import pandas as pd

    df = pd.read_csv(DATA_DIR / "otc_medicine_data.csv")
    analgesic = df[df["医薬品の種類"].astype(str).str.contains("解熱|鎮痛", na=False)]
    interval_lines: List[str] = []
    for _, row in analgesic.head(8).iterrows():
        name = _safe_str(row.get("製品名"))
        usage = _safe_str(row.get("用法用量"))[:200]
        if name and usage:
            interval_lines.append(f"- **{name}**: {usage}")

    usage_md = f"""# 解熱鎮痛薬の服用間隔・1日回数ガイド

## 概要

解熱鎮痛薬（OTC）では、**用法用量を守り、最短服用間隔を空ける**ことが重要です。
多くの製品は **1日2〜3回（4〜6時間以上あけて）** 服用が基本です。

## キーワード

解熱鎮痛薬, 服用間隔, 何時間おき, 1日何回, 最低间隔, 用法・用量, カロナール, タイレノール, ロキソニン

## 代表例（OTC データより）

{chr(10).join(interval_lines) if interval_lines else "（代表例なし）"}

## 注意

- 異なる解熱鎮痛薬の成分を重複して飲まない
- 症状が続く場合は登録販売者・医師に相談
"""
    write_doc_pair(
        out_root / "topics" / "usage-dose-interval",
        usage_md,
        {
            "domain": "medicine",
            "doc_type": "topic_guide",
            "topic": "usage_dose_interval",
            "keywords": "解熱鎮痛,服用間隔,何時間,1日回数,用法",
        },
    )

    age_examples: List[str] = []
    for _, row in df[df["年齢制限"].astype(str).str.contains("15", na=False)].head(6).iterrows():
        name = _safe_str(row.get("製品名"))
        age = _safe_str(row.get("年齢制限"))
        if name:
            age_examples.append(f"- **{name}**: {age or '用法用量参照'}")

    age_md = f"""# 年齢制限ガイド（小児・15歳未満・高齢者）

## 15歳未満・小児

多くの解熱鎮痛薬・風邪薬は **15歳未満・7歳未満・3歳未満** など年齢別の用法があります。
小児用製品以外を子どもに使う場合は **必ず用法用量欄の年齢区分** を確認してください。

## 小児用風邪薬

小児向け製品は **年齢・体重に応じた1回量・1日回数** が記載されています。

## 高齢者

高齢者は腎機能・胃腸への配慮が必要です。**NSAID（イブプロフェン・ロキソプロフェン等）** は
胃障害・腎障害リスクに注意し、短期・最小量を心がけてください。

## キーワード

15歳未満, 小児, 高齢者, 年齢制限, 風邪薬, 解熱鎮痛

## 代表例

{chr(10).join(age_examples) if age_examples else "（代表例なし）"}
"""
    write_doc_pair(
        out_root / "topics" / "age-restriction-guide",
        age_md,
        {
            "domain": "medicine",
            "doc_type": "topic_guide",
            "topic": "age_restriction",
            "keywords": "15歳未満,小児,高齢者,年齢制限,風邪薬",
        },
    )

    nsaid_md = """# NSAID（非ステロイド性抗炎症薬）と高齢者の注意

## NSAID とは

**NSAID**（Non-Steroidal Anti-Inflammatory Drug / 非ステロイド性抗炎症薬）には、
**イブプロフェン**, **ロキソプロフェン**, **アスピリン**, **ジクロフェナク** 等が含まれます。

## 高齢者が NSAID を使うとき

- 胃腸障害（胃出血・潰瘍）リスクが高まる
- 腎機能低下時は用量・期間に注意
- 他の薬（ワーファリン等）との相互作用に注意
- 必要最小限の短期使用を心がける

## キーワード

NSAID, 非ステロイド性抗炎症薬, イブプロフェン, ロキソプロフェン, 高齢者, 解熱鎮痛
"""
    write_doc_pair(
        out_root / "topics" / "nsaid-elderly",
        nsaid_md,
        {
            "domain": "medicine",
            "doc_type": "topic_guide",
            "topic": "nsaid_elderly",
            "keywords": "NSAID,高齢者,イブプロフェン,ロキソプロフェン",
        },
    )
    return 3


def build_doping_guides(out_root: Path) -> int:
    """ドーピング関連トピック（Phase 1.5）。"""
    pseudo_md = """# プソイドエフェドリン・エフェドリンとドーピング

## 概要

**プソイドエフェドリン**（Pseudoephedrine）および **エフェドリン** 系成分は、
鼻づまり改善等に用いられる一方、**WADA 禁止リスト（S6 興奮剤）** の対象となる場合があります。

## 競技会区分

市販薬の package では **S6. 興奮剤** 等の **競技会区分** が記載される製品があります。
競技参加者は **禁止物質あり** 表示と条件欄を必ず確認してください。

## キーワード

プソイドエフェドリン, エフェドリン, ドーピング, WADA, S6, 禁止物質, 競技会区分
"""
    write_doc_pair(
        out_root / "doping" / "pseudoephedrine",
        pseudo_md,
        {
            "domain": "medicine",
            "doc_type": "doping_guide",
            "topic": "pseudoephedrine",
            "keywords": "プソイドエフェドリン,エフェドリン,ドーピング,S6",
        },
    )
    return 1


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
        "interactions": build_interactions(args.output, {}),
        "side_effects": build_side_effects(args.output, {}),
        "kanpo": build_kanpo(args.output),
        "efficacy": build_efficacy(args.output),
        "topics": build_topics(args.output),
        "doping_guides": build_doping_guides(args.output),
        "raw_csv": copy_raw_csv(args.output),
    }
    _remove_stale_metadata(args.output)
    print(json.dumps({"output": str(args.output), "counts": stats}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
