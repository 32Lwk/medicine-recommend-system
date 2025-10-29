"""
症状期間抽出の専用テスト
"""

import os
import sys

# Windowsでの文字化け対策
if sys.platform.startswith('win'):
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.detach())
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.detach())

def test_duration_extraction():
    """症状期間抽出のテスト"""
    
    print("="*80)
    print("症状期間抽出テスト")
    print("="*80)
    
    # テストモードを設定
    os.environ['TEST_MODE'] = '1'
    
    from medicine_logic import extract_symptom_duration
    
    # テストケース
    test_cases = [
        # 基本パターン
        ("2日前から", 2),
        ("3日間", 3),
        ("1週間", 7),
        ("2週間前から", 14),
        ("1ヶ月", 30),
        ("昨日から", 1),
        ("今朝から", 0),
        ("先週から", 7),
        ("2日続いている", 2),
        ("3日ほど", 3),
        ("1日くらい", 1),
        
        # 複合パターン
        ("2日前から頭痛が続いています", 2),
        ("1週間前から咳が止まりません", 7),
        ("昨日から発熱があります", 1),
        ("3日間下痢が続いています", 3),
        ("先週から鼻水が出ています", 7),
        
        # エッジケース
        ("", None),
        ("症状があります", None),
        ("痛いです", None),
        ("0日前から", 0),
        ("365日間", 365),
        ("366日間", None),  # 範囲外
        ("-1日前から", None),  # 負の値
    ]
    
    print("1. 症状期間抽出テスト")
    print("-" * 50)
    
    success_count = 0
    total_count = len(test_cases)
    
    for i, (test_text, expected) in enumerate(test_cases, 1):
        result = extract_symptom_duration(test_text)
        
        if result == expected:
            success_count += 1
            status = "OK"
        else:
            status = "NG"
        
        print(f"{status} [{i:2d}/{total_count}] {test_text}")
        print(f"     期待: {expected}, 結果: {result}")
    
    accuracy = success_count / total_count * 100
    print(f"\n症状期間抽出精度: {success_count}/{total_count} ({accuracy:.1f}%)")
    
    print("\n" + "="*80)
    print("テスト結果サマリー")
    print("="*80)
    print(f"症状期間抽出精度: {accuracy:.1f}%")
    
    # 成功基準の確認
    if accuracy >= 80.0:
        print("\nOK 症状期間抽出: 成功基準をクリア")
    else:
        print("\nNG 症状期間抽出: 成功基準未達成")

if __name__ == "__main__":
    test_duration_extraction()
