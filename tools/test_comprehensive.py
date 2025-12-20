"""
医薬品推奨システム - 包括的テストスイート
統合されたテストファイル（全機能をカバー）
"""

import sys
import os
import io

# Windows環境での文字エンコーディング問題を回避
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# 現在のディレクトリをパスに追加
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from medicine_logic import (
    rule_based_medicine_recommendation, 
    analyze_symptoms_and_medicine_type,
    comprehensive_medicine_recommendation,
    client
)

def print_result(result, test_name):
    """テスト結果の表示"""
    print(f"\n{'='*80}")
    print(f"結果: {test_name}")
    print(f"{'='*80}")
    print(f"ステータス: {result.get('status')}")
    
    if result.get('status') == 'success':
        medicines = result.get('recommended_medicines', [])
        print(f"推奨医薬品数: {len(medicines)}")
        
        for i, med in enumerate(medicines[:3], 1):
            print(f"\n{i}. {med.get('product_name')} ({med.get('manufacturer')})")
            print(f"   スコア: {med.get('score', 0):.3f}")
            print(f"   推奨理由: {med.get('reason', 'なし')}")
            print(f"   効能効果: {med.get('efficacy', '')[:100]}...")
        
        if result.get('usage_notes'):
            print(f"\n使用上の注意: {result.get('usage_notes')}")
    else:
        print(f"エラー: {result.get('error', '不明なエラー')}")

def test_rule_based_cold():
    """テスト1: 風邪症状（ルールベース）"""
    print("\n" + "="*80)
    print("テスト1: 風邪症状（ルールベース推奨）")
    print("="*80)
    
    user_text = "昨日から喉が痛くて、咳も出ます。少し熱っぽいです。"
    user_info = {
        "age": 30,
        "gender": "男性",
        "pregnant": False,
        "breastfeeding": False,
        "current_medications": [],
        "allergies": []
    }
    
    result = rule_based_medicine_recommendation(user_text, user_info, client)
    print_result(result, "風邪症状")

def test_rule_based_headache():
    """テスト2: 頭痛症状（ルールベース）"""
    print("\n" + "="*80)
    print("テスト2: 頭痛症状（ルールベース推奨）")
    print("="*80)
    
    user_text = "頭が痛いです。昨日の夕方から続いています。"
    user_info = {
        "age": 25,
        "gender": "女性",
        "pregnant": False,
        "breastfeeding": False,
        "current_medications": [],
        "allergies": []
    }
    
    result = rule_based_medicine_recommendation(user_text, user_info, client)
    print_result(result, "頭痛症状")

def test_rule_based_nasal():
    """テスト3: 鼻炎症状（ルールベース）"""
    print("\n" + "="*80)
    print("テスト3: 鼻炎症状（ルールベース推奨）")
    print("="*80)
    
    user_text = "鼻水とくしゃみが止まりません。目もかゆいです。"
    user_info = {
        "age": 35,
        "gender": "女性",
        "pregnant": False,
        "breastfeeding": False,
        "current_medications": [],
        "allergies": []
    }
    
    result = rule_based_medicine_recommendation(user_text, user_info, client)
    print_result(result, "鼻炎症状")

def test_hybrid_medicine_type():
    """テスト4: 医薬品種類判定（ハイブリッド）"""
    print("\n" + "="*80)
    print("テスト4: 医薬品種類判定（ハイブリッドシステム）")
    print("="*80)
    
    test_cases = [
        "頭が痛いです",
        "喉が痛くて咳が出ます", 
        "鼻水とくしゃみが止まりません",
        "胃が痛いです"
    ]
    
    for case in test_cases:
        print(f"\n入力: {case}")
        try:
            result = analyze_symptoms_and_medicine_type(case, client)
            medicine_type = result.get('medicine_type', '不明')
            print(f"  → 医薬品の種類: {medicine_type}")
            
            # ルールベース対象かどうか
            target_types = ['風邪薬', '解熱鎮痛薬', '鼻炎用薬']
            if medicine_type in target_types:
                print(f"  → アルゴリズム: ルールベース（安全性重視）")
            else:
                print(f"  → アルゴリズム: AI推奨（柔軟性重視）")
        except Exception as e:
            print(f"  → エラー: {e}")

def test_missing_attributes():
    """テスト5: 属性不足時の質問機能"""
    print("\n" + "="*80)
    print("テスト5: 属性不足時の質問機能")
    print("="*80)
    
    user_text = "頭が痛いです。"
    user_info = {
        "age": None,           # 不足
        "gender": None,        # 不足
        "pregnant": None,      # 不足
        "breastfeeding": None, # 不足
        "current_medications": [],
        "allergies": []
    }
    
    result = rule_based_medicine_recommendation(user_text, user_info, client)
    print_result(result, "属性不足時")

def test_safety_checks():
    """テスト6: 安全性チェック"""
    print("\n" + "="*80)
    print("テスト6: 安全性チェック")
    print("="*80)
    
    # 年齢制限テスト
    user_text = "頭が痛いです。"
    user_info = {
        "age": 5,  # 7歳未満
        "gender": "男性",
        "pregnant": False,
        "breastfeeding": False,
        "current_medications": [],
        "allergies": []
    }
    
    result = rule_based_medicine_recommendation(user_text, user_info, client)
    print_result(result, "年齢制限チェック（5歳）")
    
    # 妊娠中テスト
    user_info["age"] = 30
    user_info["pregnant"] = True
    
    result = rule_based_medicine_recommendation(user_text, user_info, client)
    print_result(result, "妊娠中チェック")

def test_red_flag_symptoms():
    """テスト7: Red Flag症状検出"""
    print("\n" + "="*80)
    print("テスト7: Red Flag症状検出")
    print("="*80)
    
    user_text = "39度の高熱が3日続いています。呼吸も苦しいです。"
    user_info = {
        "age": 30,
        "gender": "男性",
        "pregnant": False,
        "breastfeeding": False,
        "current_medications": [],
        "allergies": []
    }
    
    result = rule_based_medicine_recommendation(user_text, user_info, client)
    print_result(result, "Red Flag症状")

def test_comprehensive_system():
    """テスト8: 包括的システムテスト"""
    print("\n" + "="*80)
    print("テスト8: 包括的システムテスト")
    print("="*80)
    
    user_text = "喉が痛くて咳が出ます。少し熱もあります。"
    user_info = {
        "age": 28,
        "gender": "女性",
        "pregnant": False,
        "breastfeeding": False,
        "current_medications": [],
        "allergies": []
    }
    
    result = comprehensive_medicine_recommendation(user_text, user_info, client)
    print_result(result, "包括的システム")

def test_pediatric_filtering():
    """テスト9: 小児専用製品フィルタリング（年齢未入力時）"""
    print("\n" + "="*80)
    print("テスト9: 小児専用製品フィルタリング（年齢未入力時）")
    print("="*80)
    
    user_text = "喉がイガイガして、鼻が詰まっている"
    user_info = {
        "age": None,  # 年齢未入力
        "gender": None,
        "pregnant": False,
        "breastfeeding": False,
        "current_medications": [],
        "allergies": []
    }
    
    result = rule_based_medicine_recommendation(user_text, user_info, client)
    print_result(result, "小児専用製品フィルタリング")
    
    # 小児専用製品が除外されているか確認
    medicines = result.get('recommended_medicines', [])
    pediatric_products = [m for m in medicines if '小児用' in m.get('product_name', '') or '小児' in m.get('product_name', '')]
    
    if pediatric_products:
        print(f"\n[警告] 小児専用製品が推奨されています: {[p.get('product_name') for p in pediatric_products]}")
    else:
        print("\n[OK] 小児専用製品は正しく除外されています")

