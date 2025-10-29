"""
総合評価システム
属性抽出・症状分析・推奨医薬品の精度を評価
"""

import os
import sys
import csv
import json
import time
from datetime import datetime
from openai import OpenAI

# Windowsでの文字化け対策
if sys.platform.startswith('win'):
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.detach())
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.detach())

def load_test_data():
    """テストデータを読み込み"""
    # 自然文.csvを読み込み
    natural_language_data = []
    with open('自然文.csv', 'r', encoding='utf-8-sig') as f:
        reader = csv.reader(f, delimiter='\t')
        for row in reader:
            if len(row) >= 2:
                natural_language_data.append({
                    'id': int(row[0]),
                    'text': row[1]
                })
    
    # 自然文_アノテーション.csvを読み込み
    annotation_data = {}
    with open('自然文_アノテーション.csv', 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            annotation_data[int(row['test_id'])] = row
    
    return natural_language_data, annotation_data

def evaluate_attribute_extraction(extracted, ground_truth):
    """属性抽出の精度を評価"""
    results = {}
    
    # 年齢の評価
    extracted_age = extracted.get('age')
    ground_age = ground_truth.get('age')
    if ground_age and ground_age != 'null':
        try:
            ground_age = int(ground_age)
            results['age'] = extracted_age == ground_age
        except:
            results['age'] = False
    else:
        results['age'] = extracted_age is None
    
    # 性別の評価
    extracted_gender = extracted.get('gender')
    ground_gender = ground_truth.get('gender')
    if ground_gender and ground_gender != 'null':
        results['gender'] = extracted_gender == ground_gender
    else:
        results['gender'] = extracted_gender is None
    
    # 妊娠の評価
    extracted_pregnant = extracted.get('pregnant')
    ground_pregnant = ground_truth.get('pregnant')
    if ground_pregnant and ground_pregnant != 'null':
        ground_pregnant = ground_pregnant.lower() == 'true'
        results['pregnant'] = extracted_pregnant == ground_pregnant
    else:
        results['pregnant'] = extracted_pregnant == False
    
    # 授乳の評価
    extracted_breastfeeding = extracted.get('breastfeeding')
    ground_breastfeeding = ground_truth.get('breastfeeding')
    if ground_breastfeeding and ground_breastfeeding != 'null':
        ground_breastfeeding = ground_breastfeeding.lower() == 'true'
        results['breastfeeding'] = extracted_breastfeeding == ground_breastfeeding
    else:
        results['breastfeeding'] = extracted_breastfeeding == False
    
    # アレルギーの評価
    extracted_allergies = extracted.get('allergies', [])
    ground_allergies = ground_truth.get('allergies')
    if ground_allergies and ground_allergies != 'null':
        ground_allergies = ground_allergies.split(';') if ground_allergies else []
        ground_allergies = [a.strip() for a in ground_allergies if a.strip()]
        
        # 適合率・再現率・F1スコアを計算
        if extracted_allergies and ground_allergies:
            true_positives = len(set(extracted_allergies) & set(ground_allergies))
            precision = true_positives / len(extracted_allergies) if extracted_allergies else 0
            recall = true_positives / len(ground_allergies) if ground_allergies else 0
            f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
            results['allergies'] = {
                'precision': precision,
                'recall': recall,
                'f1': f1,
                'exact_match': set(extracted_allergies) == set(ground_allergies)
            }
        else:
            results['allergies'] = {
                'precision': 0,
                'recall': 0,
                'f1': 0,
                'exact_match': extracted_allergies == ground_allergies
            }
    else:
        results['allergies'] = {
            'precision': 1.0 if not extracted_allergies else 0,
            'recall': 1.0 if not extracted_allergies else 0,
            'f1': 1.0 if not extracted_allergies else 0,
            'exact_match': not extracted_allergies
        }
    
    return results

def process_batch(batch_data, annotation_data, client):
    """バッチデータを処理"""
    results = {
        'attribute_extraction': {
            'age': {'correct': 0, 'total': 0},
            'gender': {'correct': 0, 'total': 0},
            'pregnant': {'correct': 0, 'total': 0},
            'breastfeeding': {'correct': 0, 'total': 0},
            'allergies': {'precision': [], 'recall': [], 'f1': [], 'exact_match': 0, 'total': 0}
        },
        'processing_time': [],
        'errors': 0,
        'total': len(batch_data)
    }
    
    # テストモードを設定
    os.environ['TEST_MODE'] = '1'
    os.environ['OPENAI_API_KEY'] = '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'
    
    from medicine_logic import extract_user_attributes_multilingual
    
    for item in batch_data:
        start_time = time.time()
        
        try:
            # 属性抽出を実行
            extracted = extract_user_attributes_multilingual(item['text'], client)
            
            # アノテーションデータと比較
            if item['id'] in annotation_data:
                ground_truth = annotation_data[item['id']]
                eval_results = evaluate_attribute_extraction(extracted, ground_truth)
                
                # 結果を集計
                for attr, result in eval_results.items():
                    if attr == 'allergies':
                        results['attribute_extraction']['allergies']['precision'].append(result['precision'])
                        results['attribute_extraction']['allergies']['recall'].append(result['recall'])
                        results['attribute_extraction']['allergies']['f1'].append(result['f1'])
                        results['attribute_extraction']['allergies']['total'] += 1
                        if result['exact_match']:
                            results['attribute_extraction']['allergies']['exact_match'] += 1
                    else:
                        results['attribute_extraction'][attr]['total'] += 1
                        if result:
                            results['attribute_extraction'][attr]['correct'] += 1
            
            processing_time = time.time() - start_time
            results['processing_time'].append(processing_time)
            
        except Exception as e:
            results['errors'] += 1
            print(f"エラー (ID {item['id']}): {e}")
    
    return results

def merge_results(main_results, batch_results):
    """バッチ結果をメイン結果にマージ"""
    for attr, metrics in batch_results['attribute_extraction'].items():
        if attr == 'allergies':
            for metric in ['precision', 'recall', 'f1']:
                main_results['attribute_extraction'][attr][metric].extend(metrics[metric])
            main_results['attribute_extraction'][attr]['exact_match'] += metrics['exact_match']
            main_results['attribute_extraction'][attr]['total'] += metrics['total']
        else:
            main_results['attribute_extraction'][attr]['correct'] += metrics['correct']
            main_results['attribute_extraction'][attr]['total'] += metrics['total']
    
    main_results['processing_time'].extend(batch_results['processing_time'])
    main_results['errors'] += batch_results['errors']
    main_results['total'] += batch_results['total']

def evaluate_system(test_data, annotation_data, batch_size=200):
    """総合評価を実施"""
    print("="*80)
    print("総合評価システム - 属性抽出精度測定")
    print("="*80)
    
    # OpenAIクライアントを初期化
    os.environ['OPENAI_API_KEY'] = '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'
    client = OpenAI()
    
    # 結果格納用
    results = {
        'attribute_extraction': {
            'age': {'correct': 0, 'total': 0},
            'gender': {'correct': 0, 'total': 0},
            'pregnant': {'correct': 0, 'total': 0},
            'breastfeeding': {'correct': 0, 'total': 0},
            'allergies': {'precision': [], 'recall': [], 'f1': [], 'exact_match': 0, 'total': 0}
        },
        'processing_time': [],
        'errors': 0,
        'total': 0
    }
    
    # 200件ずつバッチ処理
    for i in range(0, len(test_data), batch_size):
        batch_num = i // batch_size + 1
        batch = test_data[i:i+batch_size]
        
        print(f"\nバッチ {batch_num}: ID {i+1}-{min(i+batch_size, len(test_data))} ({len(batch)}件)")
        
        batch_results = process_batch(batch, annotation_data, client)
        merge_results(results, batch_results)
        
        # 進捗表示
        print(f"  処理完了: {batch_results['total']}件")
        print(f"  エラー: {batch_results['errors']}件")
        if batch_results['processing_time']:
            avg_time = sum(batch_results['processing_time']) / len(batch_results['processing_time'])
            print(f"  平均処理時間: {avg_time:.2f}秒/件")
    
    return results

def generate_report(results):
    """評価レポートを生成"""
    print("\n" + "="*80)
    print("評価レポート")
    print("="*80)
    
    print(f"総テスト件数: {results['total']}件")
    print(f"処理成功: {results['total'] - results['errors']}件 ({((results['total'] - results['errors']) / results['total'] * 100):.1f}%)")
    print(f"エラー件数: {results['errors']}件 ({results['errors'] / results['total'] * 100:.1f}%)")
    
    print("\n【属性抽出精度】")
    
    # 各属性の精度を計算
    for attr, metrics in results['attribute_extraction'].items():
        if attr == 'allergies':
            if metrics['total'] > 0:
                avg_precision = sum(metrics['precision']) / len(metrics['precision'])
                avg_recall = sum(metrics['recall']) / len(metrics['recall'])
                avg_f1 = sum(metrics['f1']) / len(metrics['f1'])
                exact_match_rate = metrics['exact_match'] / metrics['total'] * 100
                
                print(f"- {attr}:")
                print(f"  適合率: {avg_precision:.1%}")
                print(f"  再現率: {avg_recall:.1%}")
                print(f"  F1スコア: {avg_f1:.1%}")
                print(f"  完全一致: {exact_match_rate:.1%}")
        else:
            if metrics['total'] > 0:
                accuracy = metrics['correct'] / metrics['total'] * 100
                print(f"- {attr}: {accuracy:.1%} ({metrics['correct']}/{metrics['total']})")
    
    # 処理時間の統計
    if results['processing_time']:
        avg_time = sum(results['processing_time']) / len(results['processing_time'])
        min_time = min(results['processing_time'])
        max_time = max(results['processing_time'])
        print(f"\n【処理時間】")
        print(f"平均: {avg_time:.2f}秒/件")
        print(f"最小: {min_time:.2f}秒/件")
        print(f"最大: {max_time:.2f}秒/件")
    
    # 改善が必要な項目を特定
    print(f"\n【改善が必要な項目】")
    improvement_items = []
    
    for attr, metrics in results['attribute_extraction'].items():
        if attr == 'allergies':
            if metrics['total'] > 0:
                avg_f1 = sum(metrics['f1']) / len(metrics['f1'])
                if avg_f1 < 0.8:
                    improvement_items.append(f"{attr} (F1: {avg_f1:.1%})")
        else:
            if metrics['total'] > 0:
                accuracy = metrics['correct'] / metrics['total']
                if accuracy < 0.8:
                    improvement_items.append(f"{attr} ({accuracy:.1%})")
    
    if improvement_items:
        for i, item in enumerate(improvement_items, 1):
            print(f"{i}. {item}")
    else:
        print("すべての項目が目標精度を達成しています。")
    
    # 結果をファイルに保存
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = f"log/evaluation_report_{timestamp}.json"
    
    os.makedirs("log", exist_ok=True)
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print(f"\n詳細結果を保存しました: {report_file}")

def main():
    """メイン実行関数"""
    print("総合評価システムを開始します...")
    
    # テストデータを読み込み
    print("テストデータを読み込み中...")
    test_data, annotation_data = load_test_data()
    print(f"自然文データ: {len(test_data)}件")
    print(f"アノテーションデータ: {len(annotation_data)}件")
    
    # 評価を実行
    results = evaluate_system(test_data, annotation_data, batch_size=200)
    
    # レポートを生成
    generate_report(results)
    
    print("\n評価完了しました。")

if __name__ == "__main__":
    main()
