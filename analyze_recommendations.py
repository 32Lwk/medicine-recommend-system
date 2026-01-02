#!/usr/bin/env python3
"""
ログファイルから推奨医薬品を分析するスクリプト
"""
import re
import pandas as pd
from collections import defaultdict, Counter
from typing import Dict, List, Tuple

def parse_log_file(log_path: str) -> List[Dict]:
    """ログファイルを解析して推奨医薬品の情報を抽出"""
    recommendations = []
    
    with open(log_path, 'r', encoding='utf-8') as f:
        current_test = None
        current_input = None
        current_symptoms = None
        current_medicines = None
        
        for line in f:
            # テストケース番号を抽出
            test_match = re.search(r'test_(\d+)\|(.+?)\|', line)
            if test_match:
                current_test = test_match.group(1)
                current_input = test_match.group(2)
                current_symptoms = None
                current_medicines = None
                continue
            
            # 症状検出結果を抽出
            symptom_match = re.search(r'症状検出完了: (.+?)(?: \(処理時間|$)', line)
            if symptom_match:
                symptoms_str = symptom_match.group(1)
                if symptoms_str != "該当なし":
                    current_symptoms = [s.strip() for s in symptoms_str.split(',')]
                else:
                    current_symptoms = []
                continue
            
            # 推奨医薬品を抽出
            medicine_match = re.search(r'推奨医薬品: (.+?)(?:$|処理時間)', line)
            if medicine_match:
                medicines_str = medicine_match.group(1)
                if medicines_str != "該当なし":
                    current_medicines = [m.strip() for m in medicines_str.split(',')]
                else:
                    current_medicines = []
                
                if current_test and current_input:
                    recommendations.append({
                        'test_number': current_test,
                        'input': current_input,
                        'symptoms': current_symptoms or [],
                        'medicines': current_medicines or []
                    })
    
    return recommendations

def load_medicine_data(csv_path: str) -> pd.DataFrame:
    """医薬品データを読み込む"""
    return pd.read_csv(csv_path, encoding='utf-8')

def analyze_recommendations(recommendations: List[Dict], medicine_df: pd.DataFrame) -> Dict:
    """推奨医薬品を分析"""
    analysis = {
        'total_tests': len(recommendations),
        'tests_with_recommendations': sum(1 for r in recommendations if r['medicines']),
        'medicine_frequency': Counter(),
        'symptom_to_medicines': defaultdict(list),
        'medicine_details': {},
        'top_medicines': [],
        'symptom_patterns': defaultdict(list)
    }
    
    # 医薬品の出現頻度をカウント
    for rec in recommendations:
        if rec['medicines']:
            for medicine in rec['medicines']:
                analysis['medicine_frequency'][medicine] += 1
                
                # 症状と医薬品のマッピング
                for symptom in rec['symptoms']:
                    analysis['symptom_to_medicines'][symptom].append(medicine)
                    analysis['symptom_patterns'][symptom].append({
                        'medicine': medicine,
                        'input': rec['input'],
                        'test_number': rec['test_number']
                    })
    
    # 医薬品の詳細情報を取得
    for medicine_name, count in analysis['medicine_frequency'].most_common(50):
        # 医薬品データから情報を取得
        medicine_rows = medicine_df[medicine_df['製品名'] == medicine_name]
        if not medicine_rows.empty:
            row = medicine_rows.iloc[0]
            analysis['medicine_details'][medicine_name] = {
                'frequency': count,
                'manufacturer': row.get('メーカー名', ''),
                'category': row.get('分類', ''),
                'medicine_type': row.get('医薬品の種類', ''),
                'efficacy': row.get('効能効果', ''),
                'ingredients': row.get('成分', ''),
                'age_limit': row.get('年齢制限', ''),
                'doping_prohibited': row.get('禁止物質あり', '')
            }
    
    # トップ医薬品を取得
    analysis['top_medicines'] = analysis['medicine_frequency'].most_common(30)
    
    return analysis

def generate_report(analysis: Dict) -> str:
    """分析結果をレポート形式で生成"""
    report = []
    report.append("=" * 80)
    report.append("推奨医薬品分析レポート")
    report.append("=" * 80)
    report.append(f"\n総テストケース数: {analysis['total_tests']}")
    report.append(f"推奨医薬品が生成されたケース: {analysis['tests_with_recommendations']}")
    report.append(f"\n推奨医薬品が生成されなかったケース: {analysis['total_tests'] - analysis['tests_with_recommendations']}")
    
    report.append("\n" + "=" * 80)
    report.append("最も頻繁に推奨される医薬品 TOP 30")
    report.append("=" * 80)
    for i, (medicine, count) in enumerate(analysis['top_medicines'], 1):
        report.append(f"\n{i}. {medicine}: {count}回")
        if medicine in analysis['medicine_details']:
            details = analysis['medicine_details'][medicine]
            report.append(f"   メーカー: {details['manufacturer']}")
            report.append(f"   分類: {details['category']}")
            report.append(f"   種類: {details['medicine_type']}")
            report.append(f"   効能効果: {details['efficacy'][:100]}..." if len(details['efficacy']) > 100 else f"   効能効果: {details['efficacy']}")
    
    report.append("\n" + "=" * 80)
    report.append("症状別推奨医薬品パターン")
    report.append("=" * 80)
    for symptom, medicines in sorted(analysis['symptom_to_medicines'].items(), key=lambda x: len(x[1]), reverse=True)[:20]:
        medicine_counts = Counter(medicines)
        report.append(f"\n【{symptom}】")
        for medicine, count in medicine_counts.most_common(5):
            report.append(f"  - {medicine}: {count}回")
    
    return "\n".join(report)

if __name__ == "__main__":
    log_path = "log/test.log"
    csv_path = "data/otc_medicine_data.csv"
    
    print("ログファイルを解析中...")
    recommendations = parse_log_file(log_path)
    print(f"解析完了: {len(recommendations)}件のテストケース")
    
    print("医薬品データを読み込み中...")
    medicine_df = load_medicine_data(csv_path)
    print(f"読み込み完了: {len(medicine_df)}件の医薬品")
    
    print("分析中...")
    analysis = analyze_recommendations(recommendations, medicine_df)
    
    print("\n" + generate_report(analysis))
    
    # 詳細データをCSVに保存
    print("\n詳細データをCSVに保存中...")
    detailed_data = []
    for rec in recommendations:
        if rec['medicines']:
            for i, medicine in enumerate(rec['medicines'], 1):
                detailed_data.append({
                    'test_number': rec['test_number'],
                    'input': rec['input'],
                    'symptoms': ', '.join(rec['symptoms']),
                    'rank': i,
                    'medicine_name': medicine
                })
    
    df_detailed = pd.DataFrame(detailed_data)
    df_detailed.to_csv('recommendation_analysis.csv', index=False, encoding='utf-8-sig')
    print("recommendation_analysis.csv に保存しました。")

