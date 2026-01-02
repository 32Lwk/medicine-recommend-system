"""
テストログから推奨医薬品を詳細に分析するスクリプト
"""
import re
import json
from collections import defaultdict, Counter
import pandas as pd

def analyze_test_log_detailed(log_file_path, medicine_csv_path):
    """テストログを詳細に分析して推奨医薬品のパターンを抽出"""
    
    # データ構造
    recommendations_by_input = []  # 入力ごとの推奨
    symptom_medicine_map = defaultdict(list)  # 症状→推奨医薬品
    medicine_details = {}  # 医薬品の詳細情報
    
    # 医薬品データを読み込み
    medicine_df = pd.read_csv(medicine_csv_path)
    
    with open(log_file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    current_test = None
    current_input = None
    detected_symptoms = None
    recommended_medicines = None
    
    for i, line in enumerate(lines):
        # テストケース番号と入力の検出
        test_match = re.match(r'INFO:__main__:test_(\d+)\|(.+?)\|', line)
        if test_match:
            current_test = test_match.group(1)
            current_input = test_match.group(2)
            detected_symptoms = None
            recommended_medicines = None
            continue
        
        # 症状検出結果の検出
        if '症状検出完了:' in line:
            symptom_match = re.search(r'症状検出完了:\s*(.+?)(?:\s*\(|$)', line)
            if symptom_match:
                symptoms_str = symptom_match.group(1).strip()
                if symptoms_str != '該当なし':
                    detected_symptoms = [s.strip() for s in symptoms_str.split(',')]
        
        # 推奨医薬品の検出
        if '出力: 推奨医薬品:' in line:
            medicines_match = re.search(r'推奨医薬品:\s*(.+?)(?:\n|$)', line)
            if medicines_match:
                medicines_str = medicines_match.group(1).strip()
                if medicines_str != '該当なし':
                    recommended_medicines = [m.strip() for m in medicines_str.split(',')]
                    
                    # データを記録
                    if current_input and detected_symptoms and recommended_medicines:
                        recommendations_by_input.append({
                            'test_number': current_test,
                            'input': current_input,
                            'symptoms': detected_symptoms,
                            'medicines': recommended_medicines
                        })
                        
                        # 症状ごとにマッピング
                        for symptom in detected_symptoms:
                            symptom_medicine_map[symptom].extend(recommended_medicines)
    
    # 医薬品の詳細情報を取得
    all_medicines = set()
    for entry in recommendations_by_input:
        all_medicines.update(entry['medicines'])
    
    for medicine_name in all_medicines:
        # 部分一致で検索
        matches = medicine_df[medicine_df['製品名'].str.contains(medicine_name, na=False, regex=False)]
        if len(matches) > 0:
            # 最も長い名前に一致するものを返す
            matches = matches.copy()
            matches['name_length'] = matches['製品名'].str.len()
            matches = matches.sort_values('name_length', ascending=False)
            row = matches.iloc[0]
            medicine_details[medicine_name] = {
                'product_name': row.get('製品名', ''),
                'manufacturer': row.get('メーカー名', ''),
                'classification': row.get('分類', ''),
                'medicine_type': row.get('医薬品の種類', ''),
                'efficacy': row.get('効能効果', ''),
                'age_restriction': row.get('年齢制限', ''),
                'ingredients': row.get('成分', '')
            }
    
    return recommendations_by_input, symptom_medicine_map, medicine_details

def analyze_medicine_advantages(medicine_name, medicine_info, symptom, all_recommendations, medicine_details):
    """医薬品の優位性を分析"""
    advantages = []
    
    if not medicine_info:
        return advantages
    
    efficacy = medicine_info.get('efficacy', '')
    ingredients = medicine_info.get('ingredients', '')
    medicine_type = medicine_info.get('medicine_type', '')
    classification = medicine_info.get('classification', '')
    
    # 効能効果の確認
    if symptom in efficacy or any(s in efficacy for s in [symptom, symptom.replace('の', ''), symptom.replace('が', '')]):
        advantages.append({
            'type': 'efficacy_match',
            'description': f'効能効果に「{symptom}」が明記されている'
        })
    
    # 成分による優位性
    if 'アセトアミノフェン' in ingredients:
        if symptom in ['頭痛', '発熱']:
            advantages.append({
                'type': 'ingredient_advantage',
                'description': 'アセトアミノフェン含有 - 胃に優しく、安全性が高い。頭痛・発熱の第一選択'
            })
    
    if 'イブプロフェン' in ingredients or 'ロキソプロフェン' in ingredients:
        if symptom in ['筋肉痛', '関節痛', '腰痛']:
            advantages.append({
                'type': 'ingredient_advantage',
                'description': 'NSAIDs含有 - 抗炎症作用が強く、炎症を伴う痛みに効果的'
            })
    
    # 分類による優位性
    if '指定第1類' in classification or '第1類' in classification:
        advantages.append({
            'type': 'classification',
            'description': '第1類医薬品 - 薬剤師による説明が義務付けられており、効果が強い'
        })
    
    return advantages

if __name__ == '__main__':
    log_file = '/Users/yuto/medicine-recommend-system/log/test.log'
    medicine_csv = '/Users/yuto/medicine-recommend-system/data/otc_medicine_data.csv'
    
    print("ログファイルを詳細分析中...")
    recommendations_by_input, symptom_medicine_map, medicine_details = analyze_test_log_detailed(log_file, medicine_csv)
    
    print(f"\n総推奨ケース数: {len(recommendations_by_input)}")
    print(f"ユニークな医薬品数: {len(medicine_details)}")
    
    # 症状別の推奨を集計
    print("\n=== 症状別推奨医薬品（上位10症状） ===")
    symptom_counts = {symptom: len(medicines) for symptom, medicines in symptom_medicine_map.items()}
    for symptom, count in sorted(symptom_counts.items(), key=lambda x: x[1], reverse=True)[:10]:
        medicine_counts = Counter(symptom_medicine_map[symptom])
        print(f"\n【{symptom}】 (総推奨回数: {count})")
        print("  上位5件の推奨医薬品:")
        for med, med_count in medicine_counts.most_common(5):
            info = medicine_details.get(med, {})
            efficacy = info.get('efficacy', 'N/A')[:80] if info else 'N/A'
            med_type = info.get('medicine_type', 'N/A') if info else 'N/A'
            print(f"    {med}: {med_count}回")
            print(f"      種類: {med_type}")
            print(f"      効能: {efficacy}")
    
    # 詳細データをJSONで保存
    output_data = {
        'total_cases': len(recommendations_by_input),
        'unique_medicines': len(medicine_details),
        'symptom_medicine_counts': {
            symptom: dict(Counter(medicines))
            for symptom, medicines in symptom_medicine_map.items()
        },
        'medicine_details': medicine_details,
        'recommendations_sample': recommendations_by_input[:100]  # 最初の100ケース
    }
    
    with open('/Users/yuto/medicine-recommend-system/detailed_log_analysis.json', 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    
    print("\n詳細分析結果を detailed_log_analysis.json に保存しました。")