def test_topical_medicine_recommendation():
    """テスト10: 外用薬推奨（肩こり・筋肉痛）"""
    print("\n" + "="*80)
    print("テスト10: 外用薬推奨（肩こり・筋肉痛）")
    print("="*80)
    
    # より明確な症状表現を使用
    user_text = "肩が痛いです。肩こりもひどいです。"
    user_info = {
        "age": 30,
        "gender": "男性",
        "pregnant": False,
        "breastfeeding": False,
        "current_medications": [],
        "allergies": []
    }
    
    result = rule_based_medicine_recommendation(user_text, user_info, client)
    print_result(result, "外用薬推奨")
    
    # ステータスを確認
    if result.get('status') != 'success':
        print(f"\n[警告] 推奨が失敗しました。ステータス: {result.get('status')}")
        print(f"理由: {result.get('reason', '不明')}")
        return
    
    # 外用薬が推奨されているか確認
    medicines = result.get('recommended_medicines', [])
    topical_medicines = [m for m in medicines if '外用薬（皮膚）' in str(m.get('medicine_type', ''))]
    
    if topical_medicines:
        print(f"\n[OK] 外用薬が推奨されています: {[m.get('product_name') for m in topical_medicines]}")
    else:
        print("\n[警告] 外用薬が推奨されていません（内服薬のみの可能性）")
        print(f"推奨された医薬品の種類: {[m.get('medicine_type') for m in medicines]}")
    
    # 内服薬も推奨されているか確認
    oral_medicines = [m for m in medicines if '解熱鎮痛薬' in str(m.get('medicine_type', '')) or '筋肉痛' in str(m.get('medicine_type', ''))]
    if oral_medicines:
        print(f"[OK] 内服薬も推奨されています: {[m.get('product_name') for m in oral_medicines]}")

def test_motion_sickness_medicine_recommendation():
    """テスト11: 乗り物酔い薬の推奨テスト（改善後）"""
    print("\n" + "="*80)
    print("テスト11: 乗り物酔い薬の推奨テスト（改善後）")
    print("="*80)
    
    from rule_based_recommendation import rule_based_recommendation
    from openai import OpenAI
    import os
    from dotenv import load_dotenv
    import pandas as pd
    
    # 環境変数の読み込み
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    client = OpenAI(api_key=api_key) if api_key else None
    
    # テストケース1: 乗り物酔いの症状がある場合 → 乗り物酔い薬が推奨されるべき
    print("\n[ケース1] 乗り物酔い症状がある場合")
    user_text = "車に乗ると気持ち悪くなります。乗り物酔いがひどいです。"
    user_info = {"age": 25, "gender": "女性"}
    
    try:
        medicine_df = pd.read_csv("otc_medicine_data.csv", encoding="utf-8")
        result = rule_based_recommendation(user_text, user_info, medicine_df, client=client)
        
        if result.get("status") == "success":
            medicines = result.get("recommended_medicines", [])
            motion_sickness_medicines = [
                m for m in medicines 
                if any(kw in str(m.get('product_name', '')).lower() 
                       for kw in ["酔い", "めまい", "乗り物", "鎮暈", "トラベルミン", "トリブラ", "アネロン", "エアミット", "センパア", "レジャール", "トラベロップ"])
            ]
            
            if motion_sickness_medicines:
                print(f"[OK] 乗り物酔い薬が推奨されています: {[m.get('product_name') for m in motion_sickness_medicines[:3]]}")
            else:
                print(f"[WARNING] 乗り物酔い薬が推奨されていません。推奨された医薬品: {[m.get('product_name') for m in medicines[:3]]}")
        else:
            print(f"[ERROR] 推奨に失敗しました: {result.get('reason', '不明なエラー')}")
    except Exception as e:
        print(f"[ERROR] テスト実行中にエラー: {e}")
        import traceback
        traceback.print_exc()
    
    # テストケース2: 頭痛のみの場合 → 乗り物酔い薬が除外されるべき
    print("\n[ケース2] 頭痛のみの場合（乗り物酔い薬は除外されるべき）")
    user_text = "頭が痛い（夕方から）"
    user_info = {"age": 25, "gender": "女性"}
    
    try:
        result = rule_based_recommendation(user_text, user_info, medicine_df, client=client)
        
        if result.get("status") == "success":
            medicines = result.get("recommended_medicines", [])
            motion_sickness_medicines = [
                m for m in medicines 
                if any(kw in str(m.get('product_name', '')).lower() 
                       for kw in ["酔い", "めまい", "乗り物", "鎮暈", "トラベルミン", "トリブラ", "アネロン", "エアミット", "センパア", "レジャール", "トラベロップ"])
            ]
            
            if not motion_sickness_medicines:
                print(f"[OK] 頭痛のみの場合、乗り物酔い薬は除外されています。推奨された医薬品: {[m.get('product_name') for m in medicines[:3]]}")
            else:
                print(f"[ERROR] 頭痛のみの場合でも乗り物酔い薬が推奨されています: {[m.get('product_name') for m in motion_sickness_medicines]}")
        else:
            print(f"[ERROR] 推奨に失敗しました: {result.get('reason', '不明なエラー')}")
    except Exception as e:
        print(f"[ERROR] テスト実行中にエラー: {e}")
        import traceback
        traceback.print_exc()

def test_allergy_symptom_detection():
    """テスト12: アレルギー症状判定の強化テスト"""
    print("\n" + "="*80)
    print("テスト12: アレルギー症状判定の強化テスト")
    print("="*80)
    
    from rule_based_recommendation import rule_based_recommendation
    from openai import OpenAI
    import os
    from dotenv import load_dotenv
    import pandas as pd
    
    # 環境変数の読み込み
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    client = OpenAI(api_key=api_key) if api_key else None
    
    # テストケース: アレルギー症状（目のかゆみ + くしゃみ/鼻水）がある場合
    print("\n[ケース] アレルギー症状（目のかゆみ + くしゃみ + 鼻水）がある場合")
    user_text = "鼻水とくしゃみが止まりません。目もかゆいです。"
    user_info = {"age": 35, "gender": "女性"}
    
    try:
        medicine_df = pd.read_csv("otc_medicine_data.csv", encoding="utf-8")
        result = rule_based_recommendation(user_text, user_info, medicine_df, client=client)
        
        if result.get("status") == "success":
            medicines = result.get("recommended_medicines", [])
            nlu_result = result.get("nlu_result", {})
            detected_symptoms = [s.get("name", "") for s in nlu_result.get("symptoms", [])]
            
            print(f"[DEBUG] NLUで検出された症状: {detected_symptoms}")
            
            # 鼻炎用薬（抗アレルギー薬）を検出
            allergy_medicines = [
                m for m in medicines 
                if '鼻炎用薬' in str(m.get('medicine_type', '')) or 
                   any(kw in str(m.get('product_name', '')).lower() 
                       for kw in ["アレグラ", "アレジオン", "アルガード", "抗アレルギー"])
            ]
            
            # 風邪薬を検出
            cold_medicines = [
                m for m in medicines 
                if '風邪薬' in str(m.get('medicine_type', ''))
            ]
            
            print(f"[DEBUG] 推奨された医薬品の種類: {[m.get('medicine_type') for m in medicines[:5]]}")
            print(f"[DEBUG] 鼻炎用薬数: {len(allergy_medicines)}, 風邪薬数: {len(cold_medicines)}")
            
            if allergy_medicines:
                print(f"[OK] 鼻炎用薬（抗アレルギー薬）が推奨されています: {[m.get('product_name') for m in allergy_medicines[:3]]}")
            else:
                print(f"[WARNING] 鼻炎用薬が推奨されていません。推奨された医薬品: {[m.get('product_name') for m in medicines[:3]]}")
            
            # 鼻炎用薬が風邪薬より上位に来ているか確認
            if allergy_medicines and cold_medicines:
                allergy_ranks = [medicines.index(m) for m in allergy_medicines]
                cold_ranks = [medicines.index(m) for m in cold_medicines]
                if min(allergy_ranks) < min(cold_ranks):
                    print(f"[OK] 鼻炎用薬が風邪薬より上位に推奨されています（鼻炎用薬: {min(allergy_ranks)+1}位、風邪薬: {min(cold_ranks)+1}位）")
                else:
                    print(f"[WARNING] 鼻炎用薬が風邪薬より下位に推奨されています（鼻炎用薬: {min(allergy_ranks)+1}位、風邪薬: {min(cold_ranks)+1}位）")
            elif allergy_medicines:
                print(f"[OK] 鼻炎用薬のみが推奨されています（風邪薬は推奨されていません）")
        else:
            print(f"[ERROR] 推奨に失敗しました: {result.get('reason', '不明なエラー')}")
    except Exception as e:
        print(f"[ERROR] テスト実行中にエラー: {e}")
        import traceback
        traceback.print_exc()

