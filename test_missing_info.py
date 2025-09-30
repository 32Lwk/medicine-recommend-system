"""
不足情報チェック機能のテスト
"""

from medicine_logic import rule_based_medicine_recommendation, client

def test_missing_age():
    """テスト1: 年齢情報なし（critical）"""
    print("\n" + "="*80)
    print("テスト1: 年齢情報なし（critical）")
    print("="*80)
    
    user_text = "頭が痛いです。"
    user_info = {
        "age": None,  # 年齢なし
        "gender": "男性",
        "pregnant": False,
        "breastfeeding": False,
        "current_medications": [],
        "allergies": []
    }
    
    result = rule_based_medicine_recommendation(user_text, user_info, client)
    print_result(result)

def test_complete_info():
    """テスト2: 完全な情報あり"""
    print("\n" + "="*80)
    print("テスト2: 完全な情報あり")
    print("="*80)
    
    user_text = "30歳です。昨日から頭が痛くて熱もあります。"
    user_info = {
        "age": 30,
        "gender": "男性",
        "pregnant": False,
        "breastfeeding": False,
        "current_medications": [],
        "allergies": ["なし"]
    }
    
    result = rule_based_medicine_recommendation(user_text, user_info, client)
    print_result(result)

def test_female_unknown_pregnancy():
    """テスト3: 女性で妊娠状態不明（important）"""
    print("\n" + "="*80)
    print("テスト3: 女性で妊娠状態不明（important）")
    print("="*80)
    
    user_text = "頭が痛いです。"
    user_info = {
        "age": 28,
        "gender": "女性",
        "pregnant": None,  # 不明
        "breastfeeding": None,  # 不明
        "current_medications": [],
        "allergies": []
    }
    
    result = rule_based_medicine_recommendation(user_text, user_info, client)
    print_result(result)

def print_result(result):
    """結果を見やすく表示"""
    print(f"\n--- 結果 ---")
    print(f"ステータス: {result.get('status')}")
    
    if result.get('status') == 'need_more_info':
        print(f"\n[情報不足] 追加質問が必要")
        print(f"優先度: {result.get('priority')}")
        print(f"不足フィールド: {result.get('missing_fields')}")
        print(f"\n質問:")
        for i, q in enumerate(result.get('questions', []), 1):
            print(f"  {i}. {q}")
    
    elif result.get('status') == 'success':
        print(f"\n[成功] 推奨成功")
        medicines = result.get('recommended_medicines', [])
        print(f"推奨医薬品数: {len(medicines)}")
        
        for med in medicines[:1]:  # 最初の1件のみ表示
            print(f"\n{med.get('number')}つ目: {med.get('product_name')} ({med.get('manufacturer')})")
            print(f"  スコア: {med.get('score', 0):.3f}")
            print(f"  理由: {med.get('reason', '')[:100]}...")
        
        # 追加質問
        additional_questions = result.get('additional_questions', [])
        if additional_questions:
            print(f"\n[追加質問あり]")
            for i, q in enumerate(additional_questions, 1):
                print(f"  {i}. {q}")
    
    print("\n")

if __name__ == "__main__":
    print("\n" + "="*80)
    print("不足情報チェック機能 - テスト実行")
    print("="*80)
    
    test_missing_age()
    test_complete_info()
    test_female_unknown_pregnancy()
    
    print("\n" + "="*80)
    print("全テスト完了")
    print("="*80)
