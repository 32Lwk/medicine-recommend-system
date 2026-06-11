"""
各テストケースにおける推奨医薬品を出力するスクリプト。

pytest ではなく手動実行用:
  python scripts/recommendation_output_report.py
"""
from __future__ import annotations

import os
import sys

import pandas as pd

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

try:
    from dotenv import load_dotenv

    env_path = os.path.join(PROJECT_ROOT, ".env")
    if os.path.exists(env_path):
        load_dotenv(env_path, override=True)
    else:
        load_dotenv(override=True)
except ImportError:
    pass

from src.core.rule_based_recommendation import calculate_ingredient_based_boost
from src.core.scoring_utils import (
    TANN_FALSE_POSITIVE_BLACKLIST,
    calculate_efficacy_specificity_score,
    is_word_match,
)

CSV_PATH = os.path.join(PROJECT_ROOT, "data", "otc_medicine_data.csv")

TEST_CASES = [
    {
        "name": "test_001: 「たん」と「痰」の同義語マッピング",
        "symptom": "痰",
        "nlu_result": {"symptoms": [{"name": "痰"}]},
    },
    {
        "name": "test_002: 効能特異性スコア計算の改善（効能に「たん」が含まれている場合）",
        "symptom": "たん",
        "nlu_result": {"symptoms": [{"name": "たん"}]},
    },
    {
        "name": "test_007: 去痰成分ボーナスのテスト",
        "symptom": "たん",
        "nlu_result": {"symptoms": [{"name": "たん"}]},
        "expectorant_keywords": ["カルボシステイン", "ブロムヘキシン", "アンブロキソール"],
    },
    {
        "name": "test_008: 鎮咳成分ペナルティのテスト",
        "symptom": "たん",
        "nlu_result": {"symptoms": [{"name": "たん"}]},
        "expectorant_keywords": ["カルボシステイン"],
        "antitussive_keywords": ["ジヒドロコデイン", "コデイン"],
    },
    {
        "name": "test_009: 漢方薬の去痰成分ボーナスのテスト",
        "symptom": "たん",
        "nlu_result": {"symptoms": [{"name": "たん"}]},
        "kampo_keywords": ["麦門冬", "バクモンドウ", "清肺湯", "五虎湯"],
    },
    {
        "name": "test_012: 統合テスト",
        "symptom": "たん",
        "nlu_result": {"symptoms": [{"name": "たん"}]},
        "expectorant_keywords": ["カルボシステイン"],
        "antitussive_keywords": ["ジヒドロコデイン"],
    },
]


def main() -> None:
    print("=" * 80)
    print("各テストケースにおける推奨医薬品候補")
    print("=" * 80)

    try:
        medicine_df = pd.read_csv(CSV_PATH, encoding="utf-8")
        print(f"医薬品データ読み込み完了: {len(medicine_df)}件\n")
    except Exception as e:
        print(f"エラー: 医薬品データの読み込みに失敗しました: {e}")
        sys.exit(1)

    for i, test_case in enumerate(TEST_CASES, 1):
        print(f"\n【テストケース {i}】{test_case['name']}")
        print(f"症状: {test_case['symptom']}")
        print("-" * 80)

        symptom_name = test_case["symptom"]
        nlu_result = test_case["nlu_result"]
        candidates = []

        for _, row in medicine_df.iterrows():
            efficacy = str(row.get("効能効果", ""))
            product_name = str(row.get("製品名", ""))
            ingredients = str(row.get("成分", ""))

            if not efficacy or efficacy == "nan":
                continue

            normalized_efficacy = efficacy.lower()
            if (
                symptom_name in normalized_efficacy
                or "たん" in normalized_efficacy
                or "痰" in normalized_efficacy
            ):
                from src.core.scoring_utils import normalize_text

                normalized_efficacy_full = normalize_text(efficacy)
                normalized_symptom = normalize_text(symptom_name)

                blacklist = (
                    TANN_FALSE_POSITIVE_BLACKLIST
                    if normalized_symptom == "たん"
                    else None
                )
                if is_word_match(
                    normalized_symptom, normalized_efficacy_full, blacklist=blacklist
                ):
                    candidate = {
                        "product_name": product_name,
                        "efficacy": efficacy,
                        "ingredients": ingredients,
                        "medicine_type": str(row.get("医薬品の種類", "")),
                        "row_data": row.to_dict(),
                    }

                    try:
                        candidate["efficacy_score"] = calculate_efficacy_specificity_score(
                            candidate, nlu_result
                        )
                    except Exception:
                        candidate["efficacy_score"] = 0.0

                    try:
                        candidate["ingredient_boost"] = calculate_ingredient_based_boost(
                            candidate, nlu_result, {}
                        )
                    except Exception:
                        candidate["ingredient_boost"] = 0.0

                    include = True
                    if "expectorant_keywords" in test_case:
                        include = any(
                            kw in ingredients for kw in test_case["expectorant_keywords"]
                        )
                    if include and "kampo_keywords" in test_case:
                        include = any(
                            kw in product_name or kw in ingredients
                            for kw in test_case["kampo_keywords"]
                        )
                    if include and "antitussive_keywords" in test_case:
                        include = any(
                            kw in ingredients for kw in test_case["antitussive_keywords"]
                        )

                    if include:
                        candidates.append(candidate)

        candidates.sort(
            key=lambda x: (x.get("efficacy_score", 0) + x.get("ingredient_boost", 0)),
            reverse=True,
        )

        print(f"候補数: {len(candidates)}")
        for j, candidate in enumerate(candidates[:5], 1):
            print(f"\n  {j}. {candidate['product_name']}")
            print(f"     効能: {candidate['efficacy'][:80]}...")
            print(f"     成分: {candidate['ingredients'][:80]}...")
            print(f"     効能特異性スコア: {candidate.get('efficacy_score', 0):.4f}")
            print(f"     成分ボーナス: {candidate.get('ingredient_boost', 0):.4f}")
            total = candidate.get("efficacy_score", 0) + candidate.get("ingredient_boost", 0)
            print(f"     合計スコア: {total:.4f}")

        if len(candidates) == 0:
            print("該当する医薬品が見つかりませんでした")

        print("=" * 80)


if __name__ == "__main__":
    main()