def test_symptom_specific_boost():
    """テスト13: 症状特化型ブーストの適用テスト"""
    print("\n" + "="*80)
    print("テスト13: 症状特化型ブーストの適用テスト")
    print("="*80)
    
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
    
    # テストケース1: 喉の痛み特化医薬品のブースト
    print("\n[ケース1] 喉の痛み特化医薬品のブースト")
    user_text = "喉が痛くて、咳も出ます。少し熱っぽいです。"
    user_info = {"age": 30, "gender": "男性"}
    
    try:
        result = rule_based_recommendation(user_text, user_info, medicine_df, client=client)
        
        if result.get("status") == "success":
            medicines = result.get("recommended_medicines", [])
            # 部分一致も含めて検出（例: "ベンザブロックL" や "ルルアタックEX" など）
            throat_specific = [
                m for m in medicines 
                if any(kw.upper() in str(m.get('product_name', '')).upper() 
                       for kw in ["ベンザブロック", "ルルアタック", "トラネキサム"])
            ]
            
            print(f"[DEBUG] 推奨された医薬品: {[m.get('product_name') for m in medicines[:5]]}")
            
            # 候補全体からベンザブロック/ルルアタックを検索（スコアも表示）
            all_throat_specific = []
            for m in medicines:
                product_name = str(m.get('product_name', '')).upper()
                if any(kw.upper() in product_name for kw in ["ベンザブロック", "ルルアタック", "トラネキサム"]):
                    all_throat_specific.append((m.get('product_name'), m.get('total_score', 0)))
            
            if all_throat_specific:
                print(f"[DEBUG] 候補内の喉の痛み特化医薬品: {all_throat_specific}")
            
            if throat_specific:
                print(f"[OK] 喉の痛み特化医薬品が推奨されています: {[m.get('product_name') for m in throat_specific[:3]]}")
            else:
                print(f"[INFO] 喉の痛み特化医薬品は推奨されていません（一般的な風邪薬が推奨されています）")
                if all_throat_specific:
                    print(f"[DEBUG] 候補には含まれていますが、スコアが低い可能性があります: {all_throat_specific}")
                else:
                    print(f"[DEBUG] データベースにベンザブロック/ルルアタックが存在するか確認が必要です")
        else:
            print(f"[ERROR] 推奨に失敗しました: {result.get('reason', '不明なエラー')}")
    except Exception as e:
        print(f"[ERROR] テスト実行中にエラー: {e}")
        import traceback
        traceback.print_exc()
    
    # テストケース2: 女性の頭痛用（胃に優しい）医薬品のブースト
    print("\n[ケース2] 女性の頭痛用（胃に優しい）医薬品のブースト")
    user_text = "頭が痛いです。昨日の夕方から続いています。"
    user_info = {"age": 25, "gender": "女性"}
    
    try:
        result = rule_based_recommendation(user_text, user_info, medicine_df, client=client)
        
        if result.get("status") == "success":
            medicines = result.get("recommended_medicines", [])
            stomach_friendly = [
                m for m in medicines 
                if any(kw in (str(m.get('product_name', '')) + str(m.get('efficacy', ''))).lower() 
                       for kw in ["イブクイック", "バファリン", "酸化マグネシウム"])
            ]
            
            if stomach_friendly:
                print(f"[OK] 胃に優しい医薬品が推奨されています: {[m.get('product_name') for m in stomach_friendly[:3]]}")
            else:
                print(f"[INFO] 胃に優しい医薬品は推奨されていません（一般的な解熱鎮痛薬が推奨されています）")
        else:
            print(f"[ERROR] 推奨に失敗しました: {result.get('reason', '不明なエラー')}")
    except Exception as e:
        print(f"[ERROR] テスト実行中にエラー: {e}")
        import traceback
        traceback.print_exc()
    
    # テストケース3: 肩こり外用薬（テープ・パップ）のブースト
    print("\n[ケース3] 肩こり外用薬（テープ・パップ）のブースト")
    user_text = "肩が痛いです。肩こりもひどいです。"
    user_info = {"age": 30, "gender": "男性"}
    
    try:
        result = rule_based_recommendation(user_text, user_info, medicine_df, client=client)
        
        if result.get("status") == "success":
            medicines = result.get("recommended_medicines", [])
            topical_medicines = [
                m for m in medicines 
                if '外用薬（皮膚）' in str(m.get('medicine_type', '')) and
                   any(kw in str(m.get('product_name', '')) 
                       for kw in ["ロキソニン", "サロンパス", "バンテリン", "テープ", "パップ"])
            ]
            
            if topical_medicines:
                print(f"[OK] 外用薬（テープ・パップ）が推奨されています: {[m.get('product_name') for m in topical_medicines[:3]]}")
            else:
                print(f"[INFO] 特定の外用薬（テープ・パップ）は推奨されていません（一般的な外用薬が推奨されています）")
        else:
            print(f"[ERROR] 推奨に失敗しました: {result.get('reason', '不明なエラー')}")
    except Exception as e:
        print(f"[ERROR] テスト実行中にエラー: {e}")
        import traceback
        traceback.print_exc()

def test_drug_interaction_filtering():
    """テスト14: 医薬品相互作用フィルタリング"""
    print("\n" + "="*80)
    print("テスト14: 医薬品相互作用フィルタリング")
    print("="*80)
    
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
    
    # テストケース: 現在服用中の薬（アスピリン）がある場合
    print("\n[ケース] 現在アスピリンを服用中で、頭痛がある場合")
    user_text = "頭が痛いです。"
    user_info = {
        "age": 30,
        "gender": "男性",
        "current_medications": ["アスピリン", "アセチルサリチル酸"],
        "allergies": []
    }
    
    try:
        result = rule_based_recommendation(user_text, user_info, medicine_df, client=client)
        
        if result.get("status") == "success":
            medicines = result.get("recommended_medicines", [])
            
            # アスピリン含有製品が除外されているか確認
            aspirin_products = [
                m for m in medicines 
                if any(kw.lower() in str(m.get('ingredients', '') + str(m.get('product_name', ''))).lower()
                       for kw in ["アスピリン", "アセチルサリチル酸", "ASA"])
            ]
            
            if aspirin_products:
                print(f"[WARNING] アスピリン含有製品が推奨されています: {[m.get('product_name') for m in aspirin_products]}")
                print(f"[INFO] 相互作用チェックが機能していない可能性があります")
            else:
                print(f"[OK] アスピリン含有製品は正しく除外されています")
                print(f"[OK] 推奨された医薬品数: {len(medicines)}")
                if medicines:
                    print(f"[OK] 推奨された医薬品: {[m.get('product_name') for m in medicines[:3]]}")
        else:
            print(f"[ERROR] 推奨に失敗しました: {result.get('reason', '不明なエラー')}")
    except Exception as e:
        print(f"[ERROR] テスト実行中にエラー: {e}")
        import traceback
        traceback.print_exc()

def test_allergy_filtering():
    """テスト15: アレルギー情報に基づくフィルタリング"""
    print("\n" + "="*80)
    print("テスト15: アレルギー情報に基づくフィルタリング")
    print("="*80)
    
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
    
    # テストケース: イブプロフェンアレルギーがある場合
    print("\n[ケース] イブプロフェンアレルギーがある場合、頭痛がある場合")
    user_text = "頭が痛いです。"
    user_info = {
        "age": 30,
        "gender": "女性",
        "current_medications": [],
        "allergies": ["イブプロフェン", "イブ"]
    }
    
    try:
        result = rule_based_recommendation(user_text, user_info, medicine_df, client=client)
        
        if result.get("status") == "success":
            medicines = result.get("recommended_medicines", [])
            
            # イブプロフェン含有製品が除外されているか確認
            ibuprofen_products = [
                m for m in medicines 
                if "イブプロフェン" in str(m.get('ingredients', '')).upper() or
                   "イブ" in str(m.get('ingredients', '')).upper()
            ]
            
            if ibuprofen_products:
                print(f"[ERROR] イブプロフェン含有製品が推奨されています: {[m.get('product_name') for m in ibuprofen_products]}")
                print(f"[ERROR] アレルギーチェックが機能していません")
            else:
                print(f"[OK] イブプロフェン含有製品は正しく除外されています")
                print(f"[OK] 推奨された医薬品数: {len(medicines)}")
                if medicines:
                    print(f"[OK] 推奨された医薬品: {[m.get('product_name') for m in medicines[:3]]}")
                    # アセトアミノフェン含有製品が推奨されているか確認
                    acetaminophen_products = [
                        m for m in medicines 
                        if "アセトアミノフェン" in str(m.get('ingredients', ''))
                    ]
                    if acetaminophen_products:
                        print(f"[OK] アセトアミノフェン含有製品が推奨されています（イブプロフェンの代替として適切）")
        else:
            print(f"[ERROR] 推奨に失敗しました: {result.get('reason', '不明なエラー')}")
    except Exception as e:
        print(f"[ERROR] テスト実行中にエラー: {e}")
        import traceback
        traceback.print_exc()

