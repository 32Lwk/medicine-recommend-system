"""
ユーザー属性不足時の質問テスト
"""

from medicine_logic import rule_based_medicine_recommendation, client

def test_no_attributes():
    """テスト: すべての属性が不足"""
    print("\n" + "="*80)
    print("テスト: すべての属性が不足")
    print("="*80)
    
    user_text = "頭が痛いです。"
    user_info = {
        "age": None,           # 不足
        "gender": None,        # 不足
        "pregnant": None,      # 不足
        "breastfeeding": None, # 不足
        "current_medications": [],  # 不足
        "allergies": []        # 不足
    }
    
    result = rule_based_medicine_recommendation(user_text, user_info, client)
    
    print("\n" + "="*80)
    print("結果")
    print("="*80)
    print(f"ステータス: {result.get('status')}")
    print(f"推奨医薬品数: {len(result.get('recommended_medicines', []))}")
    
    additional_questions = result.get('additional_questions', [])
    missing_priority = result.get('missing_priority')
    
    print(f"\n追加質問数: {len(additional_questions)}")
    print(f"優先度: {missing_priority}")
    
    if additional_questions:
        print("\n質問リスト:")
        for i, q in enumerate(additional_questions, 1):
            print(f"  {i}. {q}")
    
    # 期待される質問
    expected_fields = ['age', 'gender', 'pregnancy_status', 'symptom_duration', 'current_medications', 'allergies']
    print(f"\n期待される不足フィールド: {expected_fields}")
    print(f"実際の不足フィールド数: {len(additional_questions)}")
    
    # 年齢と性別の質問が含まれているか確認
    has_age_question = any('年齢' in q for q in additional_questions)
    has_gender_question = any('性別' in q for q in additional_questions)
    has_pregnancy_question = any('妊娠' in q or '授乳' in q for q in additional_questions)
    
    print(f"\n確認:")
    print(f"  年齢の質問: {'✓' if has_age_question else '✗'}")
    print(f"  性別の質問: {'✓' if has_gender_question else '✗'}")
    print(f"  妊娠・授乳の質問: {'✓' if has_pregnancy_question else '✗'}")

if __name__ == "__main__":
    test_no_attributes()
