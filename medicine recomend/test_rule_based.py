"""
ルールベース医薬品推奨システムのテストスクリプト
"""

import sys
import os

# 現在のディレクトリをパスに追加
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from medicine_logic import rule_based_medicine_recommendation, client

# ================================================================================
# テストケース
# ================================================================================

def test_case_1():
    """テストケース1: 風邪の初期症状"""
    print("\n" + "="*80)
    print("テストケース1: 風邪の初期症状")
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
    print_result(result)

def test_case_2():
    """テストケース2: 頭痛のみ"""
    print("\n" + "="*80)
    print("テストケース2: 頭痛のみ")
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
    print_result(result)

def test_case_3():
    """テストケース3: 花粉症（鼻炎症状）"""
    print("\n" + "="*80)
    print("テストケース3: 花粉症（鼻炎症状）")
    print("="*80)
    
    user_text = "鼻水が止まらず、くしゃみも頻繁に出ます。目もかゆいです。"
    user_info = {
        "age": 28,
        "gender": "女性",
        "pregnant": False,
        "breastfeeding": False,
        "current_medications": [],
        "allergies": []
    }
    
    result = rule_based_medicine_recommendation(user_text, user_info, client)
    print_result(result)

def test_case_4():
    """テストケース4: 妊娠中の風邪"""
    print("\n" + "="*80)
    print("テストケース4: 妊娠中の風邪（安全性チェック）")
    print("="*80)
    
    user_text = "喉が痛くて咳も出ます。妊娠中なので安全な薬を教えてください。"
    user_info = {
        "age": 32,
        "gender": "女性",
        "pregnant": True,
        "breastfeeding": False,
        "current_medications": [],
        "allergies": []
    }
    
    result = rule_based_medicine_recommendation(user_text, user_info, client)
    print_result(result)

def test_case_5():
    """テストケース5: 重症疑い（高熱）"""
    print("\n" + "="*80)
    print("テストケース5: 重症疑い（高熱） - エスカレーション期待")
    print("="*80)
    
    user_text = "39度の高熱が3日間続いています。呼吸も少し苦しいです。"
    user_info = {
        "age": 45,
        "gender": "男性",
        "pregnant": False,
        "breastfeeding": False,
        "current_medications": [],
        "allergies": []
    }
    
    result = rule_based_medicine_recommendation(user_text, user_info, client)
    print_result(result)

def test_case_6():
    """テストケース6: 小児（年齢制限チェック）"""
    print("\n" + "="*80)
    print("テストケース6: 小児（年齢制限チェック）")
    print("="*80)
    
    user_text = "子供が鼻水と咳をしています。熱はありません。"
    user_info = {
        "age": 5,
        "gender": "男性",
        "pregnant": False,
        "breastfeeding": False,
        "current_medications": [],
        "allergies": []
    }
    
    result = rule_based_medicine_recommendation(user_text, user_info, client)
    print_result(result)

def print_result(result):
    """結果を見やすく表示"""
    print(f"\n--- 結果 ---")
    print(f"ステータス: {result.get('status')}")
    
    if result.get('status') == 'escalation_required':
        print(f"[警告] エスカレーション必要")
        print(f"理由: {result.get('reason')}")
    elif result.get('status') == 'success':
        print(f"[成功] 推奨成功")
        medicines = result.get('recommended_medicines', [])
        print(f"\n推奨医薬品数: {len(medicines)}")
        for med in medicines:
            print(f"\n{med.get('rank')}位: {med.get('product_name')} ({med.get('manufacturer')})")
            print(f"  種類: {med.get('medicine_type')}")
            print(f"  スコア: {med.get('score'):.3f}")
            print(f"  説明: {med.get('explanation')}")
    
    if result.get('warnings'):
        print(f"\n[警告]:")
        for warning in result.get('warnings', []):
            print(f"  - {warning}")
    
    print("\n")

# ================================================================================
# メイン実行
# ================================================================================

if __name__ == "__main__":
    print("\n")
    print("="*80)
    print("ルールベース医薬品推奨システム - テスト実行")
    print("="*80)
    
    # 全テストケースを実行
    test_case_1()
    test_case_2()
    test_case_3()
    test_case_4()
    test_case_5()
    test_case_6()
    
    print("\n")
    print("="*80)
    print("全テスト完了")
    print("="*80)