def test_breastfeeding_safety():
    """テスト16: 授乳中の安全性チェック"""
    print("\n" + "="*80)
    print("テスト16: 授乳中の安全性チェック")
    print("="*80)
    
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
    
    # テストケース: 授乳中の母親が頭痛を訴える場合
    print("\n[ケース] 授乳中の母親が頭痛を訴える場合")
    user_text = "頭が痛いです。"
    user_info = {
        "age": 28,
        "gender": "女性",
        "pregnant": False,
        "breastfeeding": True,
        "current_medications": [],
        "allergies": []
    }
    
    try:
        result = rule_based_recommendation(user_text, user_info, medicine_df, client=client)
        
        if result.get("status") == "success":
            medicines = result.get("recommended_medicines", [])
            
            # 授乳中に安全な医薬品が推奨されているか確認
            # アセトアミノフェンは授乳中に比較的安全
            safe_medicines = [
                m for m in medicines 
                if "アセトアミノフェン" in str(m.get('ingredients', ''))
            ]
            
            print(f"[DEBUG] 推奨された医薬品数: {len(medicines)}")
            if medicines:
                print(f"[DEBUG] 推奨された医薬品: {[m.get('product_name') for m in medicines[:3]]}")
            
            if safe_medicines:
                print(f"[OK] 授乳中に比較的安全なアセトアミノフェン含有製品が推奨されています: {[m.get('product_name') for m in safe_medicines[:3]]}")
            else:
                print(f"[INFO] アセトアミノフェン含有製品が推奨されていません（他の成分が推奨されている可能性があります）")
            
            # エスカレーションが必要な場合
            if result.get("usage_notes") and "授乳" in result.get("usage_notes", ""):
                print(f"[OK] 授乳中の注意喚起が表示されています")
        elif result.get("status") == "escalation_required":
            print(f"[OK] エスカレーションが必要と判定されました（授乳中の安全性のため）")
        else:
            print(f"[ERROR] 推奨に失敗しました: {result.get('reason', '不明なエラー')}")
    except Exception as e:
        print(f"[ERROR] テスト実行中にエラー: {e}")
        import traceback
        traceback.print_exc()

def test_pediatric_recommendation():
    """テスト17: 小児向け推奨テスト"""
    print("\n" + "="*80)
    print("テスト17: 小児向け推奨テスト")
    print("="*80)
    
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
    
    # テストケース1: 10歳の子供が風邪症状を訴える場合
    print("\n[ケース1] 10歳の子供が風邪症状を訴える場合")
    user_text = "喉が痛くて咳が出ます。"
    user_info = {
        "age": 10,
        "gender": "男性",
        "pregnant": False,
        "breastfeeding": False,
        "current_medications": [],
        "allergies": []
    }
    
    try:
        result = rule_based_recommendation(user_text, user_info, medicine_df, client=client)
        
        if result.get("status") == "success":
            medicines = result.get("recommended_medicines", [])
            
            # 年齢制限を満たす医薬品が推奨されているか確認
            age_restricted = [
                m for m in medicines 
                if m.get('age_restriction') is not None and m.get('age_restriction', 15) > 10
            ]
            
            if age_restricted:
                print(f"[ERROR] 年齢制限に適合しない医薬品が推奨されています: {[m.get('product_name') for m in age_restricted]}")
            else:
                print(f"[OK] 年齢制限に適合する医薬品のみが推奨されています")
                print(f"[OK] 推奨された医薬品数: {len(medicines)}")
                if medicines:
                    print(f"[OK] 推奨された医薬品: {[m.get('product_name') for m in medicines[:3]]}")
        elif result.get("status") == "escalation_required":
            print(f"[OK] エスカレーションが必要と判定されました（小児の安全性のため）")
        else:
            print(f"[ERROR] 推奨に失敗しました: {result.get('reason', '不明なエラー')}")
    except Exception as e:
        print(f"[ERROR] テスト実行中にエラー: {e}")
        import traceback
        traceback.print_exc()

def test_elderly_recommendation():
    """テスト18: 高齢者向け推奨テスト"""
    print("\n" + "="*80)
    print("テスト18: 高齢者向け推奨テスト")
    print("="*80)
    
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
    
    # テストケース: 75歳の高齢者が頭痛を訴える場合
    print("\n[ケース] 75歳の高齢者が頭痛を訴える場合")
    user_text = "頭が痛いです。"
    user_info = {
        "age": 75,
        "gender": "男性",
        "pregnant": False,
        "breastfeeding": False,
        "current_medications": [],
        "allergies": []
    }
    
    try:
        result = rule_based_recommendation(user_text, user_info, medicine_df, client=client)
        
        if result.get("status") == "success":
            medicines = result.get("recommended_medicines", [])
            
            # 高齢者に比較的安全な医薬品が推奨されているか確認
            # アセトアミノフェンは高齢者に比較的安全
            safe_medicines = [
                m for m in medicines 
                if "アセトアミノフェン" in str(m.get('ingredients', ''))
            ]
            
            print(f"[DEBUG] 推奨された医薬品数: {len(medicines)}")
            if medicines:
                print(f"[DEBUG] 推奨された医薬品: {[m.get('product_name') for m in medicines[:3]]}")
            
            if safe_medicines:
                print(f"[OK] 高齢者に比較的安全なアセトアミノフェン含有製品が推奨されています")
            
            # 高齢者向けの注意喚起があるか確認
            if result.get("usage_notes") and ("高齢" in result.get("usage_notes", "") or "年齢" in result.get("usage_notes", "")):
                print(f"[OK] 高齢者向けの注意喚起が表示されています")
        elif result.get("status") == "escalation_required":
            print(f"[OK] エスカレーションが必要と判定されました（高齢者の安全性のため）")
        else:
            print(f"[ERROR] 推奨に失敗しました: {result.get('reason', '不明なエラー')}")
    except Exception as e:
        print(f"[ERROR] テスト実行中にエラー: {e}")
        import traceback
        traceback.print_exc()

def test_complex_symptom_combination():
    """テスト19: 複数症状の組み合わせテスト"""
    print("\n" + "="*80)
    print("テスト19: 複数症状の組み合わせテスト")
    print("="*80)
    
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
    
    # テストケース: 複数の症状が組み合わさっている場合
    print("\n[ケース] 発熱、頭痛、鼻水、のどの痛みが同時にある場合")
    user_text = "熱があって頭も痛いです。鼻水も出て、のども痛いです。"
    user_info = {
        "age": 30,
        "gender": "女性",
        "pregnant": False,
        "breastfeeding": False,
        "current_medications": [],
        "allergies": []
    }
    
    try:
        result = rule_based_recommendation(user_text, user_info, medicine_df, client=client)
        
        if result.get("status") == "success":
            medicines = result.get("recommended_medicines", [])
            
            # 複数の症状に対応する医薬品が推奨されているか確認
            comprehensive_medicines = [
                m for m in medicines 
                if any(symptom in str(m.get('efficacy', ''))
                       for symptom in ["発熱", "頭痛", "鼻水", "のどの痛み", "喉の痛み"])
            ]
            
            print(f"[DEBUG] 推奨された医薬品数: {len(medicines)}")
            if medicines:
                print(f"[DEBUG] 推奨された医薬品: {[m.get('product_name') for m in medicines[:3]]}")
                print(f"[DEBUG] 医薬品の効能: {[m.get('efficacy', '')[:50] for m in medicines[:3]]}")
            
            if comprehensive_medicines:
                print(f"[OK] 複数の症状に対応する包括的な医薬品が推奨されています")
            else:
                print(f"[INFO] 特定の症状に特化した医薬品が推奨されている可能性があります")
        else:
            print(f"[ERROR] 推奨に失敗しました: {result.get('reason', '不明なエラー')}")
    except Exception as e:
        print(f"[ERROR] テスト実行中にエラー: {e}")
        import traceback
        traceback.print_exc()

