"""
ハイブリッドシステムの簡単なテスト
"""

from medicine_logic import analyze_symptoms_and_medicine_type, rule_based_medicine_recommendation, comprehensive_medicine_recommendation, client

def test_medicine_type_detection():
    """医薬品種類の判定テスト"""
    print("\n" + "="*80)
    print("医薬品種類判定テスト")
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
                print(f"  → アルゴリズム: ChatGPTベース")
        except Exception as e:
            print(f"  → エラー: {e}")

if __name__ == "__main__":
    test_medicine_type_detection()
    print("\n" + "="*80)
    print("テスト完了")
    print("="*80 + "\n")
