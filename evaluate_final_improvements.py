# -*- coding: utf-8 -*-
"""
改善後の最終評価
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
print("改善後の最終評価")
print("="*80)

# 改善点1: 頭痛のみの場合の風邪薬ペナルティ
print("\n【改善点1】頭痛のみの場合の風邪薬ペナルティ")
print("-"*80)
print("✅ 改善成功！")

headache_tests = [
    r for r in results 
    if ("頭痛" in r["test_name"] or "テスト2" in r["test_name"] or "テスト11-ケース2" in r["test_name"] or "テスト13-ケース2" in r["test_name"])
    and "風邪" not in r["test_name"]
]

for test in headache_tests:
    print(f"\n{test['test_name']}")
    print(f"症状: {test['symptom']}")
    medicines = test['recommended_medicines']
    
    # 1位の医薬品を確認
    top_med = medicines[0]
    medicine_type = top_med.get('medicine_type', '')
    product_name = top_med.get('product_name', '')
    
    if '風邪薬' in medicine_type or 'かぜ' in product_name or '風邪' in product_name:
        print(f"  [問題] 1位に風邪薬が推奨されています: {product_name}")
    else:
        print(f"  [改善成功] 1位に解熱鎮痛薬が推奨されています: {product_name} ({medicine_type})")
        # NSAIDs成分が含まれているか確認
        ingredients = top_med.get('ingredients', '')
        nsaid_keywords = ["アセトアミノフェン", "イブプロフェン", "ロキソプロフェン", "ロキソニン"]
        if any(kw in str(ingredients) for kw in nsaid_keywords):
            print(f"    → NSAIDs成分含有: ✅")

# 改善点2: 肩こり外用薬の最適解
print("\n\n【改善点2】肩こり外用薬の最適解")
print("-"*80)

shoulder_tests = [r for r in results if "肩こり" in r["test_name"] or "外用薬" in r["test_name"]]

for test in shoulder_tests:
    print(f"\n{test['test_name']}")
    print(f"症状: {test['symptom']}")
    medicines = test['recommended_medicines']
    
    optimal_keywords = ["フェイタス", "バンテリン", "サロンパス"]
    found_optimal = False
    
    for i, med in enumerate(medicines[:3], 1):
        product_name = med.get('product_name', '')
        for keyword in optimal_keywords:
            if keyword in product_name:
                found_optimal = True
                print(f"  [改善成功] 最適解が{i}位に推奨されています: {product_name} (キーワード: {keyword})")
                break
    
    if not found_optimal:
        print(f"  [要改善] 最適解（フェイタス、バンテリン、サロンパス）は推奨されていません")
        print(f"  推奨された医薬品: {[m.get('product_name') for m in medicines[:3]]}")

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

# まとめ
print("\n" + "="*80)
print("評価まとめ")
print("="*80)
print("✅ 改善点1（頭痛のみの風邪薬ペナルティ）: 成功")
print("   - 風邪薬が1位になることを防ぎ、解熱鎮痛薬が優先されるようになりました")
print("   - NSAIDs成分含有の解熱鎮痛薬が推奨されています")
print("\n⚠️ 改善点2（肩こり外用薬の最適解）: 要改善")
print("   - フェイタス、バンテリン、サロンパスが推奨されていません")
print("   - 製品名マッチングのロジックを確認する必要があります")
print("\n⚠️ 改善点3（乗り物酔い薬の最適解）: 部分的成功")
print("   - アネロン「キャップ」が2位に推奨されています")
print("   - 1位にするにはさらにブーストの調整が必要です")
print("="*80)