def test_optimal_medicine_selection():
    """テスト20: 最適な医薬品が推奨されているかの検証"""
    print("\n" + "="*80)
    print("テスト20: 最適な医薬品が推奨されているかの検証")
    print("="*80)
    
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
    
    # テストケース: のどの痛み特化症状の場合
    print("\n[ケース] のどの痛みが主症状の場合、最適な医薬品が推奨されているか")
    user_text = "のどがとても痛いです。"
    user_info = {
        "age": 30,
        "gender": "男性",
        "pregnant": False,
        "breastfeeding": False,
        "current_medications": [],
        "allergies": []
    }
    
    try:
        result = rule_based_recommendation(user_text, user_info, medicine_df, client=client)
        
        if result.get("status") == "success":
            medicines = result.get("recommended_medicines", [])
            
            if not medicines:
                print(f"[ERROR] 推奨医薬品がありません")
                return
            
            # トップ3の医薬品のスコアと効能を確認
            print(f"[DEBUG] 推奨された上位3つの医薬品:")
            for i, med in enumerate(medicines[:3], 1):
                score = med.get('total_score', med.get('score', 0))
                efficacy = med.get('efficacy', '')
                product_name = med.get('product_name', '')
                
                print(f"  {i}. {product_name}")
                print(f"     スコア: {score:.3f}")
                print(f"     効能: {efficacy[:80]}...")
                
                # のどの痛みへの適合度を確認
                if "のどの痛み" in efficacy or "喉の痛み" in efficacy:
                    print(f"     ✅ のどの痛みに対応")
                else:
                    print(f"     ⚠️ のどの痛みへの対応が不明")
            
            # スコアが降順に並んでいるか確認
            scores = [m.get('total_score', m.get('score', 0)) for m in medicines[:3]]
            if scores == sorted(scores, reverse=True):
                print(f"[OK] スコアが降順に並んでいます（最適な医薬品が上位に配置）")
            else:
                print(f"[WARNING] スコアが降順に並んでいません: {scores}")
            
            # 相対スコアとスコア帯の検証
            relative_scores = [m.get('relative_score') for m in medicines[:3] if m.get('relative_score') is not None]
            score_levels = [m.get('score_level') for m in medicines[:3] if m.get('score_level')]
            if relative_scores:
                print(f"[OK] 相対スコアが設定されています: {[f'{s*100:.1f}%' for s in relative_scores[:3]]}")
                if score_levels:
                    print(f"[OK] スコア帯が設定されています: {score_levels[:3]}")
            
            # スコア内訳の検証
            for i, med in enumerate(medicines[:3], 1):
                score_breakdown = med.get('score_breakdown', {})
                if score_breakdown:
                    print(f"\n  {i}. {med.get('product_name', '')} のスコア内訳:")
                    print(f"     症状適合: {score_breakdown.get('symptom_match', 0):.3f}")
                    print(f"     効能特異性: {score_breakdown.get('efficacy_specificity', 0):.3f}")
                    print(f"     年齢適合: {score_breakdown.get('age_fit', 0):.3f}")
                    if score_breakdown.get('symptom_specificity_penalty', 0) < 0:
                        print(f"     症状特異性ペナルティ: {score_breakdown.get('symptom_specificity_penalty', 0):.3f}")
        else:
            print(f"[ERROR] 推奨に失敗しました: {result.get('reason', '不明なエラー')}")
    except Exception as e:
        print(f"[ERROR] テスト実行中にエラー: {e}")
        import traceback
        traceback.print_exc()

def test_edge_cases():
    """テスト21: エッジケーステスト"""
    print("\n" + "="*80)
    print("テスト21: エッジケーステスト")
    print("="*80)
    
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
    
    # テストケース1: 空の入力
    print("\n[ケース1] 空の入力")
    user_text = ""
    user_info = {
        "age": 30,
        "gender": "男性",
        "current_medications": [],
        "allergies": []
    }
    
    try:
        result = rule_based_recommendation(user_text, user_info, medicine_df, client=client)
        
        if result.get("status") == "error" or result.get("status") == "escalation_required":
            print(f"[OK] 空の入力に対して適切にエラーまたはエスカレーションが返されました")
        else:
            print(f"[WARNING] 空の入力に対して推奨が返されました（予期しない動作）")
    except Exception as e:
        print(f"[OK] 空の入力に対して例外が発生しました（適切なエラーハンドリング）: {type(e).__name__}")
    
    # テストケース2: 非常に長い入力
    print("\n[ケース2] 非常に長い入力")
    user_text = "頭が痛いです。" * 100
    user_info = {
        "age": 30,
        "gender": "女性",
        "current_medications": [],
        "allergies": []
    }
    
    try:
        result = rule_based_recommendation(user_text, user_info, medicine_df, client=client)
        
        if result.get("status") == "success":
            medicines = result.get("recommended_medicines", [])
            print(f"[OK] 長い入力に対しても推奨が返されました（推奨数: {len(medicines)}）")
        else:
            print(f"[WARNING] 長い入力に対して推奨が返されませんでした: {result.get('status')}")
    except Exception as e:
        print(f"[WARNING] 長い入力でエラーが発生しました: {e}")
    
    # テストケース3: 不明な症状
    print("\n[ケース3] 不明な症状の入力")
    user_text = "宇宙人が襲ってくるような気がします。"
    user_info = {
        "age": 30,
        "gender": "男性",
        "current_medications": [],
        "allergies": []
    }
    
    try:
        result = rule_based_recommendation(user_text, user_info, medicine_df, client=client)
        
        if result.get("status") == "escalation_required" or result.get("status") == "error":
            print(f"[OK] 不明な症状に対して適切にエスカレーションまたはエラーが返されました")
        else:
            print(f"[INFO] 不明な症状に対して推奨が返されました（ステータス: {result.get('status')}）")
    except Exception as e:
        print(f"[OK] 不明な症状に対して例外が発生しました（適切なエラーハンドリング）")

def main():
    """メイン実行関数"""
    print("\n" + "="*80)
    print("医薬品推奨システム - 包括的テストスイート")
    print("="*80)
    
    try:
        # 全テストケースを実行
        test_rule_based_cold()
        test_rule_based_headache()
        test_rule_based_nasal()
        test_hybrid_medicine_type()
        test_missing_attributes()
        test_safety_checks()
        test_red_flag_symptoms()
        test_comprehensive_system()
        test_pediatric_filtering()
        test_topical_medicine_recommendation()
        test_motion_sickness_medicine_recommendation()
        test_allergy_symptom_detection()
        test_symptom_specific_boost()
        test_drug_interaction_filtering()
        test_allergy_filtering()
        test_breastfeeding_safety()
        test_pediatric_recommendation()
        test_elderly_recommendation()
        test_complex_symptom_combination()
        test_optimal_medicine_selection()
        test_edge_cases()
        
        test_kampo_penalty_shoulder_stiffness()
        test_kampo_safety_weak_stomach()
        test_throat_pain_only_scoring()
        
        # 不足している症状ケースのテスト（35件）
        test_menstrual_pain()
        test_toothache()
        test_stomach_pain()
        test_abdominal_pain()
        test_diarrhea()
        test_constipation()
        test_nausea()
        test_heartburn()
        test_indigestion()
        test_itching()
        test_rash()
        test_eczema()
        test_athletes_foot()
        test_bruise()
        test_sprain()
        test_eye_redness()
        test_eye_fatigue()
        test_eye_itching()
        test_insomnia()
        test_dizziness()
        test_fatigue()
        test_irritability()
        test_anxiety()
        test_stress()
        test_fever_only()
        test_cough_only()
        test_phlegm()
        test_runny_nose()
        test_nasal_congestion()
        test_sneezing()
        test_chills()
        test_joint_pain()
        test_cold_symptoms_combination()
        test_gastrointestinal_symptoms_combination()
        test_skin_symptoms_combination()
        
        print("\n" + "="*80)
        print("[OK] 全テスト完了")
        print("="*80)
        
    except Exception as e:
        print(f"\n[ERROR] テスト実行中にエラーが発生しました: {e}")
        import traceback
        traceback.print_exc()

