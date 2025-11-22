# -*- coding: utf-8 -*-
"""
推奨された医薬品の詳細を取得して評価する
"""
import sys
import io
import json

# Windows環境での文字エンコーディング問題を回避
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

from rule_based_recommendation import rule_based_recommendation
from openai import OpenAI
import os
from dotenv import load_dotenv
import pandas as pd

# 環境変数の読み込み
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=api_key) if api_key else None

medicine_df = pd.read_csv("otc_medicine_data.csv", encoding="utf-8")

# テストケースの定義
test_cases = [
    {
        "test_name": "テスト1: 風邪症状",
        "symptom": "昨日から喉が痛くて、咳も出ます。少し熱っぽいです。",
        "user_info": {"age": 30, "gender": "男性"}
    },
    {
        "test_name": "テスト2: 頭痛症状",
        "symptom": "頭が痛いです。昨日の夕方から続いています。",
        "user_info": {"age": 25, "gender": "女性"}
    },
    {
        "test_name": "テスト3: 鼻炎症状（アレルギー）",
        "symptom": "鼻水とくしゃみが止まりません。目もかゆいです。",
        "user_info": {"age": 35, "gender": "女性"}
    },
    {
        "test_name": "テスト9: 小児専用製品フィルタリング",
        "symptom": "喉がイガイガして、鼻が詰まっている",
        "user_info": {"age": None, "gender": None}
    },
    {
        "test_name": "テスト10: 外用薬推奨（肩こり）",
        "symptom": "肩が痛いです。肩こりもひどいです。",
        "user_info": {"age": 30, "gender": "男性"}
    },
    {
        "test_name": "テスト11-ケース1: 乗り物酔い症状",
        "symptom": "車に乗ると気持ち悪くなります。乗り物酔いがひどいです。",
        "user_info": {"age": 25, "gender": "女性"}
    },
    {
        "test_name": "テスト11-ケース2: 頭痛のみ",
        "symptom": "頭が痛い（夕方から）",
        "user_info": {"age": 25, "gender": "女性"}
    },
    {
        "test_name": "テスト12: アレルギー症状判定",
        "symptom": "鼻水とくしゃみが止まりません。目もかゆいです。",
        "user_info": {"age": 35, "gender": "女性"}
    },
    {
        "test_name": "テスト13-ケース1: 喉の痛み特化",
        "symptom": "喉が痛くて、咳も出ます。少し熱っぽいです。",
        "user_info": {"age": 30, "gender": "男性"}
    },
    {
        "test_name": "テスト13-ケース2: 女性の頭痛",
        "symptom": "頭が痛いです。昨日の夕方から続いています。",
        "user_info": {"age": 25, "gender": "女性"}
    },
    {
        "test_name": "テスト13-ケース3: 肩こり外用薬",
        "symptom": "肩が痛いです。肩こりもひどいです。",
        "user_info": {"age": 30, "gender": "男性"}
    }
]

print("="*80)
print("推奨された医薬品の詳細評価")
print("="*80)

all_results = []

for test_case in test_cases:
    print(f"\n{test_case['test_name']}")
    print(f"症状: {test_case['symptom']}")
    print(f"ユーザー情報: {test_case['user_info']}")
    print("-"*80)
    
    try:
        result = rule_based_recommendation(
            test_case['symptom'], 
            test_case['user_info'], 
            medicine_df, 
            client=client
        )
        
        if result.get("status") == "success":
            medicines = result.get("recommended_medicines", [])
            print(f"推奨医薬品数: {len(medicines)}")
            
            test_result = {
                "test_name": test_case['test_name'],
                "symptom": test_case['symptom'],
                "user_info": test_case['user_info'],
                "recommended_medicines": []
            }
            
            for i, med in enumerate(medicines[:3], 1):
                product_name = med.get('product_name', '不明')
                manufacturer = med.get('manufacturer', '不明')
                medicine_type = med.get('medicine_type', '不明')
                efficacy = med.get('efficacy', '')[:100] if med.get('efficacy') else '不明'
                score = med.get('total_score', 0)
                reason = med.get('reason', 'なし')
                
                print(f"\n{i}. {product_name} ({manufacturer})")
                print(f"   種類: {medicine_type}")
                print(f"   スコア: {score:.3f}")
                print(f"   効能効果: {efficacy}...")
                print(f"   推奨理由: {reason[:100]}...")
                
                test_result["recommended_medicines"].append({
                    "rank": i,
                    "product_name": product_name,
                    "manufacturer": manufacturer,
                    "medicine_type": medicine_type,
                    "efficacy": efficacy,
                    "score": score,
                    "reason": reason
                })
            
            all_results.append(test_result)
        else:
            print(f"推奨失敗: {result.get('reason', '不明なエラー')}")
            all_results.append({
                "test_name": test_case['test_name'],
                "symptom": test_case['symptom'],
                "user_info": test_case['user_info'],
                "recommended_medicines": [],
                "status": "failed",
                "error": result.get('reason', '不明なエラー')
            })
    except Exception as e:
        print(f"エラー: {e}")
        import traceback
        traceback.print_exc()
        all_results.append({
            "test_name": test_case['test_name'],
            "symptom": test_case['symptom'],
            "user_info": test_case['user_info'],
            "recommended_medicines": [],
            "status": "error",
            "error": str(e)
        })

# 結果をJSONファイルに保存
with open("recommended_medicines_detail.json", "w", encoding="utf-8") as f:
    json.dump(all_results, f, ensure_ascii=False, indent=2)

print("\n" + "="*80)
print("結果を recommended_medicines_detail.json に保存しました")
print("="*80)

