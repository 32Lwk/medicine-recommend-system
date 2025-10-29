"""
アレルギー28品目抽出の専用テスト
辞書式抽出とChatGPT抽出の両方を検証
"""

import os
import sys
from openai import OpenAI

def test_allergy_extraction():
    """アレルギー28品目の抽出テスト"""
    
    print("="*80)
    print("アレルギー28品目抽出テスト")
    print("="*80)
    
    # テストモードを設定
    os.environ['TEST_MODE'] = '1'
    os.environ['OPENAI_API_KEY'] = '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'
    
    from medicine_logic import extract_allergies_from_text, extract_user_attributes_multilingual
    
    client = OpenAI()
    
    # アレルギー28品目
    ALLERGY_28_ITEMS = [
        'えび', 'かに', 'くるみ', '小麦', 'そば', '卵', '乳', '落花生',
        'ピーナッツ', 'アーモンド', 'あわび', 'いか', 'いくら', 'オレンジ',
        'カシューナッツ', 'キウイフルーツ', '牛肉', 'ごま', 'さけ', 'さば',
        '大豆', '鶏肉', 'バナナ', '豚肉', 'マカダミアナッツ', 'もも',
        'やまいも', 'りんご', 'ゼラチン'
    ]
    
    # テストケース（各品目1つずつ）
    test_cases = [
        "えびアレルギーです。昨日から蕁麻疹が出ています。",
        "かにが食べられません。2日前から腹痛があります。",
        "くるみでアレルギー反応が出ます。頭痛が続いています。",
        "小麦アレルギー体質です。胃が痛いです。",
        "そばで蕁麻疹が出ます。3日前から咳が止まりません。",
        "卵アレルギーがあります。発熱と倦怠感があります。",
        "乳製品がダメです。下痢が続いています。",
        "落花生でアナフィラキシーを起こします。呼吸が苦しいです。",
        "ピーナッツアレルギーです。目のかゆみがあります。",
        "アーモンドが食べられません。鼻水が止まりません。",
        "あわびでアレルギー反応が出ます。関節痛があります。",
        "いかアレルギーです。筋肉痛がひどいです。",
        "いくらで蕁麻疹が出ます。めまいがします。",
        "オレンジアレルギー体質です。疲れが取れません。",
        "カシューナッツがダメです。不眠気味です。",
        "キウイフルーツでアレルギーがあります。冷え性です。",
        "牛肉アレルギーです。むくみがひどいです。",
        "ごまでアレルギー反応が出ます。肩こりがひどいです。",
        "さけアレルギー体質です。腰痛があります。",
        "さばが食べられません。胃もたれがします。",
        "大豆アレルギーがあります。吐き気がします。",
        "鶏肉でアレルギー反応が出ます。便秘がちです。",
        "バナナアレルギーです。腹痛があります。",
        "豚肉がダメです。下痢をしています。",
        "マカダミアナッツで蕁麻疹が出ます。頭痛があります。",
        "ももアレルギー体質です。発熱しています。",
        "やまいもでアレルギーがあります。咳が出ます。",
        "りんごアレルギーです。鼻づまりがひどいです。",
        "ゼラチンが食べられません。喉の痛みがあります。"
    ]
    
    # 誤検出テストケース
    false_positive_cases = [
        "太ももが痛いです。",  # もも（桃）の誤検出を防ぐ
        "小麦色の肌をしています。",  # 小麦の誤検出を防ぐ
        "さばを読むのが得意です。",  # さば（魚）の誤検出を防ぐ
        "包み込むように優しく。",  # くるみの誤検出を防ぐ
    ]
    
    print("1. 辞書式抽出テスト")
    print("-" * 50)
    
    dictionary_success = 0
    dictionary_total = len(test_cases)
    
    for i, test_text in enumerate(test_cases, 1):
        expected_allergy = ALLERGY_28_ITEMS[i-1]
        extracted_allergies = extract_allergies_from_text(test_text)
        
        if expected_allergy in extracted_allergies:
            dictionary_success += 1
            status = "OK"
        else:
            status = "NG"
        
        print(f"{status} [{i:2d}/29] {test_text[:30]}...")
        print(f"     期待: {expected_allergy}, 抽出: {extracted_allergies}")
    
    dictionary_accuracy = dictionary_success / dictionary_total * 100
    print(f"\n辞書式抽出精度: {dictionary_success}/{dictionary_total} ({dictionary_accuracy:.1f}%)")
    
    print("\n2. 誤検出テスト")
    print("-" * 50)
    
    false_positive_count = 0
    for i, test_text in enumerate(false_positive_cases, 1):
        extracted_allergies = extract_allergies_from_text(test_text)
        
        if extracted_allergies:
            false_positive_count += 1
            status = "NG"
        else:
            status = "OK"
        
        print(f"{status} [{i}/4] {test_text}")
        print(f"     抽出: {extracted_allergies}")
    
    false_positive_rate = false_positive_count / len(false_positive_cases) * 100
    print(f"\n誤検出率: {false_positive_count}/{len(false_positive_cases)} ({false_positive_rate:.1f}%)")
    
    print("\n3. 統合抽出テスト（辞書式+ChatGPT）")
    print("-" * 50)
    
    # 最初の10件でテスト（時間短縮）
    integration_success = 0
    integration_total = min(10, len(test_cases))
    
    for i in range(integration_total):
        test_text = test_cases[i]
        expected_allergy = ALLERGY_28_ITEMS[i]
        
        try:
            extracted_attrs = extract_user_attributes_multilingual(test_text, client)
            extracted_allergies = extracted_attrs.get('allergies', [])
            
            if expected_allergy in extracted_allergies:
                integration_success += 1
                status = "OK"
            else:
                status = "NG"
            
            print(f"{status} [{i+1:2d}/10] {test_text[:30]}...")
            print(f"     期待: {expected_allergy}, 抽出: {extracted_allergies}")
            
        except Exception as e:
            print(f"NG [{i+1:2d}/10] エラー: {e}")
    
    integration_accuracy = integration_success / integration_total * 100
    print(f"\n統合抽出精度: {integration_success}/{integration_total} ({integration_accuracy:.1f}%)")
    
    print("\n" + "="*80)
    print("テスト結果サマリー")
    print("="*80)
    print(f"辞書式抽出精度: {dictionary_accuracy:.1f}%")
    print(f"誤検出率: {false_positive_rate:.1f}%")
    print(f"統合抽出精度: {integration_accuracy:.1f}%")
    
    # 成功基準の確認
    if dictionary_accuracy >= 90.0 and false_positive_rate <= 5.0:
        print("\nOK 辞書式抽出: 成功基準をクリア")
    else:
        print("\nNG 辞書式抽出: 成功基準未達成")
    
    if integration_accuracy >= 90.0:
        print("OK 統合抽出: 成功基準をクリア")
    else:
        print("NG 統合抽出: 成功基準未達成")

if __name__ == "__main__":
    test_allergy_extraction()
