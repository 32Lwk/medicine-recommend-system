# -*- coding: utf-8 -*-
"""
改善後のテスト結果を詳細に評価する
"""
import sys
import io
import json

# Windows環境での文字エンコーディング問題を回避
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

with open("recommended_medicines_detail.json", "r", encoding="utf-8") as f:
    results = json.load(f)

print("="*80)
print("改善後のテスト結果詳細評価")
print("="*80)

# 改善点1: 頭痛のみの場合の風邪薬ペナルティ
print("\n【改善点1】頭痛のみの場合の風邪薬ペナルティ")
print("-"*80)

headache_tests = [
    r for r in results 
    if ("頭痛" in r["test_name"] or "テスト2" in r["test_name"] or "テスト11-ケース2" in r["test_name"] or "テスト13-ケース2" in r["test_name"])
    and "風邪" not in r["test_name"]
]

for test in headache_tests:
    print(f"\n{test['test_name']}")
    print(f"症状: {test['symptom']}")
    medicines = test['recommended_medicines']
    
    # 風邪薬が1位に来ているか確認
    has_cold_medicine_at_top = False
    has_nsaid_at_top = False
    has_kampo_at_top = False
    
    for i, med in enumerate(medicines[:3], 1):
        medicine_type = med.get('medicine_type', '')
        product_name = med.get('product_name', '')
        ingredients = med.get('ingredients', '')
        
        if i == 1:
            if '風邪薬' in medicine_type:
                has_cold_medicine_at_top = True
                print(f"  [問題] {i}位に風邪薬が推奨されています: {product_name}")
                print(f"    成分: {ingredients[:100] if ingredients else '不明'}...")
            elif '解熱鎮痛薬' in medicine_type:
                # NSAIDs成分が含まれているか確認
                nsaid_keywords = ["アセトアミノフェン", "イブプロフェン", "ロキソプロフェン", "ロキソニン"]
                if any(kw in str(ingredients) for kw in nsaid_keywords):
                    has_nsaid_at_top = True
                    print(f"  [改善成功] {i}位にNSAIDs含有の解熱鎮痛薬が推奨されています: {product_name}")
                elif "漢方" in product_name or "エキス" in str(ingredients):
                    has_kampo_at_top = True
                    print(f"  [要改善] {i}位に漢方薬が推奨されています: {product_name}")
                else:
                    print(f"  [改善成功] {i}位に解熱鎮痛薬が推奨されています: {product_name}")

# 改善点2: 肩こり外用薬の最適解
print("\n\n【改善点2】肩こり外用薬の最適解")
print("-"*80)

shoulder_tests = [r for r in results if "肩こり" in r["test_name"] or "外用薬" in r["test_name"]]

for test in shoulder_tests:
    print(f"\n{test['test_name']}")
    print(f"症状: {test['symptom']}")
    medicines = test['recommended_medicines']
    
    optimal_keywords = ["フェイタス", "バンテリン", "サロンパス"]
    second_gen_ingredients = ["フェルビナク", "インドメタシン", "ジクロフェナク"]
    found_optimal = False
    
    for i, med in enumerate(medicines[:3], 1):
        product_name = med.get('product_name', '')
        ingredients = med.get('ingredients', '')
        
        # 製品名による検出
        for keyword in optimal_keywords:
            if keyword in product_name:
                found_optimal = True
                print(f"  [改善成功] 最適解が推奨されています: {i}位 {product_name} (キーワード: {keyword})")
                break
        
        # 成分による検出
        if not found_optimal:
            for ingredient in second_gen_ingredients:
                if ingredient in str(ingredients):
                    found_optimal = True
                    print(f"  [改善成功] 第2世代鎮痛成分含有: {i}位 {product_name} (成分: {ingredient})")
                    break
        
        if found_optimal:
            break
    
    if not found_optimal:
        print(f"  [要改善] 最適解（フェイタス、バンテリン、サロンパス）は推奨されていません")
        print(f"  推奨された医薬品: {[m.get('product_name') for m in medicines[:3]]}")
        print(f"  成分確認:")
        for i, med in enumerate(medicines[:3], 1):
            print(f"    {i}. {med.get('product_name')}: {med.get('ingredients', '')[:100]}...")

# 改善点3: 乗り物酔い薬の最適解
print("\n\n【改善点3】乗り物酔い薬の最適解")
print("-"*80)

motion_sickness_tests = [r for r in results if "乗り物酔い" in r["test_name"]]

for test in motion_sickness_tests:
    print(f"\n{test['test_name']}")
    print(f"症状: {test['symptom']}")
    medicines = test['recommended_medicines']
    
    optimal_keywords = ["アネロン", "ニスキャップ", "キャップ"]
    found_optimal = False
    
    for i, med in enumerate(medicines[:3], 1):
        product_name = med.get('product_name', '')
        for keyword in optimal_keywords:
            if keyword in product_name:
                found_optimal = True
                if i == 1:
                    print(f"  [改善成功] 最適解が1位に推奨されています: {product_name} (キーワード: {keyword})")
                else:
                    print(f"  [部分的成功] 最適解が{i}位に推奨されています: {product_name} (キーワード: {keyword})")
                break
    
    if not found_optimal:
        print(f"  [要改善] 最適解（アネロン「ニスキャップ」）は推奨されていません")
        print(f"  推奨された医薬品: {[m.get('product_name') for m in medicines[:3]]}")

print("\n" + "="*80)
print("評価完了")
print("="*80)

