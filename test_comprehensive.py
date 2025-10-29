"""
医薬品推奨システム - 包括的テストスイート
統合されたテストファイル（全機能をカバー）
"""

import sys
import os

# 現在のディレクトリをパスに追加
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# UTF-8エンコーディングを明示的に設定
if sys.platform.startswith('win'):
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.detach())
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.detach())

from medicine_logic import (
    rule_based_medicine_recommendation, 
    analyze_symptoms_and_medicine_type,
    comprehensive_medicine_recommendation,
    client
)

def print_result(result, test_name):
    """テスト結果の表示"""
    print(f"\n{'='*80}")
    print(f"結果: {test_name}")
    print(f"{'='*80}")
    print(f"ステータス: {result.get('status')}")
    
    if result.get('status') == 'success':
        medicines = result.get('recommended_medicines', [])
        print(f"推奨医薬品数: {len(medicines)}")
        
        for i, med in enumerate(medicines[:3], 1):
            print(f"\n{i}. {med.get('product_name')} ({med.get('manufacturer')})")
            print(f"   スコア: {med.get('score', 0):.3f}")
            print(f"   推奨理由: {med.get('reason', 'なし')}")
            print(f"   効能効果: {med.get('efficacy', '')[:100]}...")
        
        if result.get('usage_notes'):
            print(f"\n使用上の注意: {result.get('usage_notes')}")
    else:
        print(f"エラー: {result.get('error', '不明なエラー')}")

def test_rule_based_cold():
    """テスト1: 風邪症状（ルールベース）"""
    print("\n" + "="*80)
    print("テスト1: 風邪症状（ルールベース推奨）")
    print("="*80)
    
    user_text = "昨日から喉が痛くて、咳も出ます。少し熱っぽいです。"
    user_info = {
        "age": 30,
        "gender": "男性",
        "pregnant": False,
        "breastfeeding": False,
        "current_medications": [],
        "allergies": []
    }
    
    result = rule_based_medicine_recommendation(user_text, user_info, client)
    print_result(result, "風邪症状")

def test_rule_based_headache():
    """テスト2: 頭痛症状（ルールベース）"""
    print("\n" + "="*80)
    print("テスト2: 頭痛症状（ルールベース推奨）")
    print("="*80)
    
    user_text = "頭が痛いです。昨日の夕方から続いています。"
    user_info = {
        "age": 25,
        "gender": "女性",
        "pregnant": False,
        "breastfeeding": False,
        "current_medications": [],
        "allergies": []
    }
    
    result = rule_based_medicine_recommendation(user_text, user_info, client)
    print_result(result, "頭痛症状")

def test_rule_based_nasal():
    """テスト3: 鼻炎症状（ルールベース）"""
    print("\n" + "="*80)
    print("テスト3: 鼻炎症状（ルールベース推奨）")
    print("="*80)
    
    user_text = "鼻水とくしゃみが止まりません。目もかゆいです。"
    user_info = {
        "age": 35,
        "gender": "女性",
        "pregnant": False,
        "breastfeeding": False,
        "current_medications": [],
        "allergies": []
    }
    
    result = rule_based_medicine_recommendation(user_text, user_info, client)
    print_result(result, "鼻炎症状")

def test_hybrid_medicine_type():
    """テスト4: 医薬品種類判定（ハイブリッド）"""
    print("\n" + "="*80)
    print("テスト4: 医薬品種類判定（ハイブリッドシステム）")
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
                print(f"  → アルゴリズム: AI推奨（柔軟性重視）")
        except Exception as e:
            print(f"  → エラー: {e}")

def test_missing_attributes():
    """テスト5: 属性不足時の質問機能"""
    print("\n" + "="*80)
    print("テスト5: 属性不足時の質問機能")
    print("="*80)
    
    user_text = "頭が痛いです。"
    user_info = {
        "age": None,           # 不足
        "gender": None,        # 不足
        "pregnant": None,      # 不足
        "breastfeeding": None, # 不足
        "current_medications": [],
        "allergies": []
    }
    
    result = rule_based_medicine_recommendation(user_text, user_info, client)
    print_result(result, "属性不足時")

