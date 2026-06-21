#!/usr/bin/env python3
"""store_products.json を store_product_index と同じ正規化規則で重複排除する。"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.core.scoring_utils import basic_normalize_text  # noqa: E402

_MIN_TOKEN_LEN = 2
DEFAULT_PATH = ROOT / "data" / "store_products.json"


def _count_entries(data: dict) -> tuple[int, int, int]:
    products = brands = 0
    for cd in data.values():
        for sd in cd.get("subcategories", {}).values():
            products += len(sd.get("products", []))
            brands += len(sd.get("brands", []))
    return products + brands, products, brands


def dedup_store_products(data: dict) -> dict:
    """正規化トークン単位で先勝ち（index 構築順と一致）。"""
    global_seen: set[str] = set()
    out: dict = {}

    for category_name, category_data in data.items():
        sub_out: dict = {}
        for sub_name, sub_data in category_data.get("subcategories", {}).items():
            new_sub = dict(sub_data)
            kept_products: list[str] = []
            kept_brands: list[str] = []

            for product in sub_data.get("products", []):
                norm = basic_normalize_text(product)
                if len(norm) >= _MIN_TOKEN_LEN:
                    if norm in global_seen:
                        continue
                    global_seen.add(norm)
                elif product in kept_products:
                    continue
                kept_products.append(product)

            for brand in sub_data.get("brands", []):
                norm = basic_normalize_text(brand)
                if len(norm) >= _MIN_TOKEN_LEN:
                    if norm in global_seen:
                        continue
                    global_seen.add(norm)
                elif brand in kept_brands:
                    continue
                kept_brands.append(brand)

            new_sub["products"] = kept_products
            if kept_brands:
                new_sub["brands"] = kept_brands
            elif "brands" in new_sub:
                del new_sub["brands"]
            sub_out[sub_name] = new_sub

        out[category_name] = {"subcategories": sub_out}

    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--path",
        type=Path,
        default=DEFAULT_PATH,
        help="store_products.json のパス",
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="ファイルを上書き保存（省略時は dry-run）",
    )
    args = parser.parse_args()

    raw = json.loads(args.path.read_text(encoding="utf-8"))
    before_total, before_p, before_b = _count_entries(raw)
    deduped = dedup_store_products(raw)
    after_total, after_p, after_b = _count_entries(deduped)

    print(f"path: {args.path}")
    print(f"before: total={before_total} products={before_p} brands={before_b}")
    print(f"after:  total={after_total} products={after_p} brands={after_b}")
    print(f"removed: {before_total - after_total}")

    if args.write:
        args.path.write_text(
            json.dumps(deduped, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print("written.")
    else:
        print("dry-run (use --write to apply)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