def test_kampo_penalty_shoulder_stiffness():
    """テスト: 肩こり・筋肉痛での漢方薬ペナルティ（Test 10改善版）"""
    print("\n" + "="*80)
    print("テスト: 肩こり・筋肉痛での漢方薬ペナルティ検証")
    print("="*80)
    print("【目的】桃核承気湯などの実証向け漢方がペナルティされ、推奨順位が下がることを確認")
    
    user_text = "肩がこる、筋肉痛"
    user_info = {
        "age": 30,
        "gender": "男性",
        "pregnant": False,
        "breastfeeding": False,
        "current_medications": [],
        "allergies": []
    }
    
    result = rule_based_medicine_recommendation(user_text, user_info, client)
    
    if result.get('status') != 'success':
        print(f"\n[警告] 推奨が失敗しました。ステータス: {result.get('status')}")
        print(f"理由: {result.get('reason', '不明')}")
        return
    
    medicines = result.get('recommended_medicines', [])
    print(f"\n推奨医薬品数: {len(medicines)}")
    
    # 桃核承気湯の位置を確認
    tokakujoki_positions = []
    for i, med in enumerate(medicines, 1):
        product_name = med.get('product_name', '')
        score = med.get('score', 0)
        print(f"\n{i}. {product_name}")
        print(f"   スコア: {score:.3f}")
        print(f"   推奨理由: {med.get('reason', 'なし')[:100]}")
        
        if "桃核承気湯" in product_name:
            tokakujoki_positions.append((i, score, product_name))
    
    # 検証結果
    print("\n" + "-"*80)
    print("【検証結果】")
    if tokakujoki_positions:
        for pos, score, name in tokakujoki_positions:
            print(f"⚠️ 桃核承気湯が検出されました: 順位 {pos}, スコア {score:.3f}")
            if pos <= 3:
                print(f"   ⚠️ 警告: 桃核承気湯が上位3位以内にあります（ペナルティが効いていない可能性）")
            else:
                print(f"   ✅ 良好: 桃核承気湯が下位に配置されています（ペナルティが機能）")
    else:
        print("✅ 良好: 桃核承気湯が推奨リストに含まれていません（ペナLティが機能）")
    
    # 外用薬や葛根湯が上位にあるか確認
    topical_count = 0
    kakkonto_count = 0
    for i, med in enumerate(medicines[:5], 1):
        product_name = med.get('product_name', '')
        medicine_type = str(med.get('medicine_type', ''))
        if '外用' in medicine_type or 'テープ' in product_name or 'パップ' in product_name:
            topical_count += 1
        if '葛根湯' in product_name:
            kakkonto_count += 1
    
    print(f"\n上位5位内の外用薬数: {topical_count}")
    print(f"上位5位内の葛根湯数: {kakkonto_count}")
    if topical_count > 0 or kakkonto_count > 0:
        print("✅ 良好: 適切な医薬品（外用薬・葛根湯）が上位に配置されています")

def test_throat_pain_only_scoring():
    """テスト: のどの痛みのみの場合のスコア検証"""
    print("\n" + "="*80)
    print("テスト: のどの痛みのみの場合のスコア検証")
    print("="*80)
    print("【目的】のどの痛みのみの場合、のど特化医薬品が上位に来ることを確認")
    
    user_text = "のどが痛いです。"
    user_info = {
        "age": 30,
        "gender": "男性",
        "pregnant": False,
        "breastfeeding": False,
        "current_medications": [],
        "allergies": []
    }
    
    result = rule_based_medicine_recommendation(user_text, user_info, client)
    
    if result.get('status') != 'success':
        print(f"\n[警告] 推奨が失敗しました。ステータス: {result.get('status')}")
        print(f"理由: {result.get('reason', '不明')}")
        return
    
    medicines = result.get('recommended_medicines', [])
    print(f"\n推奨医薬品数: {len(medicines)}")
    
    if not medicines:
        print(f"[ERROR] 推奨医薬品がありません")
        return
    
    # トップ3の医薬品のスコアと効能を確認
    print(f"\n[DEBUG] 推奨された上位3つの医薬品:")
    for i, med in enumerate(medicines[:3], 1):
        score = med.get('score', 0)
        relative_score = med.get('relative_score')
        score_level = med.get('score_level', '中')
        efficacy = med.get('efficacy', '')
        product_name = med.get('product_name', '')
        medicine_type = med.get('medicine_type', '')
        
        print(f"  {i}. {product_name} ({medicine_type})")
        print(f"     絶対スコア: {score:.3f}")
        if relative_score is not None:
            print(f"     相対スコア: {relative_score * 100:.1f}% (レベル: {score_level})")
        print(f"     効能: {efficacy[:80]}...")
        
        # のどの痛みへの適合度を確認
        if "のどの痛み" in efficacy or "喉の痛み" in efficacy or "のど" in product_name:
            print(f"     ✅ のどの痛みに対応")
        else:
            print(f"     ⚠️ のどの痛みへの対応が不明")
    
    # スコアが降順に並んでいるか確認
    scores = [m.get('score', 0) for m in medicines[:3]]
    if scores == sorted(scores, reverse=True):
        print(f"\n[OK] スコアが降順に並んでいます（最適な医薬品が上位に配置）")
    else:
        print(f"\n[WARNING] スコアが降順に並んでいません: {scores}")
    
    # 相対スコアが設定されているか確認
    relative_scores = [m.get('relative_score') for m in medicines[:3] if m.get('relative_score') is not None]
    if relative_scores:
        print(f"[OK] 相対スコアが設定されています: {[f'{s*100:.1f}%' for s in relative_scores[:3]]}")
    else:
        print(f"[WARNING] 相対スコアが設定されていません")
    
    # のど特化医薬品が上位に来ているか確認
    throat_specific = [m for m in medicines[:3] if "のど" in m.get('product_name', '') or "のどの痛み" in m.get('efficacy', '')]
    if throat_specific:
        print(f"[OK] のど特化医薬品が上位に推奨されています: {[m.get('product_name') for m in throat_specific]}")
    else:
        print(f"[INFO] のど特化医薬品が上位3位以内にありません（一般的な風邪薬が推奨されている可能性）")
    
    # 複合薬（せき・たん用）が下位に来ているか確認
    compound_medicines = [m for m in medicines if "せき" in m.get('efficacy', '') and "たん" in m.get('efficacy', '')]
    if compound_medicines:
        compound_ranks = [medicines.index(m) + 1 for m in compound_medicines]
        print(f"[INFO] 複合薬（せき・たん用）の順位: {compound_ranks}")
        if min(compound_ranks) > 3:
            print(f"[OK] 複合薬が下位に配置されています（症状特異性ペナルティが機能）")
        else:
            print(f"[WARNING] 複合薬が上位に配置されています（症状特異性ペナルティが不十分の可能性）")

def test_kampo_safety_weak_stomach():
    """テスト: 胃腸虚弱者の肩こりでの安全性チェック"""
    print("\n" + "="*80)
    print("テスト: 胃腸虚弱者の肩こりでの安全性チェック")
    print("="*80)
    print("【目的】実証向け漢方（桃核承気湯など）が強力にペナルティ（-0.5）されることを確認")
    
    user_text = "肩こりがひどいが、胃腸が弱く下痢気味です"
    user_info = {
        "age": 35,
        "gender": "男性",
        "pregnant": False,
        "breastfeeding": False,
        "current_medications": [],
        "allergies": []
    }
    
    result = rule_based_medicine_recommendation(user_text, user_info, client)
    
    if result.get('status') != 'success':
        print(f"\n[警告] 推奨が失敗しました。ステータス: {result.get('status')}")
        print(f"理由: {result.get('reason', '不明')}")
        return
    
    medicines = result.get('recommended_medicines', [])
    print(f"\n推奨医薬品数: {len(medicines)}")
    
    # 実証向け漢方薬の位置とスコアを確認
    robust_kampo_medicines = []
    for i, med in enumerate(medicines, 1):
        product_name = med.get('product_name', '')
        score = med.get('score', 0)
        efficacy = str(med.get('efficacy', ''))
        
        print(f"\n{i}. {product_name}")
        print(f"   スコア: {score:.3f}")
        print(f"   推奨理由: {med.get('reason', 'なし')[:100]}")
        
        # 実証向け漢方を検出（桃核承気湯、防風通聖散など）
        is_robust_kampo = (
            "桃核承気湯" in product_name or
            "防風通聖散" in product_name or
            ("体力" in efficacy and ("充実" in efficacy or "比較的体力があり" in efficacy)) or
            ("便秘" in efficacy and "のぼせ" in efficacy)
        )
        
        if is_robust_kampo:
            robust_kampo_medicines.append((i, score, product_name, efficacy[:100]))
    
    # 検証結果
    print("\n" + "-"*80)
    print("【検証結果】")
    if robust_kampo_medicines:
        print("⚠️ 実証向け漢方が検出されました:")
        for pos, score, name, eff in robust_kampo_medicines:
            print(f"   - 順位 {pos}: {name} (スコア: {score:.3f})")
            print(f"     効能: {eff}")
            if pos <= 3:
                print(f"     ⚠️ 警告: 上位3位以内にあります（強力なペナルティが効いていない可能性）")
            elif pos <= 5:
                print(f"     ⚠️ 注意: 中位にあります（ペナルティが部分的に機能）")
            else:
                print(f"     ✅ 良好: 下位に配置されています（強力なペナルティが機能）")
    else:
        print("✅ 良好: 実証向け漢方が推奨リストに含まれていません（強力なペナルティが機能）")
    
    # 外用薬が推奨されているか確認
    topical_medicines = []
    for i, med in enumerate(medicines[:5], 1):
        product_name = med.get('product_name', '')
        medicine_type = str(med.get('medicine_type', ''))
        if '外用' in medicine_type or 'テープ' in product_name or 'パップ' in product_name:
            topical_medicines.append((i, product_name))
    
    if topical_medicines:
        print(f"\n✅ 良好: 適切な外用薬が上位に推奨されています:")
        for pos, name in topical_medicines:
            print(f"   - 順位 {pos}: {name}")
    else:
        print("\n⚠️ 注意: 外用薬が上位に推奨されていません")