def test_safety_checks():
    """テスト6: 安全性チェック"""
    print("\n" + "="*80)
    print("テスト6: 安全性チェック")
    print("="*80)
    
    # 年齢制限テスト
    user_text = "頭が痛いです。"
    user_info = {
        "age": 5,  # 7歳未満
        "gender": "男性",
        "pregnant": False,
        "breastfeeding": False,
        "current_medications": [],
        "allergies": []
    }
    
    result = rule_based_medicine_recommendation(user_text, user_info, client)
    print_result(result, "年齢制限チェック（5歳）")
    
    # 妊娠中テスト
    user_info["age"] = 30
    user_info["pregnant"] = True
    
    result = rule_based_medicine_recommendation(user_text, user_info, client)
    print_result(result, "妊娠中チェック")

def test_red_flag_symptoms():
    """テスト7: Red Flag症状検出"""
    print("\n" + "="*80)
    print("テスト7: Red Flag症状検出")
    print("="*80)
    
    user_text = "39度の高熱が3日続いています。呼吸も苦しいです。"
    user_info = {
        "age": 30,
        "gender": "男性",
        "pregnant": False,
        "breastfeeding": False,
        "current_medications": [],
        "allergies": []
    }
    
    result = rule_based_medicine_recommendation(user_text, user_info, client)
    print_result(result, "Red Flag症状")

def test_comprehensive_system():
    """テスト8: 包括的システムテスト"""
    print("\n" + "="*80)
    print("テスト8: 包括的システムテスト")
    print("="*80)
    
    user_text = "喉が痛くて咳が出ます。少し熱もあります。"
    user_info = {
        "age": 28,
        "gender": "女性",
        "pregnant": False,
        "breastfeeding": False,
        "current_medications": [],
        "allergies": []
    }
    
    result = comprehensive_medicine_recommendation(user_text, user_info, client)
    print_result(result, "包括的システム")

def test_age_expression_variations():
    """テスト: 年齢表現のバリエーション"""
    print("\n" + "="*80)
    print("テスト: 年齢表現のバリエーション")
    print("="*80)
    
    from medicine_logic import parse_age_expression
    
    test_cases = [
        ("30歳", 30),
        ("30代", 35),
        ("25 years old", 25),
        ("40代女性", 45),
        ("20代男性", 25),
        ("50代", 55),
        ("年齢は30歳です", 30),
        ("私は30代です", 35),
    ]
    
    for text, expected in test_cases:
        result = parse_age_expression(text)
        status = "OK" if result == expected else "NG"
        print(f"{status} '{text}' -> {result} (期待値: {expected})")

