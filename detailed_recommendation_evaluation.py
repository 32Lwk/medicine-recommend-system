# -*- coding: utf-8 -*-
"""
推奨された医薬品の詳細評価
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
print("推奨された医薬品の詳細評価")
print("="*80)

for test in results:
    print("\n" + "="*80)
    print(f"【{test['test_name']}】")
    print("="*80)
    print(f"症状: {test['symptom']}")
    print(f"ユーザー情報: 年齢={test['user_info'].get('age', '不明')}, 性別={test['user_info'].get('gender', '不明')}")
    print("-"*80)
    
    medicines = test['recommended_medicines']
    print(f"推奨医薬品数: {len(medicines)}")
    print()
    
    for i, med in enumerate(medicines, 1):
        print(f"{i}. {med.get('product_name', '不明')} ({med.get('manufacturer', '不明')})")
        print(f"   種類: {med.get('medicine_type', '不明')}")
        print(f"   分類: {med.get('classification', '不明')}")
        print(f"   効能効果: {med.get('efficacy', '不明')[:100]}...")
        
        # 成分情報があれば表示
        ingredients = med.get('ingredients', '')
        if ingredients:
            # 主要成分を抽出（最初の3つ程度）
            ingredient_list = str(ingredients).split('\n')[:3]
            main_ingredients = ', '.join([ing.strip() for ing in ingredient_list if ing.strip()])
            if main_ingredients:
                print(f"   主成分: {main_ingredients}")
        
        # 推奨理由
        reason = med.get('reason', '')
        if reason:
            print(f"   推奨理由: {reason[:200]}...")
        
        print()
    
    # 改善点の評価
    print("【評価】")
    
    # 改善点1: 頭痛のみの場合の風邪薬ペナルティ
    if "頭痛" in test['test_name'] or ("頭痛" in test['symptom'] and "風邪" not in test['test_name']):
        top_med = medicines[0]
        medicine_type = top_med.get('medicine_type', '')
        product_name = top_med.get('product_name', '')
        
        if '風邪薬' in medicine_type or 'かぜ' in product_name or '風邪' in product_name:
            print("  ❌ 問題: 1位に風邪薬が推奨されています（頭痛のみの場合、風邪薬は不適切）")
        else:
            print("  ✅ 適切: 1位に解熱鎮痛薬が推奨されています")
            # NSAIDs成分の確認
            ingredients = top_med.get('ingredients', '')
            nsaid_keywords = ["アセトアミノフェン", "イブプロフェン", "ロキソプロフェン", "ロキソニン"]
            if any(kw in str(ingredients) for kw in nsaid_keywords):
                print("     → NSAIDs成分含有の解熱鎮痛薬で、即効性が期待できます")
    
    # 改善点2: 肩こり外用薬の最適解
    if "肩こり" in test['test_name'] or "外用薬" in test['test_name'] or ("肩こり" in test['symptom'] and "外用" in str([m.get('medicine_type') for m in medicines])):
        optimal_keywords = ["フェイタス", "バンテリン", "サロンパス"]
        found_optimal = False
        
        for i, med in enumerate(medicines[:3], 1):
            product_name = med.get('product_name', '')
            for keyword in optimal_keywords:
                if keyword in product_name:
                    found_optimal = True
                    if i == 1:
                        print(f"  ✅ 最適解が1位に推奨されています: {product_name} (キーワード: {keyword})")
                    else:
                        print(f"  ⚠️ 最適解が{i}位に推奨されています: {product_name} (キーワード: {keyword})")
                    break
        
        if not found_optimal:
            print("  ❌ 最適解（フェイタス、バンテリン、サロンパス）は推奨されていません")
            print(f"     推奨された医薬品: {[m.get('product_name') for m in medicines[:3]]}")
    
    # 改善点3: 乗り物酔い薬の最適解
    if "乗り物酔い" in test['test_name'] or "乗り物酔い" in test['symptom']:
        optimal_keywords = ["アネロン", "ニスキャップ", "キャップ"]
        found_optimal = False
        
        for i, med in enumerate(medicines[:3], 1):
            product_name = med.get('product_name', '')
            for keyword in optimal_keywords:
                if keyword in product_name:
                    found_optimal = True
                    if i == 1:
                        print(f"  ✅ 最適解が1位に推奨されています: {product_name} (キーワード: {keyword})")
                    else:
                        print(f"  ⚠️ 最適解が{i}位に推奨されています: {product_name} (キーワード: {keyword})")
                    break
        
        if not found_optimal:
            print("  ❌ 最適解（アネロン「ニスキャップ」）は推奨されていません")
            print(f"     推奨された医薬品: {[m.get('product_name') for m in medicines[:3]]}")

print("\n" + "="*80)
print("評価完了")
print("="*80)