# ================================================================================
# 不足している症状ケースのテスト追加（35件）
# ================================================================================

def test_menstrual_pain():
    """テスト: 生理痛の推奨テスト"""
    print("\n" + "="*80)
    print("テスト: 生理痛の推奨テスト")
    print("="*80)
    
    user_text = "生理痛がひどいです。"
    user_info = {"age": 25, "gender": "女性", "pregnant": False, "breastfeeding": False, "current_medications": [], "allergies": []}
    result = rule_based_medicine_recommendation(user_text, user_info, client)
    print_result(result, "生理痛")

def test_toothache():
    """テスト: 歯痛の推奨テスト"""
    print("\n" + "="*80)
    print("テスト: 歯痛の推奨テスト")
    print("="*80)
    
    user_text = "歯が痛いです。"
    user_info = {"age": 30, "gender": "男性", "pregnant": False, "breastfeeding": False, "current_medications": [], "allergies": []}
    result = rule_based_medicine_recommendation(user_text, user_info, client)
    print_result(result, "歯痛")

def test_stomach_pain():
    """テスト: 胃痛の推奨テスト"""
    print("\n" + "="*80)
    print("テスト: 胃痛の推奨テスト")
    print("="*80)
    
    user_text = "胃が痛いです。"
    user_info = {"age": 30, "gender": "男性", "pregnant": False, "breastfeeding": False, "current_medications": [], "allergies": []}
    result = rule_based_medicine_recommendation(user_text, user_info, client)
    print_result(result, "胃痛")

def test_abdominal_pain():
    """テスト: 腹痛の推奨テスト"""
    print("\n" + "="*80)
    print("テスト: 腹痛の推奨テスト")
    print("="*80)
    
    user_text = "お腹が痛いです。"
    user_info = {"age": 30, "gender": "女性", "pregnant": False, "breastfeeding": False, "current_medications": [], "allergies": []}
    result = rule_based_medicine_recommendation(user_text, user_info, client)
    print_result(result, "腹痛")

def test_diarrhea():
    """テスト: 下痢の推奨テスト"""
    print("\n" + "="*80)
    print("テスト: 下痢の推奨テスト")
    print("="*80)
    
    user_text = "下痢が続いています。"
    user_info = {"age": 30, "gender": "男性", "pregnant": False, "breastfeeding": False, "current_medications": [], "allergies": []}
    result = rule_based_medicine_recommendation(user_text, user_info, client)
    print_result(result, "下痢")

def test_constipation():
    """テスト: 便秘の推奨テスト"""
    print("\n" + "="*80)
    print("テスト: 便秘の推奨テスト")
    print("="*80)
    
    user_text = "便秘が続いています。"
    user_info = {"age": 30, "gender": "女性", "pregnant": False, "breastfeeding": False, "current_medications": [], "allergies": []}
    result = rule_based_medicine_recommendation(user_text, user_info, client)
    print_result(result, "便秘")

def test_nausea():
    """テスト: 吐き気の推奨テスト"""
    print("\n" + "="*80)
    print("テスト: 吐き気の推奨テスト")
    print("="*80)
    
    user_text = "吐き気がします。"
    user_info = {"age": 30, "gender": "男性", "pregnant": False, "breastfeeding": False, "current_medications": [], "allergies": []}
    result = rule_based_medicine_recommendation(user_text, user_info, client)
    print_result(result, "吐き気")

def test_heartburn():
    """テスト: 胸やけの推奨テスト"""
    print("\n" + "="*80)
    print("テスト: 胸やけの推奨テスト")
    print("="*80)
    
    user_text = "胸やけがします。"
    user_info = {"age": 30, "gender": "女性", "pregnant": False, "breastfeeding": False, "current_medications": [], "allergies": []}
    result = rule_based_medicine_recommendation(user_text, user_info, client)
    print_result(result, "胸やけ")

def test_indigestion():
    """テスト: 胃もたれの推奨テスト"""
    print("\n" + "="*80)
    print("テスト: 胃もたれの推奨テスト")
    print("="*80)
    
    user_text = "胃もたれがします。"
    user_info = {"age": 30, "gender": "男性", "pregnant": False, "breastfeeding": False, "current_medications": [], "allergies": []}
    result = rule_based_medicine_recommendation(user_text, user_info, client)
    print_result(result, "胃もたれ")

def test_itching():
    """テスト: かゆみの推奨テスト"""
    print("\n" + "="*80)
    print("テスト: かゆみの推奨テスト")
    print("="*80)
    
    user_text = "かゆみがあります。"
    user_info = {"age": 30, "gender": "男性", "pregnant": False, "breastfeeding": False, "current_medications": [], "allergies": []}
    result = rule_based_medicine_recommendation(user_text, user_info, client)
    print_result(result, "かゆみ")

def test_rash():
    """テスト: 発疹の推奨テスト"""
    print("\n" + "="*80)
    print("テスト: 発疹の推奨テスト")
    print("="*80)
    
    user_text = "発疹が出ています。"
    user_info = {"age": 30, "gender": "女性", "pregnant": False, "breastfeeding": False, "current_medications": [], "allergies": []}
    result = rule_based_medicine_recommendation(user_text, user_info, client)
    print_result(result, "発疹")

def test_eczema():
    """テスト: 湿疹の推奨テスト"""
    print("\n" + "="*80)
    print("テスト: 湿疹の推奨テスト")
    print("="*80)
    
    user_text = "湿疹が出ています。"
    user_info = {"age": 30, "gender": "男性", "pregnant": False, "breastfeeding": False, "current_medications": [], "allergies": []}
    result = rule_based_medicine_recommendation(user_text, user_info, client)
    print_result(result, "湿疹")

def test_athletes_foot():
    """テスト: 水虫の推奨テスト"""
    print("\n" + "="*80)
    print("テスト: 水虫の推奨テスト")
    print("="*80)
    
    user_text = "水虫が気になります。"
    user_info = {"age": 30, "gender": "男性", "pregnant": False, "breastfeeding": False, "current_medications": [], "allergies": []}
    result = rule_based_medicine_recommendation(user_text, user_info, client)
    print_result(result, "水虫")

def test_bruise():
    """テスト: 打撲の推奨テスト"""
    print("\n" + "="*80)
    print("テスト: 打撲の推奨テスト")
    print("="*80)
    
    user_text = "打撲しました。"
    user_info = {"age": 30, "gender": "男性", "pregnant": False, "breastfeeding": False, "current_medications": [], "allergies": []}
    result = rule_based_medicine_recommendation(user_text, user_info, client)
    print_result(result, "打撲")

def test_sprain():
    """テスト: 捻挫の推奨テスト"""
    print("\n" + "="*80)
    print("テスト: 捻挫の推奨テスト")
    print("="*80)
    
    user_text = "捻挫しました。"
    user_info = {"age": 30, "gender": "女性", "pregnant": False, "breastfeeding": False, "current_medications": [], "allergies": []}
    result = rule_based_medicine_recommendation(user_text, user_info, client)
    print_result(result, "捻挫")

def test_eye_redness():
    """テスト: 目の充血の推奨テスト"""
    print("\n" + "="*80)
    print("テスト: 目の充血の推奨テスト")
    print("="*80)
    
    user_text = "目が充血しています。"
    user_info = {"age": 30, "gender": "男性", "pregnant": False, "breastfeeding": False, "current_medications": [], "allergies": []}
    result = rule_based_medicine_recommendation(user_text, user_info, client)
    print_result(result, "目の充血")

def test_eye_fatigue():
    """テスト: 目の疲れの推奨テスト"""
    print("\n" + "="*80)
    print("テスト: 目の疲れの推奨テスト")
    print("="*80)
    
    user_text = "目が疲れます。"
    user_info = {"age": 30, "gender": "女性", "pregnant": False, "breastfeeding": False, "current_medications": [], "allergies": []}
    result = rule_based_medicine_recommendation(user_text, user_info, client)
    print_result(result, "目の疲れ")

