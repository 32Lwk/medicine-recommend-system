"""
最終テスト: 頭痛症状での完全なフロー確認
"""

from medicine_logic import rule_based_medicine_recommendation, client

def test_headache():
    """頭痛のテスト（undefined問題の確認）"""
    print("\n" + "="*80)
    print("最終テスト: 頭痛症状")
    print("="*80)
    
    user_text = "頭が痛く、熱があります。"
    user_info = {
        "age": 30,
        "gender": "男性",
        "pregnant": False,
        "breastfeeding": False,
        "current_medications": [],
        "allergies": []
    }
    
    result = rule_based_medicine_recommendation(user_text, user_info, client)
    
    print("\n" + "="*80)
    print("結果の詳細")
    print("="*80)
    print(f"ステータス: {result.get('status')}")
    
    if result.get('status') == 'success':
        medicines = result.get('recommended_medicines', [])
        print(f"\n推奨医薬品数: {len(medicines)}")
        
        for med in medicines:
            print(f"\n{'='*80}")
            print(f"{med.get('number')}つ目: {med.get('product_name')} ({med.get('manufacturer')})")
            print(f"スコア: {med.get('score', 0):.3f}")
            print(f"推奨理由: {med.get('reason', 'なし')}")
            print(f"効能効果: {med.get('efficacy', '')[:100]}...")
            print(f"主な成分: {med.get('ingredients', '').split(chr(10))[0] if med.get('ingredients') else 'なし'}")
            
            # numberとreasonがundefinedでないか確認
            assert med.get('number') is not None, "numberがNoneです！"
            assert med.get('reason') is not None, "reasonがNoneです！"
            assert med.get('reason') != '', "reasonが空文字です！"
        
        print(f"\n{'='*80}")
        print("使用上の注意:")
        print(result.get('usage_notes', 'なし'))
        
        print(f"\n{'='*80}")
        print("医師の受診が必要な場合:")
        print(result.get('doctor_consultation', 'なし'))
        
        print(f"\n{'='*80}")
        print("[成功] すべてのフィールドが正しく設定されています！")
        print("="*80)

if __name__ == "__main__":
    test_headache()
