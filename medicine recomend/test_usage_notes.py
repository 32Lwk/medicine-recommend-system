"""
使用上の注意の表示確認テスト
"""

from medicine_logic import rule_based_medicine_recommendation, client

def test_usage_notes_display():
    """使用上の注意の詳細表示テスト"""
    print("\n" + "="*80)
    print("使用上の注意 - 表示確認テスト")
    print("="*80)
    
    user_text = "頭が痛いです。"
    user_info = {
        "age": 30,
        "gender": "女性",
        "pregnant": False,
        "breastfeeding": False,
        "current_medications": [],
        "allergies": []
    }
    
    result = rule_based_medicine_recommendation(user_text, user_info, client)
    
    if result.get('status') == 'success':
        print("\n" + "="*80)
        print("推奨医薬品")
        print("="*80)
        for med in result.get('recommended_medicines', [])[:3]:
            print(f"\n{med.get('number')}. {med.get('product_name')} ({med.get('manufacturer')})")
            print(f"   スコア: {med.get('score', 0):.3f}")
        
        print("\n" + "="*80)
        print("使用上の注意")
        print("="*80)
        print(result.get('usage_notes', 'なし'))
        
        print("\n" + "="*80)
        print("医師の受診が必要な場合")
        print("="*80)
        print(result.get('doctor_consultation', 'なし'))
        
        print("\n" + "="*80)
        print("追加質問")
        print("="*80)
        additional_questions = result.get('additional_questions', [])
        if additional_questions:
            for i, q in enumerate(additional_questions, 1):
                print(f"{i}. {q}")
        else:
            print("なし")
        
        # 年齢制限情報が含まれているか確認
        usage_notes = result.get('usage_notes', '')
        print("\n" + "="*80)
        print("チェック項目")
        print("="*80)
        
        checks = {
            "年齢制限の記載": any(keyword in usage_notes for keyword in ["年齢", "歳未満", "歳以上"]),
            "使ってはいけない人の記載": "使ってはいけない" in usage_notes or "禁忌" in usage_notes or "アレルギー" in usage_notes,
            "用法用量の記載": "用法" in usage_notes or "服用" in usage_notes,
            "医師相談の記載": result.get('doctor_consultation', '') != ''
        }
        
        for check_name, check_result in checks.items():
            status = "[OK]" if check_result else "[NG]"
            print(f"{status} {check_name}")

if __name__ == "__main__":
    test_usage_notes_display()