def test_eye_itching():
    """テスト: 目のかゆみの推奨テスト"""
    print("\n" + "="*80)
    print("テスト: 目のかゆみの推奨テスト")
    print("="*80)
    
    user_text = "目がかゆいです。"
    user_info = {"age": 30, "gender": "男性", "pregnant": False, "breastfeeding": False, "current_medications": [], "allergies": []}
    result = rule_based_medicine_recommendation(user_text, user_info, client)
    print_result(result, "目のかゆみ")

def test_insomnia():
    """テスト: 不眠の推奨テスト"""
    print("\n" + "="*80)
    print("テスト: 不眠の推奨テスト")
    print("="*80)
    
    user_text = "眠れません。"
    user_info = {"age": 30, "gender": "男性", "pregnant": False, "breastfeeding": False, "current_medications": [], "allergies": []}
    result = rule_based_medicine_recommendation(user_text, user_info, client)
    print_result(result, "不眠")

def test_dizziness():
    """テスト: めまいの推奨テスト"""
    print("\n" + "="*80)
    print("テスト: めまいの推奨テスト")
    print("="*80)
    
    user_text = "めまいがします。"
    user_info = {"age": 30, "gender": "女性", "pregnant": False, "breastfeeding": False, "current_medications": [], "allergies": []}
    result = rule_based_medicine_recommendation(user_text, user_info, client)
    print_result(result, "めまい")

def test_fatigue():
    """テスト: 疲労感の推奨テスト"""
    print("\n" + "="*80)
    print("テスト: 疲労感の推奨テスト")
    print("="*80)
    
    user_text = "疲れが取れません。"
    user_info = {"age": 30, "gender": "男性", "pregnant": False, "breastfeeding": False, "current_medications": [], "allergies": []}
    result = rule_based_medicine_recommendation(user_text, user_info, client)
    print_result(result, "疲労感")

def test_irritability():
    """テスト: イライラの推奨テスト"""
    print("\n" + "="*80)
    print("テスト: イライラの推奨テスト")
    print("="*80)
    
    user_text = "イライラします。"
    user_info = {"age": 30, "gender": "女性", "pregnant": False, "breastfeeding": False, "current_medications": [], "allergies": []}
    result = rule_based_medicine_recommendation(user_text, user_info, client)
    print_result(result, "イライラ")

def test_anxiety():
    """テスト: 不安の推奨テスト"""
    print("\n" + "="*80)
    print("テスト: 不安の推奨テスト")
    print("="*80)
    
    user_text = "不安です。"
    user_info = {"age": 30, "gender": "男性", "pregnant": False, "breastfeeding": False, "current_medications": [], "allergies": []}
    result = rule_based_medicine_recommendation(user_text, user_info, client)
    print_result(result, "不安")

def test_stress():
    """テスト: ストレスの推奨テスト"""
    print("\n" + "="*80)
    print("テスト: ストレスの推奨テスト")
    print("="*80)
    
    user_text = "ストレスがたまっています。"
    user_info = {"age": 30, "gender": "女性", "pregnant": False, "breastfeeding": False, "current_medications": [], "allergies": []}
    result = rule_based_medicine_recommendation(user_text, user_info, client)
    print_result(result, "ストレス")

def test_fever_only():
    """テスト: 発熱のみの推奨テスト"""
    print("\n" + "="*80)
    print("テスト: 発熱のみの推奨テスト")
    print("="*80)
    
    user_text = "熱があります。"
    user_info = {"age": 30, "gender": "男性", "pregnant": False, "breastfeeding": False, "current_medications": [], "allergies": []}
    result = rule_based_medicine_recommendation(user_text, user_info, client)
    print_result(result, "発熱のみ")

def test_cough_only():
    """テスト: 咳のみの推奨テスト"""
    print("\n" + "="*80)
    print("テスト: 咳のみの推奨テスト")
    print("="*80)
    
    user_text = "咳が出ます。"
    user_info = {"age": 30, "gender": "女性", "pregnant": False, "breastfeeding": False, "current_medications": [], "allergies": []}
    result = rule_based_medicine_recommendation(user_text, user_info, client)
    print_result(result, "咳のみ")

def test_phlegm():
    """テスト: 痰の推奨テスト"""
    print("\n" + "="*80)
    print("テスト: 痰の推奨テスト")
    print("="*80)
    
    user_text = "痰が絡みます。"
    user_info = {"age": 30, "gender": "男性", "pregnant": False, "breastfeeding": False, "current_medications": [], "allergies": []}
    result = rule_based_medicine_recommendation(user_text, user_info, client)
    print_result(result, "痰")

def test_runny_nose():
    """テスト: 鼻水のみの推奨テスト"""
    print("\n" + "="*80)
    print("テスト: 鼻水のみの推奨テスト")
    print("="*80)
    
    user_text = "鼻水が出ます。"
    user_info = {"age": 30, "gender": "女性", "pregnant": False, "breastfeeding": False, "current_medications": [], "allergies": []}
    result = rule_based_medicine_recommendation(user_text, user_info, client)
    print_result(result, "鼻水のみ")

def test_nasal_congestion():
    """テスト: 鼻づまりのみの推奨テスト"""
    print("\n" + "="*80)
    print("テスト: 鼻づまりのみの推奨テスト")
    print("="*80)
    
    user_text = "鼻が詰まっています。"
    user_info = {"age": 30, "gender": "男性", "pregnant": False, "breastfeeding": False, "current_medications": [], "allergies": []}
    result = rule_based_medicine_recommendation(user_text, user_info, client)
    print_result(result, "鼻づまりのみ")

def test_sneezing():
    """テスト: くしゃみのみの推奨テスト"""
    print("\n" + "="*80)
    print("テスト: くしゃみのみの推奨テスト")
    print("="*80)
    
    user_text = "くしゃみが出ます。"
    user_info = {"age": 30, "gender": "女性", "pregnant": False, "breastfeeding": False, "current_medications": [], "allergies": []}
    result = rule_based_medicine_recommendation(user_text, user_info, client)
    print_result(result, "くしゃみのみ")

def test_chills():
    """テスト: 悪寒の推奨テスト"""
    print("\n" + "="*80)
    print("テスト: 悪寒の推奨テスト")
    print("="*80)
    
    user_text = "寒気がします。"
    user_info = {"age": 30, "gender": "男性", "pregnant": False, "breastfeeding": False, "current_medications": [], "allergies": []}
    result = rule_based_medicine_recommendation(user_text, user_info, client)
    print_result(result, "悪寒")

def test_joint_pain():
    """テスト: 関節痛の推奨テスト"""
    print("\n" + "="*80)
    print("テスト: 関節痛の推奨テスト")
    print("="*80)
    
    user_text = "関節が痛いです。"
    user_info = {"age": 30, "gender": "女性", "pregnant": False, "breastfeeding": False, "current_medications": [], "allergies": []}
    result = rule_based_medicine_recommendation(user_text, user_info, client)
    print_result(result, "関節痛")

def test_cold_symptoms_combination():
    """テスト: 複数の風邪症状の組み合わせ"""
    print("\n" + "="*80)
    print("テスト: 複数の風邪症状の組み合わせ")
    print("="*80)
    
    user_text = "熱があって、のども痛く、咳も出ます。"
    user_info = {"age": 30, "gender": "男性", "pregnant": False, "breastfeeding": False, "current_medications": [], "allergies": []}
    result = rule_based_medicine_recommendation(user_text, user_info, client)
    print_result(result, "複数の風邪症状")

def test_gastrointestinal_symptoms_combination():
    """テスト: 複数の胃腸症状の組み合わせ"""
    print("\n" + "="*80)
    print("テスト: 複数の胃腸症状の組み合わせ")
    print("="*80)
    
    user_text = "胃が痛くて、吐き気もします。"
    user_info = {"age": 30, "gender": "女性", "pregnant": False, "breastfeeding": False, "current_medications": [], "allergies": []}
    result = rule_based_medicine_recommendation(user_text, user_info, client)
    print_result(result, "複数の胃腸症状")

def test_skin_symptoms_combination():
    """テスト: 複数の皮膚症状の組み合わせ"""
    print("\n" + "="*80)
    print("テスト: 複数の皮膚症状の組み合わせ")
    print("="*80)
    
    user_text = "かゆみと発疹があります。"
    user_info = {"age": 30, "gender": "男性", "pregnant": False, "breastfeeding": False, "current_medications": [], "allergies": []}
    result = rule_based_medicine_recommendation(user_text, user_info, client)
    print_result(result, "複数の皮膚症状")

if __name__ == "__main__":
    main()
