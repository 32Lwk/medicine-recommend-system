"""
年齢抽出の専用テスト
ルールベース抽出の改善を検証
"""

import os
import sys

# Windowsでの文字化け対策
if sys.platform.startswith('win'):
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.detach())
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.detach())

def test_age_extraction():
    """年齢抽出のテスト"""
    
    print("="*80)
    print("年齢抽出テスト")
    print("="*80)
    
    # テストモードを設定
    os.environ['TEST_MODE'] = '1'
    
    from medicine_logic import parse_age_expression
    
    # テストケース
    test_cases = [
        # 基本パターン
        ("30歳", 30),
        ("25才", 25),
        ("30代", 35),
        ("30歳代", 30),
        ("5歳児", 5),
        ("30代前半", 32),
        ("30代後半", 37),
        ("30代半ば", 35),
        ("30 years old", 30),
        ("30세", 30),
        ("30岁", 30),
        
        # 年齢推定パターン
        ("子どもが", 10),
        ("子供です", 10),
        ("こどもが", 10),
        ("赤ちゃんが", 1),
        ("赤ん坊です", 1),
        ("若い女性", 25),
        ("若者です", 25),
        ("中年の男性", 45),
        ("高齢者です", 70),
        ("高齢の女性", 70),
        ("お年寄りが", 70),
        ("学生さんです", 20),
        ("おじいちゃんが", 70),
        ("おじいさんです", 70),
        ("おばあちゃんが", 70),
        ("おばあさんです", 70),
        ("お父さんが", 45),
        ("お父様です", 45),
        ("お母さんが", 40),
        ("お母様です", 40),
        
        # 複合パターン
        ("30代女性で", 35),
        ("20代前半の男性", 22),
        ("40代後半の女性", 47),
        ("50代半ばの男性", 55),
        
        # エッジケース
        ("", None),
        ("年齢不明", None),
        ("大人です", None),
        ("成人です", None),
    ]
    
    print("1. 年齢抽出テスト")
    print("-" * 50)
    
    success_count = 0
    total_count = len(test_cases)
    
    for i, (test_text, expected) in enumerate(test_cases, 1):
        result = parse_age_expression(test_text)
        
        if result == expected:
            success_count += 1
            status = "OK"
        else:
            status = "NG"
        
        print(f"{status} [{i:2d}/{total_count}] {test_text}")
        print(f"     期待: {expected}, 結果: {result}")
    
    accuracy = success_count / total_count * 100
    print(f"\n年齢抽出精度: {success_count}/{total_count} ({accuracy:.1f}%)")
    
    print("\n" + "="*80)
    print("テスト結果サマリー")
    print("="*80)
    print(f"年齢抽出精度: {accuracy:.1f}%")
    
    # 成功基準の確認
    if accuracy >= 90.0:
        print("\nOK 年齢抽出: 成功基準をクリア")
    else:
        print("\nNG 年齢抽出: 成功基準未達成")

if __name__ == "__main__":
    test_age_extraction()
