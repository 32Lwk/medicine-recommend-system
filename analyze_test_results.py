# -*- coding: utf-8 -*-
"""
テスト結果を分析して、症状と推奨医薬品をまとめる
"""
import sys
import io
import subprocess

# Windows環境での文字エンコーディング問題を回避
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

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
    },
    {
        "test_name": "テスト: 若年層への中年向け漢方ペナルティ",
        "symptom": "頭が痛いです。昨日の夕方から続いています。",
        "user_info": {"age": 25, "gender": "女性"}
    },
    {
        "test_name": "テスト: 空入力のガード条件（空文字列）",
        "symptom": "",
        "user_info": {"age": 30, "gender": "男性"}
    },
    {
        "test_name": "テスト: 空入力のガード条件（空白のみ）",
        "symptom": "   ",
        "user_info": {"age": 30, "gender": "男性"}
    },
    {
        "test_name": "テスト: 空入力のガード条件（短い文字列）",
        "symptom": "ああ",
        "user_info": {"age": 30, "gender": "男性"}
    },
    {
        "test_name": "テスト: 空入力のガード条件（繰り返し文字）",
        "symptom": "あああああ",
        "user_info": {"age": 30, "gender": "男性"}
    },
    {
        "test_name": "テスト: 空入力のガード条件（医療キーワードなし）",
        "symptom": "こんにちは",
        "user_info": {"age": 30, "gender": "男性"}
    },
    {
        "test_name": "テスト: 当帰四逆加呉茱萸生姜湯の不適切推奨防止（頭痛のみ）",
        "symptom": "頭が痛いです。昨日の夕方から続いています。",
        "user_info": {"age": 25, "gender": "女性"}
    },
    {
        "test_name": "テスト: 当帰四逆加呉茱萸生姜湯の適切推奨（冷え性あり）",
        "symptom": "頭が痛くて、手足が冷えます。しもやけもできやすいです。",
        "user_info": {"age": 30, "gender": "女性"}
    },
    {
        "test_name": "テスト: シロップ剤の大人への推奨抑制",
        "symptom": "昨日から喉が痛くて、咳も出ます。少し熱っぽいです。",
        "user_info": {"age": 30, "gender": "男性"}
    },
    {
        "test_name": "テスト: ドライシロップの大人への推奨抑制",
        "symptom": "喉が痛くて、咳も出ます。少し熱っぽいです。",
        "user_info": {"age": 35, "gender": "男性"}
    }
]

from rule_based_recommendation import rule_based_recommendation
from openai import OpenAI
import os
from dotenv import load_dotenv
import pandas as pd

# 環境変数の読み込み
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=api_key) if api_key else None

try:
    medicine_df = pd.read_csv("otc_medicine_data.csv", encoding="utf-8")
    print("CSVファイルの読み込み成功")
except Exception as e:
    print(f"CSVファイルの読み込みエラー: {e}")
    sys.exit(1)

print("="*80)
print("テスト結果の分析: 症状と推奨医薬品のまとめ")
print("="*80)
sys.stdout.flush()

results_summary = []

