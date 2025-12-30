"""
不適切な要求検出機能のユニットテスト
"""
import sys
import os

# プロジェクトルートをパスに追加
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

# .envファイルを読み込む
try:
    from dotenv import load_dotenv
    env_path = os.path.join(BASE_DIR, '.env')
    if os.path.exists(env_path):
        load_dotenv(env_path, override=True)
        print(f"✅ .envファイルを読み込みました: {env_path}")
    else:
        # .envファイルが存在しない場合は、プロジェクトルートでload_dotenvを試す
        load_dotenv(override=True)
        print("⚠️ .envファイルが見つかりませんでした。環境変数から直接読み込みます。")
except ImportError:
    print("⚠️ python-dotenvがインストールされていません。環境変数から直接読み込みます。")

from counseling_response import (
    detect_inappropriate_request, 
    generate_illegal_drug_rejection_message,
    is_treatment_mention,
    has_specific_symptom,
    is_medical_prevention_request,
    is_severe_disease_request,
    is_psychiatric_disease_request
)
from llm_triage import llm_triage, check_heart_emergency_with_context
from openai import OpenAI

def test_detect_inappropriate_request():
    """detect_inappropriate_request関数のテスト"""
    print("=== detect_inappropriate_request関数のテスト ===")
    
    # テストケース
    test_cases = [
        {
            "user_text": "処方して",
            "triage_result": {"category": "Other", "subcategory": "inappropriate_request/prescription"},
            "expected": "prescription"
        },
        {
            "user_text": "痩せ薬を教えて",
            "triage_result": {"category": "Other", "subcategory": "inappropriate_request/weight_loss"},
            "expected": "weight_loss"
        },
        {
            "user_text": "惚れ薬を処方して",
            "triage_result": {"category": "Other", "subcategory": "inappropriate_request/love_potion"},
            "expected": "love_potion"
        },
        {
            "user_text": "覚醒剤を教えて",
            "triage_result": {"category": "Other", "subcategory": "inappropriate_request/illegal"},
            "expected": "illegal"
        },
        {
            "user_text": "頭痛がします",
            "triage_result": {"category": "Physical", "subcategory": "headache"},
            "expected": None
        },
        # 併存症と主訴の切り分け
        {
            "user_text": "風邪を完治したい",
            "triage_result": {"category": "Physical", "subcategory": "headache"},
            "expected": None  # 通常フロー（具体的な症状が述べられている）
        },
        {
            "user_text": "頭痛を治したい",
            "triage_result": {"category": "Physical", "subcategory": "headache"},
            "expected": None  # 通常フロー（具体的な症状が述べられている）
        },
        {
            "user_text": "糖尿病で通院中だけど、鼻水が止まらない",
            "triage_result": {"category": "Physical", "subcategory": "headache"},
            "expected": None  # 通常フロー（治療中キーワード + 具体的な症状）
        },
        {
            "user_text": "糖尿病の薬を飲んでいるが、風邪を完治させたい",
            "triage_result": {"category": "Physical", "subcategory": "headache"},
            "expected": None  # 通常フロー（併存症としての言及）
        },
        # 誤判定対策
        {
            "user_text": "心臓がドキドキする（動悸）",
            "triage_result": {"category": "Physical", "subcategory": "heart_pain"},
            "expected": None  # 通常フロー（症状キーワード）
        },
        {
            "user_text": "肝臓を労わりたい",
            "triage_result": {"category": "Physical", "subcategory": "general"},
            "expected": None  # 通常フロー（重篤疾患リストから除外）
        },
        # 不適切な要求として除外するケース
        {
            "user_text": "がんを完治する薬",
            "triage_result": {"category": "Other", "subcategory": "inappropriate_request/cure_prevention"},
            "expected": "cure_prevention"  # 重篤な疾患の完治要求
        },
        {
            "user_text": "糖尿病に効く市販薬を教えて",
            "triage_result": {"category": "Other", "subcategory": "inappropriate_request/cure_prevention"},
            "expected": "cure_prevention"  # 重篤な疾患の治療要求
        },
        {
            "user_text": "心筋梗塞を予防したい",
            "triage_result": {"category": "Other", "subcategory": "inappropriate_request/cure_prevention"},
            "expected": "cure_prevention"  # 重篤な疾患の予防要求
        },
        # 医薬的な予防
        {
            "user_text": "日焼けを予防したい",
            "triage_result": {"category": "Other", "subcategory": "inappropriate_request/cure_prevention"},
            "expected": None  # カウンセリングフロー（医薬的な予防）
        },
        {
            "user_text": "酔い止めを教えて",
            "triage_result": {"category": "Other", "subcategory": "inappropriate_request/cure_prevention"},
            "expected": None  # カウンセリングフロー（医薬的な予防）
        },
        # 精神疾患のテスト
        {
            "user_text": "うつ病を完治したい",
            "triage_result": {"category": "Other", "subcategory": "inappropriate_request/cure_prevention"},
            "expected": "psychiatric_cure_prevention"  # 共感的なメッセージ
        },
        {
            "user_text": "うつ病の薬を飲んでいるが、不眠で悩んでいる",
            "triage_result": {"category": "Physical", "subcategory": "insomnia"},
            "expected": None  # 通常フロー（併存症）
        },
        # 表記ゆれのテスト
        {
            "user_text": "ガンを完治したい",
            "triage_result": {"category": "Other", "subcategory": "inappropriate_request/cure_prevention"},
            "expected": "cure_prevention"  # 表記ゆれ（ガン）
        },
        {
            "user_text": "癌を完治したい",
            "triage_result": {"category": "Other", "subcategory": "inappropriate_request/cure_prevention"},
            "expected": "cure_prevention"  # 表記ゆれ（癌）
        },
        # 治療中キーワードのテスト
        {
            "user_text": "緑内障で治療中だけど、酔い止めを教えて",
            "triage_result": {"category": "Other", "subcategory": "inappropriate_request/cure_prevention"},
            "expected": None  # 通常フロー（治療中キーワード + 医薬的な予防）
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        result = detect_inappropriate_request(
            test_case["user_text"],
            test_case["triage_result"]
        )
        expected = test_case["expected"]
        status = "✅" if result == expected else "❌"
        print(f"{status} テストケース {i}: {test_case['user_text']}")
        print(f"   期待値: {expected}, 実際の値: {result}")
        if result != expected:
            print(f"   ⚠️ テスト失敗")
        print()


def test_generate_illegal_drug_rejection_message():
    """generate_illegal_drug_rejection_message関数のテスト"""
    print("=== generate_illegal_drug_rejection_message関数のテスト ===")
    
    # 違法薬物のテスト
    illegal_message = generate_illegal_drug_rejection_message("illegal")
    print("✅ 違法薬物メッセージ生成:")
    print(f"   長さ: {len(illegal_message)}文字")
    print(f"   内容の一部: {illegal_message[:100]}...")
    assert "違法薬物" in illegal_message, "違法薬物のメッセージに「違法薬物」が含まれていません"
    assert "法的警告" in illegal_message, "違法薬物のメッセージに「法的警告」が含まれていません"
    print()
    
    # 規制薬物のテスト
    controlled_message = generate_illegal_drug_rejection_message("controlled")
    print("✅ 規制薬物メッセージ生成:")
    print(f"   長さ: {len(controlled_message)}文字")
    print(f"   内容の一部: {controlled_message[:100]}...")
    assert "規制薬物" in controlled_message, "規制薬物のメッセージに「規制薬物」が含まれていません"
    assert "法的警告" in controlled_message, "規制薬物のメッセージに「法的警告」が含まれていません"
    print()


def test_helper_functions():
    """ヘルパー関数のテスト"""
    print("=== ヘルパー関数のテスト ===")
    
    # is_treatment_mentionのテスト
    test_cases_treatment = [
        ("糖尿病で通院中だけど、鼻水が止まらない", True),
        ("薬を飲んでいる", True),
        ("治療中です", True),
        ("頭痛がします", False),
    ]
    
    for user_text, expected in test_cases_treatment:
        result = is_treatment_mention(user_text)
        status = "✅" if result == expected else "❌"
        print(f"{status} is_treatment_mention: {user_text}")
        print(f"   期待値: {expected}, 実際の値: {result}")
        print()
    
    # has_specific_symptomのテスト
    test_cases_symptom = [
        ("心臓がドキドキする（動悸）", True),
        ("動悸", True),
        ("胸の痛み", True),
        ("肝臓を労わりたい", True),
        ("がんを完治したい", False),
    ]
    
    for user_text, expected in test_cases_symptom:
        result = has_specific_symptom(user_text)
        status = "✅" if result == expected else "❌"
        print(f"{status} has_specific_symptom: {user_text}")
        print(f"   期待値: {expected}, 実際の値: {result}")
        print()
    
    # is_medical_prevention_requestのテスト
    test_cases_prevention = [
        ("日焼けを予防したい", True),
        ("酔い止めを教えて", True),
        ("ビタミンを補給したい", True),
        ("風邪を予防したい", True),
        ("がんを予防したい", False),  # 重篤疾患の予防は除外
    ]
    
    for user_text, expected in test_cases_prevention:
        result = is_medical_prevention_request(user_text)
        status = "✅" if result == expected else "❌"
        print(f"{status} is_medical_prevention_request: {user_text}")
        print(f"   期待値: {expected}, 実際の値: {result}")
        print()
    
    # is_severe_disease_requestのテスト
    test_cases_severe = [
        ("がんを完治したい", True),
        ("糖尿病を完治したい", True),
        ("心筋梗塞を予防したい", True),
        ("糖尿病で通院中だけど、鼻水が止まらない", False),  # 治療中キーワードで除外
        ("心臓がドキドキする（動悸）", False),  # 症状キーワードで除外
    ]
    
    for user_text, expected in test_cases_severe:
        triage_result = {"category": "Other", "subcategory": "inappropriate_request/cure_prevention"}
        result = is_severe_disease_request(user_text, triage_result)
        status = "✅" if result == expected else "❌"
        print(f"{status} is_severe_disease_request: {user_text}")
        print(f"   期待値: {expected}, 実際の値: {result}")
        print()
    
    # is_psychiatric_disease_requestのテスト
    test_cases_psychiatric = [
        ("うつ病を完治したい", True),
        ("パニック障害を治したい", True),
        ("頭痛がします", False),
    ]
    
    for user_text, expected in test_cases_psychiatric:
        triage_result = {"category": "Other", "subcategory": "inappropriate_request/cure_prevention"}
        result = is_psychiatric_disease_request(user_text, triage_result)
        status = "✅" if result == expected else "❌"
        print(f"{status} is_psychiatric_disease_request: {user_text}")
        print(f"   期待値: {expected}, 実際の値: {result}")
        print()


def test_urgent_symptom_detection():
    """緊急症状検出のテスト"""
    print("=== 緊急症状検出のテスト ===")
    
    test_cases = [
        ("激しい胸痛があります", True),
        ("突然の呼吸困難", True),
        ("激しい動悸", True),
        ("頭痛がします", False),
    ]
    
    for user_text, expected_urgent in test_cases:
        try:
            result = check_heart_emergency_with_context(user_text)
            is_emergency = result.get('is_emergency', False)
            status = "✅" if is_emergency == expected_urgent else "❌"
            print(f"{status} 緊急症状検出: {user_text}")
            print(f"   期待値: {expected_urgent}, 実際の値: {is_emergency}")
            print(f"   理由: {result.get('reasoning', 'N/A')}")
            print()
        except Exception as e:
            print(f"❌ エラー: {e}")
            print()


def test_llm_triage_inappropriate_request():
    """LLMトリアージでの不適切な要求検出のテスト"""
    print("=== LLMトリアージでの不適切な要求検出のテスト ===")
    
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("⚠️ OPENAI_API_KEYが設定されていないため、このテストをスキップします")
        return
    
    client = OpenAI(api_key=api_key)
    
    test_cases = [
        "処方して",
        "痩せ薬を教えて",
        "惚れ薬を処方して",
        "覚醒剤を教えて"
    ]
    
    for user_text in test_cases:
        try:
            result = llm_triage(user_text, client, use_cache=False)
            category = result.get("category", "")
            subcategory = result.get("subcategory", "")
            
            print(f"✅ 入力: {user_text}")
            print(f"   カテゴリ: {category}, サブカテゴリ: {subcategory}")
            
            if category == "Other" and "inappropriate_request" in subcategory:
                print(f"   ✅ 不適切な要求として正しく検出されました")
            else:
                print(f"   ⚠️ 不適切な要求として検出されませんでした")
            print()
        except Exception as e:
            print(f"❌ エラー: {e}")
            print()


if __name__ == "__main__":
    print("不適切な要求検出機能のユニットテストを開始します\n")
    
    try:
        test_detect_inappropriate_request()
        test_generate_illegal_drug_rejection_message()
        test_helper_functions()
        test_urgent_symptom_detection()
        test_llm_triage_inappropriate_request()
        
        print("=" * 50)
        print("✅ すべてのテストが完了しました")
    except Exception as e:
        print(f"❌ テストエラー: {e}")
        import traceback
        traceback.print_exc()

