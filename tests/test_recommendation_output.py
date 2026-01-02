"""
各テストケースにおける推奨医薬品を出力するスクリプト
"""
import sys
import os
import pandas as pd
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# .envファイルから環境変数を読み込み
try:
    from dotenv import load_dotenv
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    env_path = os.path.join(base_dir, '.env')
    if os.path.exists(env_path):
        load_dotenv(env_path, override=True)
    else:
        load_dotenv(override=True)
except ImportError:
    pass

from scoring_utils import calculate_efficacy_specificity_score, is_word_match, TANN_FALSE_POSITIVE_BLACKLIST
from rule_based_recommendation import calculate_ingredient_based_boost

# CSVデータを読み込み
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSV_PATH = os.path.join(BASE_DIR, "data", "otc_medicine_data.csv")

print("=" * 80)
print("各テストケースにおける推奨医薬品候補")
print("=" * 80)

# テストケース定義
test_cases = [
    {
        "name": "test_001: 「たん」と「痰」の同義語マッピング",
        "symptom": "痰",
        "nlu_result": {"symptoms": [{"name": "痰"}]}
    },
    {
        "name": "test_002: 効能特異性スコア計算の改善（効能に「たん」が含まれている場合）",
        "symptom": "たん",
        "nlu_result": {"symptoms": [{"name": "たん"}]}
    },
    {
        "name": "test_007: 去痰成分ボーナスのテスト",
        "symptom": "たん",
        "nlu_result": {"symptoms": [{"name": "たん"}]},
        "expectorant_keywords": ["カルボシステイン", "ブロムヘキシン", "アンブロキソール"]
    },
    {
        "name": "test_008: 鎮咳成分ペナルティのテスト",
        "symptom": "たん",
        "nlu_result": {"symptoms": [{"name": "たん"}]},
        "expectorant_keywords": ["カルボシステイン"],
        "antitussive_keywords": ["ジヒドロコデイン", "コデイン"]
    },
    {
        "name": "test_009: 漢方薬の去痰成分ボーナスのテスト",
        "symptom": "たん",
        "nlu_result": {"symptoms": [{"name": "たん"}]},
        "kampo_keywords": ["麦門冬", "バクモンドウ", "清肺湯", "五虎湯"]
    },
    {
        "name": "test_012: 統合テスト",
        "symptom": "たん",
        "nlu_result": {"symptoms": [{"name": "たん"}]},
        "expectorant_keywords": ["カルボシステイン"],
        "antitussive_keywords": ["ジヒドロコデイン"]
    }
]

try:
    medicine_df = pd.read_csv(CSV_PATH, encoding='utf-8')
    print(f"医薬品データ読み込み完了: {len(medicine_df)}件\n")
except Exception as e:
    print(f"エラー: 医薬品データの読み込みに失敗しました: {e}")
    sys.exit(1)

for i, test_case in enumerate(test_cases, 1):
    print(f"\n【テストケース {i}】{test_case['name']}")
    print(f"症状: {test_case['symptom']}")
    print("-" * 80)
    
    symptom_name = test_case['symptom']
    nlu_result = test_case['nlu_result']
    
    # 効能に症状が含まれる医薬品を検索
    candidates = []
    for idx, row in medicine_df.iterrows():
        efficacy = str(row.get('効能効果', ''))
        product_name = str(row.get('製品名', ''))
        ingredients = str(row.get('成分', ''))
        
        if not efficacy or efficacy == 'nan':
            continue
        
        # 効能に症状が含まれているかチェック
        normalized_efficacy = efficacy.lower()
        if symptom_name in normalized_efficacy or 'たん' in normalized_efficacy or '痰' in normalized_efficacy:
            # 単語境界チェック
            from scoring_utils import normalize_text
            normalized_efficacy_full = normalize_text(efficacy)
            normalized_symptom = normalize_text(symptom_name)
            
            blacklist = TANN_FALSE_POSITIVE_BLACKLIST if normalized_symptom == "たん" else None
            if is_word_match(normalized_symptom, normalized_efficacy_full, blacklist=blacklist):
                candidate = {
                    'product_name': product_name,
                    'efficacy': efficacy,
                    'ingredients': ingredients,
                    'medicine_type': str(row.get('医薬品の種類', '')),
                    'row_data': row.to_dict()
                }
                
                # 効能特異性スコアを計算
                try:
                    efficacy_score = calculate_efficacy_specificity_score(candidate, nlu_result)
                    candidate['efficacy_score'] = efficacy_score
                except:
                    candidate['efficacy_score'] = 0.0
                
                # 去痰成分ボーナスを計算
                try:
                    boost = calculate_ingredient_based_boost(candidate, nlu_result, {})
                    candidate['ingredient_boost'] = boost
                except:
                    candidate['ingredient_boost'] = 0.0
                
                # フィルタリング（テストケース固有の条件）
                include = True
                if 'expectorant_keywords' in test_case:
                    has_expectorant = any(kw in ingredients for kw in test_case['expectorant_keywords'])
                    if not has_expectorant:
                        include = False
                
                if 'kampo_keywords' in test_case:
                    has_kampo = any(kw in product_name or kw in ingredients for kw in test_case['kampo_keywords'])
                    if not has_kampo:
                        include = False
                
                if 'antitussive_keywords' in test_case:
                    has_antitussive = any(kw in ingredients for kw in test_case['antitussive_keywords'])
                    if not has_antitussive:
                        include = False
                
                if include:
                    candidates.append(candidate)
    
    # スコアでソート
    candidates.sort(key=lambda x: (x.get('efficacy_score', 0) + x.get('ingredient_boost', 0)), reverse=True)
    
    # 上位5件を表示
    print(f"候補数: {len(candidates)}")
    for j, candidate in enumerate(candidates[:5], 1):
        print(f"\n  {j}. {candidate['product_name']}")
        print(f"     効能: {candidate['efficacy'][:80]}...")
        print(f"     成分: {candidate['ingredients'][:80]}...")
        print(f"     効能特異性スコア: {candidate.get('efficacy_score', 0):.4f}")
        print(f"     成分ボーナス: {candidate.get('ingredient_boost', 0):.4f}")
        print(f"     合計スコア: {candidate.get('efficacy_score', 0) + candidate.get('ingredient_boost', 0):.4f}")
    
    if len(candidates) == 0:
        print("該当する医薬品が見つかりませんでした")
    
    print("=" * 80)
