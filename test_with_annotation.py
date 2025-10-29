"""
アノテーションファイルを使用した正確な属性抽出テスト
事前に作成されたアノテーションファイルと比較して、正確な成功率を計算
"""

import csv
import os
import sys
from openai import OpenAI

def test_with_annotation():
    """アノテーションファイルを使用した正確なテスト"""
    
    print("="*80)
    print("アノテーションファイルを使用した属性抽出テスト")
    print("="*80)
    
    # テストモードを設定
    os.environ['TEST_MODE'] = '1'
    os.environ['OPENAI_API_KEY'] = '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'
    
    from medicine_logic import extract_user_attributes_multilingual
    
    client = OpenAI()
    
    # アノテーションファイルを読み込み
    annotation_file = '自然文_アノテーション.csv'
    if not os.path.exists(annotation_file):
        print(f"エラー: {annotation_file} が見つかりません")
        return
    
    # アノテーションデータを読み込み
    annotations = {}
    with open(annotation_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            annotations[row['test_id']] = row
    
    print(f"アノテーションデータ: {len(annotations)}件読み込み完了")
    
    # テスト実行
    results = []
    success_count = 0
    total_count = 0
    
    # 最初の50件をテスト（時間短縮のため）
    test_ids = list(annotations.keys())[:50]
    
    for i, test_id in enumerate(test_ids, 1):
        annotation = annotations[test_id]
        input_text = annotation['input_text']
        
        print(f"テスト中: {i}/50 - ID: {test_id}")
        
        try:
            # 属性抽出を実行
            extracted_attrs = extract_user_attributes_multilingual(input_text, client)
            
            # 各属性の正確性を評価
            accuracy = evaluate_attribute_accuracy(annotation, extracted_attrs)
            
            if accuracy['overall_success']:
                success_count += 1
            
            results.append({
                'test_id': test_id,
                'input_text': input_text,
                'annotation': annotation,
                'extracted': extracted_attrs,
                'accuracy': accuracy
            })
            
            total_count += 1
            
            # 進捗表示
            if i % 10 == 0:
                current_success_rate = success_count / i * 100
                print(f"進捗: {i}/50 - 成功率: {current_success_rate:.1f}%")
            
        except Exception as e:
            print(f"エラー (ID: {test_id}): {e}")
            total_count += 1
    
    # 結果サマリー
    final_success_rate = success_count / total_count * 100 if total_count > 0 else 0
    
    print("\n" + "="*80)
    print("テスト結果サマリー")
    print("="*80)
    print(f"総テストケース数: {total_count}")
    print(f"成功: {success_count}")
    print(f"失敗: {total_count - success_count}")
    print(f"成功率: {final_success_rate:.1f}%")
    
    # 詳細分析
    analyze_detailed_results(results)
    
    # 結果をCSVファイルに保存
    save_detailed_results(results)

def evaluate_attribute_accuracy(annotation, extracted):
    """各属性の正確性を評価"""
    
    accuracy = {
        'age': False,
        'gender': False,
        'pregnant': False,
        'breastfeeding': False,
        'allergies': False,
        'current_medications': False,
        'medical_history': False,
        'constitution': False,
        'doping_concern': False,
        'overall_success': False
    }
    
    # 年齢の評価
    expected_age = annotation['age']
    extracted_age = extracted.get('age')
    if expected_age == 'null' and (extracted_age is None or extracted_age == ''):
        accuracy['age'] = True
    elif expected_age != 'null' and str(extracted_age) == str(expected_age):
        accuracy['age'] = True
    
    # 性別の評価
    expected_gender = annotation['gender']
    extracted_gender = extracted.get('gender')
    if expected_gender == 'null' and (extracted_gender is None or extracted_gender == ''):
        accuracy['gender'] = True
    elif expected_gender != 'null' and extracted_gender == expected_gender:
        accuracy['gender'] = True
    
    # 妊娠中の評価
    expected_pregnant = annotation['pregnant'] == 'True'
    extracted_pregnant = extracted.get('pregnant', False)
    accuracy['pregnant'] = expected_pregnant == extracted_pregnant
    
    # 授乳中の評価
    expected_breastfeeding = annotation['breastfeeding'] == 'True'
    extracted_breastfeeding = extracted.get('breastfeeding', False)
    accuracy['breastfeeding'] = expected_breastfeeding == extracted_breastfeeding
    
    # アレルギーの評価
    expected_allergies = annotation['allergies']
    extracted_allergies = extracted.get('allergies', [])
    if expected_allergies == 'null' and (not extracted_allergies or extracted_allergies == []):
        accuracy['allergies'] = True
    elif expected_allergies != 'null' and extracted_allergies:
        # アレルギー情報が抽出されているかチェック
        accuracy['allergies'] = True
    
    # 服用中の薬の評価
    expected_meds = annotation['current_medications']
    extracted_meds = extracted.get('current_medications', [])
    if expected_meds == 'null' and (not extracted_meds or extracted_meds == []):
        accuracy['current_medications'] = True
    elif expected_meds != 'null' and extracted_meds:
        accuracy['current_medications'] = True
    
    # 既往症の評価
    expected_history = annotation['medical_history']
    extracted_history = extracted.get('medical_history', [])
    if expected_history == 'null' and (not extracted_history or extracted_history == []):
        accuracy['medical_history'] = True
    elif expected_history != 'null' and extracted_history:
        accuracy['medical_history'] = True
    
    # 体質の評価
    expected_constitution = annotation['constitution']
    extracted_constitution = extracted.get('constitution')
    if expected_constitution == 'null' and (extracted_constitution is None or extracted_constitution == ''):
        accuracy['constitution'] = True
    elif expected_constitution != 'null' and extracted_constitution:
        accuracy['constitution'] = True
    
    # ドーピング懸念の評価
    expected_doping = annotation['doping_concern'] == 'True'
    extracted_doping = extracted.get('doping_concern', False)
    accuracy['doping_concern'] = expected_doping == extracted_doping
    
    # 全体の成功判定（年齢と性別が正確に抽出できている場合）
    accuracy['overall_success'] = accuracy['age'] and accuracy['gender']
    
    return accuracy

def analyze_detailed_results(results):
    """詳細な結果分析"""
    
    print("\n" + "="*80)
    print("詳細分析")
    print("="*80)
    
    # 各属性の成功率
    attribute_success = {
        'age': 0,
        'gender': 0,
        'pregnant': 0,
        'breastfeeding': 0,
        'allergies': 0,
        'current_medications': 0,
        'medical_history': 0,
        'constitution': 0,
        'doping_concern': 0
    }
    
    total = len(results)
    
    for result in results:
        accuracy = result['accuracy']
        for attr in attribute_success:
            if accuracy[attr]:
                attribute_success[attr] += 1
    
    print("各属性の成功率:")
    for attr, count in attribute_success.items():
        success_rate = count / total * 100 if total > 0 else 0
        print(f"  {attr}: {count}/{total} ({success_rate:.1f}%)")
    
    # 失敗ケースの分析
    failed_cases = [r for r in results if not r['accuracy']['overall_success']]
    print(f"\n失敗ケース: {len(failed_cases)}件")
    
    if failed_cases:
        print("\n失敗例（最初の5件）:")
        for i, case in enumerate(failed_cases[:5], 1):
            print(f"{i}. ID: {case['test_id']}")
            print(f"   入力: {case['input_text']}")
            print(f"   期待: 年齢={case['annotation']['age']}, 性別={case['annotation']['gender']}")
            print(f"   実際: 年齢={case['extracted'].get('age')}, 性別={case['extracted'].get('gender')}")
            print()

def save_detailed_results(results):
    """詳細な結果をCSVファイルに保存"""
    
    output_file = 'log/detailed_test_results.csv'
    os.makedirs('log', exist_ok=True)
    
    with open(output_file, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        
        # ヘッダー
        headers = [
            'test_id', 'input_text', 'expected_age', 'extracted_age', 'age_correct',
            'expected_gender', 'extracted_gender', 'gender_correct',
            'expected_pregnant', 'extracted_pregnant', 'pregnant_correct',
            'expected_breastfeeding', 'extracted_breastfeeding', 'breastfeeding_correct',
            'expected_allergies', 'extracted_allergies', 'allergies_correct',
            'expected_medications', 'extracted_medications', 'medications_correct',
            'expected_history', 'extracted_history', 'history_correct',
            'expected_constitution', 'extracted_constitution', 'constitution_correct',
            'expected_doping', 'extracted_doping', 'doping_correct',
            'overall_success'
        ]
        writer.writerow(headers)
        
        # データ
        for result in results:
            annotation = result['annotation']
            extracted = result['extracted']
            accuracy = result['accuracy']
            
            row = [
                result['test_id'],
                result['input_text'],
                annotation['age'],
                extracted.get('age', ''),
                accuracy['age'],
                annotation['gender'],
                extracted.get('gender', ''),
                accuracy['gender'],
                annotation['pregnant'],
                extracted.get('pregnant', ''),
                accuracy['pregnant'],
                annotation['breastfeeding'],
                extracted.get('breastfeeding', ''),
                accuracy['breastfeeding'],
                annotation['allergies'],
                '; '.join(extracted.get('allergies', [])),
                accuracy['allergies'],
                annotation['current_medications'],
                '; '.join(extracted.get('current_medications', [])),
                accuracy['current_medications'],
                annotation['medical_history'],
                '; '.join(extracted.get('medical_history', [])),
                accuracy['medical_history'],
                annotation['constitution'],
                extracted.get('constitution', ''),
                accuracy['constitution'],
                annotation['doping_concern'],
                extracted.get('doping_concern', ''),
                accuracy['doping_concern'],
                accuracy['overall_success']
            ]
            writer.writerow(row)
    
    print(f"\n詳細結果を {output_file} に保存しました")

if __name__ == "__main__":
    test_with_annotation()
