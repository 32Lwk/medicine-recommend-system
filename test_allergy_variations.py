"""
アレルギー異表記対応のテスト
"""

import os
import sys

# Windowsでの文字化け対策
if sys.platform.startswith('win'):
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.detach())
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.detach())

def test_allergy_variations():
    """アレルギー異表記のテスト"""
    
    print("="*80)
    print("アレルギー異表記対応テスト")
    print("="*80)
    
    # テストモードを設定
    os.environ['TEST_MODE'] = '1'
    
    from medicine_logic import extract_allergies_from_text
    
    # テストケース（異表記を含む）
    test_cases = [
        # 卵の異表記
        ("たまごアレルギーです。", ["卵"]),
        ("タマゴが食べられません。", ["卵"]),
        ("エッグで蕁麻疹が出ます。", ["卵"]),
        ("eggアレルギー体質です。", ["卵"]),
        
        # 乳の異表記
        ("牛乳でアレルギー反応が出ます。", ["乳"]),
        ("ミルクがダメです。", ["乳"]),
        ("milkで蕁麻疹が出ます。", ["乳"]),
        ("乳製品アレルギーです。", ["乳"]),
        
        # 小麦の異表記
        ("こむぎアレルギー体質です。", ["小麦"]),
        ("コムギが食べられません。", ["小麦"]),
        ("wheatで発疹が出ます。", ["小麦"]),
        
        # えびの異表記
        ("エビアレルギーです。", ["えび"]),
        ("海老がダメです。", ["えび"]),
        ("shrimpでかゆみが出ます。", ["えび"]),
        
        # かにの異表記
        ("カニアレルギー体質です。", ["かに"]),
        ("蟹が食べられません。", ["かに"]),
        ("crabで蕁麻疹が出ます。", ["かに"]),
        
        # そばの異表記
        ("ソバアレルギーです。", ["そば"]),
        ("蕎麦がダメです。", ["そば"]),
        ("sobaで発疹が出ます。", ["そば"]),
        
        # 複数アレルギーの異表記
        ("たまごと牛乳のアレルギーがあります。", ["卵", "乳"]),
        ("エビとカニが食べられません。", ["えび", "かに"]),
        ("wheatとsobaで蕁麻疹が出ます。", ["小麦", "そば"]),
        
        # 誤検出を防ぐテスト
        ("太ももが痛いです。", []),  # もも（桃）の誤検出を防ぐ
        ("小麦色の肌をしています。", []),  # 小麦の誤検出を防ぐ
        ("さばを読むのが得意です。", []),  # さば（魚）の誤検出を防ぐ
    ]
    
    print("1. 異表記マッチングテスト")
    print("-" * 50)
    
    success_count = 0
    total_count = len(test_cases)
    
    for i, (test_text, expected) in enumerate(test_cases, 1):
        result = extract_allergies_from_text(test_text)
        
        # 結果を比較（順序は考慮しない）
        result_set = set(result)
        expected_set = set(expected)
        
        if result_set == expected_set:
            success_count += 1
            status = "OK"
        else:
            status = "NG"
        
        print(f"{status} [{i:2d}/{total_count}] {test_text}")
        print(f"     期待: {expected}")
        print(f"     結果: {result}")
    
    accuracy = success_count / total_count * 100
    print(f"\n異表記マッチング精度: {success_count}/{total_count} ({accuracy:.1f}%)")
    
    print("\n" + "="*80)
    print("テスト結果サマリー")
    print("="*80)
    print(f"異表記マッチング精度: {accuracy:.1f}%")
    
    # 成功基準の確認
    if accuracy >= 80.0:
        print("\nOK 異表記対応: 成功基準をクリア")
    else:
        print("\nNG 異表記対応: 成功基準未達成")

if __name__ == "__main__":
    test_allergy_variations()
