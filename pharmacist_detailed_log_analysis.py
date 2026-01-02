"""
ログファイルを分析して、薬剤師の視点から推奨医薬品の優位性を評価
"""
import re
from collections import Counter, defaultdict
import pandas as pd
import json

def analyze_log_recommendations():
    """ログファイルを分析して推奨医薬品の詳細を取得"""
    
    # CSVデータを読み込む
    df = pd.read_csv('data/otc_medicine_data.csv', encoding='utf-8')
    
    # ログファイルを読み込んで推奨医薬品を抽出
    recommendations_by_case = []
    current_test = None
    current_input = None
    
    with open('log/test.log', 'r', encoding='utf-8') as f:
        for line in f:
            # テストケース番号を取得
            if 'test_' in line and '|' in line:
                parts = line.split('|')
                if len(parts) >= 2:
                    current_test = parts[0].strip()
                    current_input = parts[1].strip() if len(parts) > 1 else ''
            
            # 推奨医薬品を取得
            if '推奨医薬品:' in line:
                medicines_str = line.split('推奨医薬品:')[1].strip()
                medicines = [m.strip() for m in medicines_str.split(',') if m.strip()]
                if current_test and current_input:
                    recommendations_by_case.append({
                        'test': current_test,
                        'input': current_input,
                        'medicines': medicines
                    })
    
    # 推奨医薬品の集計
    all_medicines = []
    for rec in recommendations_by_case:
        all_medicines.extend(rec['medicines'])
    
    counter = Counter(all_medicines)
    
    # 症状別の推奨医薬品を集計
    symptom_medicine_map = defaultdict(lambda: defaultdict(int))
    for rec in recommendations_by_case:
        input_text = rec['input'].lower()
        medicines = rec['medicines']
        
        # 症状を推定
        symptoms = []
        if '頭痛' in input_text or ('頭' in input_text and '痛' in input_text):
            symptoms.append('頭痛')
        if '発熱' in input_text or ('熱' in input_text and '発' in input_text):
            symptoms.append('発熱')
        if '咳' in input_text:
            symptoms.append('咳')
        if 'たん' in input_text or '痰' in input_text:
            symptoms.append('たん')
        if '鼻水' in input_text or '鼻づまり' in input_text:
            symptoms.append('鼻水')
        if 'のど' in input_text or '喉' in input_text:
            symptoms.append('のど')
        if '腹痛' in input_text or ('胃' in input_text and '痛' in input_text):
            symptoms.append('腹痛')
        if '下痢' in input_text:
            symptoms.append('下痢')
        if '便秘' in input_text:
            symptoms.append('便秘')
        if '生理痛' in input_text or '月経痛' in input_text:
            symptoms.append('生理痛')
        if '筋肉痛' in input_text or '関節痛' in input_text:
            symptoms.append('筋肉痛')
        
        for symptom in symptoms:
            for medicine in medicines:
                symptom_medicine_map[symptom][medicine] += 1
    
    # 上位推奨医薬品の詳細情報を取得
    top_medicines = [m for m, _ in counter.most_common(30)]
    
    analysis_results = {
        'total_cases': len(recommendations_by_case),
        'total_recommendations': len(all_medicines),
        'unique_medicines': len(counter),
        'top_medicines': [],
        'symptom_analysis': {}
    }
    
    # 上位推奨医薬品の詳細分析
    for medicine_name in top_medicines:
        matches = df[df['製品名'].str.contains(medicine_name, na=False)]
        if len(matches) > 0:
            row = matches.iloc[0]
            medicine_info = {
                'product_name': row.get('製品名', ''),
                'manufacturer': row.get('メーカー名', ''),
                'classification': row.get('分類', ''),
                'medicine_type': row.get('医薬品の種類', ''),
                'efficacy': str(row.get('効能効果', '')),
                'ingredients': str(row.get('成分', '')),
                'age_restriction': row.get('年齢制限', ''),
                'recommendation_count': counter[medicine_name],
                'recommendation_percentage': (counter[medicine_name] / len(all_medicines)) * 100 if all_medicines else 0,
                'symptoms_recommended_for': {}
            }
            
            # 症状別の推奨回数
            for symptom, medicine_counts in symptom_medicine_map.items():
                if medicine_name in medicine_counts:
                    medicine_info['symptoms_recommended_for'][symptom] = medicine_counts[medicine_name]
            
            analysis_results['top_medicines'].append(medicine_info)
    
    # 症状別分析
    for symptom, medicine_counts in symptom_medicine_map.items():
        top_medicines_for_symptom = sorted(medicine_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        analysis_results['symptom_analysis'][symptom] = {
            'total_cases': sum(medicine_counts.values()),
            'top_medicines': [{'name': m, 'count': c} for m, c in top_medicines_for_symptom]
        }
    
    return analysis_results

if __name__ == '__main__':
    results = analyze_log_recommendations()
    
    # JSON形式で保存
    with open('pharmacist_log_analysis.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print(f"分析完了: {results['total_cases']}件のテストケース、{results['total_recommendations']}件の推奨")
    print(f"ユニークな医薬品数: {results['unique_medicines']}")

