"""
医薬品推奨システム - 包括的テストスイート
統合されたテストファイル（全機能をカバー）
"""

import sys
import os

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
        
        print("\n" + "="*80)
        print("✅ 全テスト完了")
        print("="*80)
        
    except Exception as e:
        print(f"\n❌ テスト実行中にエラーが発生しました: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