for test_case in test_cases:
    print(f"\n{test_case['test_name']}")
    print(f"症状: {test_case['symptom']}")
    print(f"ユーザー情報: {test_case['user_info']}")
    sys.stdout.flush()
    
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
            
            recommended_names = []
            for i, med in enumerate(medicines[:3], 1):
                name = med.get('product_name', '不明')
                manufacturer = med.get('manufacturer', '不明')
                score = med.get('total_score', 0)
                medicine_type = med.get('medicine_type', '不明')
                recommended_names.append(f"{name} ({manufacturer})")
                print(f"  {i}. {name} ({manufacturer})")
                print(f"     スコア: {score:.3f}, 種類: {medicine_type}")
                
                # 若年層への中年向け漢方ペナルティの検証
                if "中年" in test_case['test_name']:
                    user_age = test_case['user_info'].get('age')
                    if user_age and user_age < 40:
                        # 釣藤散や中年以降向けの漢方を検出
                        if "釣藤散" in name or ("中年" in str(med.get('efficacy', '')) and "以降" in str(med.get('efficacy', ''))):
                            print(f"     ⚠️ 検証: {user_age}歳に対して中年向け漢方（{name}）が推奨されています")
                            print(f"     期待: ペナルティにより下位に配置されるべき")
                        elif i <= 3:
                            print(f"     ✅ 検証: 上位3位に中年向け漢方は含まれていません（ペナルティが機能している可能性）")
                
                # 当帰四逆加呉茱萸生姜湯の不適切推奨防止の検証
                if "当帰四逆" in test_case['test_name']:
                    if "当帰四逆加呉茱萸生姜湯" in name:
                        user_symptom = test_case['symptom']
                        has_cold_symptoms = any(kw in user_symptom for kw in ["冷え", "手足", "しもやけ", "冷え性"])
                        if "不適切推奨防止" in test_case['test_name']:
                            # 頭痛のみの場合、当帰四逆加呉茱萸生姜湯は推奨されるべきではない
                            if i <= 3:
                                print(f"     ⚠️ 検証: 頭痛のみの場合に当帰四逆加呉茱萸生姜湯が上位{i}位に推奨されています")
                                print(f"     期待: ペナルティにより下位に配置されるべき（冷え性の症状がないため）")
                        elif "適切推奨" in test_case['test_name']:
                            # 冷え性の症状がある場合、推奨されても良い
                            if has_cold_symptoms and i <= 3:
                                print(f"     ✅ 検証: 冷え性の症状がある場合に当帰四逆加呉茱萸生姜湯が推奨されています（適切）")
                
                # シロップ剤の大人への推奨抑制の検証
                if "シロップ" in test_case['test_name'] or "ドライシロップ" in test_case['test_name']:
                    user_age = test_case['user_info'].get('age')
                    if user_age is None or user_age >= 15:
                        if "シロップ" in name or "ドライシロップ" in name:
                            # 小児向けキーワードが含まれていない場合
                            pediatric_keywords = ["小児", "こども", "子供", "キッズ", "ジュニア", "ベビー"]
                            has_pediatric_keyword = any(kw in name for kw in pediatric_keywords)
                            if not has_pediatric_keyword and i <= 3:
                                print(f"     ⚠️ 検証: {user_age if user_age else '年齢未入力'}歳に対してシロップ剤（{name}）が上位{i}位に推奨されています")
                                print(f"     期待: ペナルティにより下位に配置されるべき")
                            elif has_pediatric_keyword:
                                print(f"     ✅ 検証: 小児向けキーワードが含まれているため除外されている可能性")
            
            results_summary.append({
                "test_name": test_case['test_name'],
                "symptom": test_case['symptom'],
                "user_info": test_case['user_info'],
                "recommended_medicines": recommended_names,
                "status": "success"
            })
        else:
            error_reason = result.get('reason', '不明なエラー')
            error_message = result.get('error_message', '')
            print(f"推奨失敗: {error_reason}")
            if error_message:
                print(f"エラーメッセージ: {error_message}")
            
            # 空入力のガード条件の検証
            if "空入力" in test_case['test_name'] or "ガード条件" in test_case['test_name']:
                if ("症状を入力してください" in error_reason or "症状を入力してください" in error_message or
                    "症状を詳しく入力してください" in error_reason or "症状を詳しく入力してください" in error_message):
                    print(f"  ✅ 検証: 空入力のガード条件が正常に機能しています")
                else:
                    print(f"  ⚠️ 警告: 空入力のガード条件が期待通りに動作していない可能性があります")
            
            results_summary.append({
                "test_name": test_case['test_name'],
                "symptom": test_case['symptom'],
                "user_info": test_case['user_info'],
                "recommended_medicines": [],
                "status": "failed",
                "error": error_reason
            })
    except Exception as e:
        print(f"エラー: {e}")
        results_summary.append({
            "test_name": test_case['test_name'],
            "symptom": test_case['symptom'],
            "user_info": test_case['user_info'],
            "recommended_medicines": [],
            "status": "error",
            "error": str(e)
        })

print("\n" + "="*80)
print("まとめ")
print("="*80)
sys.stdout.flush()

for result in results_summary:
    print(f"\n{result['test_name']}")
    print(f"  症状: {result['symptom']}")
    print(f"  推奨医薬品:")
    if result['recommended_medicines']:
        for i, med in enumerate(result['recommended_medicines'], 1):
            print(f"    {i}. {med}")
    else:
        print(f"    なし（{result.get('status', 'unknown')}）")