def test_attribute_extraction_from_csv():
    """テスト: CSV全500件の属性抽出テスト"""
    print("\n" + "="*80)
    print("テスト: CSV全500件の属性抽出テスト")
    print("="*80)
    
    import csv
    import os
    from medicine_logic import extract_user_attributes_multilingual
    
    # テストモードを設定（ログ出力を抑制）
    os.environ['TEST_MODE'] = '1'
    
    # OPENAI_API_KEYを設定
    os.environ['OPENAI_API_KEY'] = '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'
    
    csv_file = '自然文.csv'
    if not os.path.exists(csv_file):
        print(f"NG CSVファイルが見つかりません: {csv_file}")
        return
    
    success_count = 0
    error_count = 0
    results = []
    
    try:
        with open(csv_file, 'r', encoding='utf-8-sig') as f:
            reader = csv.reader(f, delimiter='\t')
            all_rows = list(reader)
        
        # バッチ処理（50件ずつ）
        batch_size = 50
        total_batches = (len(all_rows) + batch_size - 1) // batch_size
        
        for batch_num in range(total_batches):
            start_idx = batch_num * batch_size
            end_idx = min(start_idx + batch_size, len(all_rows))
            batch_rows = all_rows[start_idx:end_idx]
            
            print(f"\nバッチ {batch_num + 1}/{total_batches} 処理中...")
            
            for i, row in enumerate(batch_rows, start_idx + 1):
                if len(row) < 2:
                    continue
                    
                test_id, user_text = row[0], row[1]
                
                try:
                    # 属性抽出を実行
                    extracted_attrs = extract_user_attributes_multilingual(user_text, client)
                    
                    # 成功判定（年齢 AND 性別の両方が抽出できた場合のみ成功）
                    has_age = extracted_attrs.get('age') and extracted_attrs.get('age') is not None
                    has_gender = extracted_attrs.get('gender') and extracted_attrs.get('gender') != ''
                    
                    if has_age and has_gender:
                        success_count += 1
                        status = "OK"
                    else:
                        error_count += 1
                        status = "NG"
                    
                    results.append({
                        'test_id': test_id,
                        'input': user_text,
                        'extracted_attrs': extracted_attrs,
                        'status': status
                    })
                    
                except Exception as e:
                    error_count += 1
                    status = "NG"
                    results.append({
                        'test_id': test_id,
                        'input': user_text,
                        'extracted_attrs': {},
                        'status': status
                    })
                
                # 進捗表示（10件ごと）
                if i % 10 == 0:
                    success_rate = success_count/i*100 if i > 0 else 0
                    print(f"[{i}/500] 成功: {success_count}, 失敗: {error_count} ({success_rate:.1f}%)")
            
            # バッチ間で少し待機（レート制限回避）
            if batch_num < total_batches - 1:
                import time
                time.sleep(1)
    
    except Exception as e:
        print(f"NG CSV読み込みエラー: {e}")
        return
    
    # 結果サマリー
    print(f"\n{'='*80}")
    print("属性抽出テスト結果サマリー")
    print(f"{'='*80}")
    print(f"総テストケース数: {len(results)}")
    print(f"成功: {success_count}")
    print(f"失敗: {error_count}")
    print(f"成功率: {success_count/len(results)*100:.1f}%")
    
    # logディレクトリが存在しない場合は作成
    os.makedirs('log', exist_ok=True)
    
    # 詳細ログファイルに結果を保存
    import time
    with open('log/attribute_test_results.log', 'w', encoding='utf-8') as log_file:
        log_file.write("属性抽出テスト詳細結果\n")
        log_file.write("="*80 + "\n")
        log_file.write(f"実行日時: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        log_file.write(f"総テストケース数: {len(results)}\n")
        log_file.write(f"成功: {success_count}\n")
        log_file.write(f"失敗: {error_count}\n")
        log_file.write(f"成功率: {success_count/len(results)*100:.1f}%\n\n")
        
        for result in results:
            log_file.write(f"テストID: {result['test_id']}\n")
            log_file.write(f"入力: {result['input']}\n")
            log_file.write(f"抽出結果: {result['extracted_attrs']}\n")
            log_file.write(f"ステータス: {result['status']}\n")
            log_file.write("-" * 80 + "\n")
    
    # 結果をCSVファイルに保存
    import csv
    with open('log/attribute_test_report.csv', 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['test_id', 'input', 'age', 'gender', 'pregnant', 'breastfeeding', 'allergies', 'current_medications', 'medical_history', 'doping_concern', 'constitution', 'status'])
        for result in results:
            attrs = result['extracted_attrs']
            writer.writerow([
                result['test_id'],
                result['input'],
                attrs.get('age', ''),
                attrs.get('gender', ''),
                attrs.get('pregnant', ''),
                attrs.get('breastfeeding', ''),
                ', '.join(attrs.get('allergies', [])),
                ', '.join(attrs.get('current_medications', [])),
                ', '.join(attrs.get('medical_history', [])),
                attrs.get('doping_concern', ''),
                attrs.get('constitution', ''),
                result['status']
            ])
    
    print(f"詳細結果を log/attribute_test_report.csv に保存しました")
    print(f"詳細ログを log/attribute_test_results.log に保存しました")

def test_personalized_advice_generation():
    """テスト: 個別アドバイス生成テスト"""
    print("\n" + "="*80)
    print("テスト: 個別アドバイス生成テスト")
    print("="*80)
    
    from app import generate_personalized_advice
    from openai import OpenAI
    
    # OPENAI_API_KEYを設定
    os.environ['OPENAI_API_KEY'] = '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'
    
    client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
    
    test_cases = [
        {
            'user_attrs': {'age': 30, 'gender': '女性', 'constitution': '冷え性'},
            'medicines': [{'product_name': 'ルルアタックＴＲ'}, {'product_name': '新コンタックかぜＥＸ'}],
            'symptoms': ['頭痛', 'むくみ']
        },
        {
            'user_attrs': {'age': 25, 'gender': '男性', 'doping_concern': True},
            'medicines': [{'product_name': 'ベンザブロックＬ錠'}],
            'symptoms': ['発熱', '咳']
        },
        {
            'user_attrs': {'age': 40, 'gender': '女性', 'pregnant': True, 'medical_history': ['高血圧']},
            'medicines': [{'product_name': 'ルルアタックＴＲ'}],
            'symptoms': ['頭痛']
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n--- テストケース {i} ---")
        print(f"ユーザー属性: {test_case['user_attrs']}")
        print(f"症状: {test_case['symptoms']}")
        
        try:
            advice = generate_personalized_advice(
                test_case['user_attrs'],
                test_case['medicines'],
                test_case['symptoms'],
                client
            )
            print(f"OK 生成されたアドバイス: {advice}")
        except Exception as e:
            print(f"NG エラー: {e}")

def test_complex_attribute_combinations():
    """テスト: 複合属性パターンのテスト"""
    print("\n" + "="*80)
    print("テスト: 複合属性パターンのテスト")
    print("="*80)
    
    from medicine_logic import extract_user_attributes_multilingual
    
    test_cases = [
        "30代女性で冷え性です。生理前から頭痛とむくみがひどいです。",
        "40代男性で糖尿病の薬を飲んでいます。喉が痛くて咳が出ます。",
        "20代女性でアレルギー体質です。春先から鼻がムズムズして止まりません。",
        "50代男性で高血圧です。肩こりと頭痛がひどいです。",
        "60代女性で便秘しやすく、最近お腹が張って苦しいです。",
        "妊娠中の女性です。鼻づまりがつらいのですが薬を使っても大丈夫ですか。",
        "授乳中の母親です。喉が痛くて咳が出ます。",
        "30代男性でよく胃が荒れます。食後に胃もたれがします。",
        "50代女性で更年期に入っていて、最近頭痛とイライラが強いです。",
        "運動をしているので、ドーピングに注意したいです。頭痛がひどいです。"
    ]
    
    for i, test_text in enumerate(test_cases, 1):
        print(f"\n--- テストケース {i} ---")
        print(f"入力: {test_text}")
        
        try:
            extracted_attrs = extract_user_attributes_multilingual(test_text, client)
            print(f"抽出結果:")
            for key, value in extracted_attrs.items():
                if key != 'detected_language':
                    print(f"  {key}: {value}")
        except Exception as e:
            print(f"NG エラー: {e}")

def test_strict_attribute_extraction():
    """テスト: 厳格な基準での属性抽出テスト"""
    print("\n" + "="*80)
    print("テスト: 厳格な基準での属性抽出テスト")
    print("="*80)
    
    # テストモードを設定
    os.environ['TEST_MODE'] = '1'
    os.environ['OPENAI_API_KEY'] = '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'
    
    from medicine_logic import extract_user_attributes_multilingual
    from openai import OpenAI
    
    client = OpenAI()
    
    # 厳格なテストケース
    strict_test_cases = [
        "30代女性で冷え性です。生理前から頭痛とむくみがひどいです。",
        "25歳の男性です。風邪をひいて熱があります。",
        "40代女性で妊娠中です。鼻づまりがつらいです。",
        "60歳の男性で糖尿病の薬を飲んでいます。",
        "20代女性で授乳中です。肩こりがひどいです。"
    ]
    
    success_count = 0
    total_count = len(strict_test_cases)
    
    for i, test_text in enumerate(strict_test_cases, 1):
        try:
            extracted_attrs = extract_user_attributes_multilingual(test_text, client)
            
            # 厳格な判定：年齢 AND 性別の両方が必要
            has_age = extracted_attrs.get('age') and extracted_attrs.get('age') is not None
            has_gender = extracted_attrs.get('gender') and extracted_attrs.get('gender') != ''
            
            if has_age and has_gender:
                success_count += 1
                status = "OK"
            else:
                status = "NG"
            
            print(f"{status} [{i}/{total_count}] {test_text}")
            print(f"    年齢: {extracted_attrs.get('age', 'N/A')}, 性別: {extracted_attrs.get('gender', 'N/A')}")
            
        except Exception as e:
            print(f"NG [{i}/{total_count}] エラー: {e}")
    
    success_rate = success_count / total_count * 100
    print(f"\n厳格テスト結果: {success_count}/{total_count} ({success_rate:.1f}%)")

def test_edge_cases():
    """テスト: エッジケース（曖昧な表現、複雑な文）のテスト"""
    print("\n" + "="*80)
    print("テスト: エッジケーステスト")
    print("="*80)
    
    # テストモードを設定
    os.environ['TEST_MODE'] = '1'
    os.environ['OPENAI_API_KEY'] = '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'
    
    from medicine_logic import extract_user_attributes_multilingual
    from openai import OpenAI
    
    client = OpenAI()
    
    # エッジケース
    edge_cases = [
        "おばあちゃんが風邪をひきました。",  # 年齢不明、性別推測
        "子どもが熱を出しています。",  # 年齢・性別不明
        "30代くらいの女性だと思います。",  # 曖昧な表現
        "たぶん男性で、年齢は40歳くらいです。",  # 推測表現
        "妊娠しているかもしれません。",  # 妊娠状況不明
    ]
    
    success_count = 0
    total_count = len(edge_cases)
    
    for i, test_text in enumerate(edge_cases, 1):
        try:
            extracted_attrs = extract_user_attributes_multilingual(test_text, client)
            
            # エッジケースでは年齢 OR 性別のいずれかが抽出できれば成功とする
            has_age = extracted_attrs.get('age') and extracted_attrs.get('age') is not None
            has_gender = extracted_attrs.get('gender') and extracted_attrs.get('gender') != ''
            
            if has_age or has_gender:
                success_count += 1
                status = "OK"
            else:
                status = "NG"
            
            print(f"{status} [{i}/{total_count}] {test_text}")
            print(f"    年齢: {extracted_attrs.get('age', 'N/A')}, 性別: {extracted_attrs.get('gender', 'N/A')}")
            
        except Exception as e:
            print(f"NG [{i}/{total_count}] エラー: {e}")
    
    success_rate = success_count / total_count * 100
    print(f"\nエッジケーステスト結果: {success_count}/{total_count} ({success_rate:.1f}%)")

def main():
    """メイン実行関数"""
    print("\n" + "="*80)
    print("医薬品推奨システム - 包括的テストスイート")
    print("="*80)
    
    try:
        # 全テストケースを実行
        test_rule_based_cold()
        test_rule_based_headache()
        test_rule_based_nasal()
        test_hybrid_medicine_type()
        test_missing_attributes()
        test_safety_checks()
        test_red_flag_symptoms()
        test_comprehensive_system()
        
        # 新しいテストケース
        test_age_expression_variations()
        test_complex_attribute_combinations()
        test_personalized_advice_generation()
        
        # 段階的テスト
        test_strict_attribute_extraction()
        test_edge_cases()
        
        # CSV全500件のテスト（時間がかかるため最後に実行）
        print("\n注意: CSV全500件のテストを実行します（時間がかかります）...")
        test_attribute_extraction_from_csv()
        
        print("\n" + "="*80)
        print("OK 全テスト完了")
        print("="*80)
        
    except Exception as e:
        print(f"\nNG テスト実行中にエラーが発生しました: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
