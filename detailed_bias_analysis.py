#!/usr/bin/env python3
"""
推奨の偏りと医薬品選択の妥当性を詳細に分析するスクリプト
"""
import pandas as pd
import re
from collections import Counter, defaultdict
from typing import Dict, List

def load_data():
    """データを読み込む"""
    log_path = "log/test.log"
    csv_path = "data/otc_medicine_data.csv"
    
    # ログを解析
    recommendations = []
    with open(log_path, 'r', encoding='utf-8') as f:
        current_test = None
        current_input = None
        current_symptoms = None
        current_medicines = None
        
        for line in f:
            test_match = re.search(r'test_(\d+)\|(.+?)\|', line)
            if test_match:
                current_test = test_match.group(1)
                current_input = test_match.group(2)
                current_symptoms = None
                current_medicines = None
                continue
            
            symptom_match = re.search(r'症状検出完了: (.+?)(?: \(処理時間|$)', line)
            if symptom_match:
                symptoms_str = symptom_match.group(1)
                if symptoms_str != "該当なし":
                    current_symptoms = [s.strip() for s in symptoms_str.split(',')]
                else:
                    current_symptoms = []
                continue
            
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
    
    # 医薬品データを読み込み
    medicine_df = pd.read_csv(csv_path, encoding='utf-8')
    
    return recommendations, medicine_df

def analyze_recommendation_bias(recommendations: List[Dict], medicine_df: pd.DataFrame):
    """推奨の偏りを分析"""
    total_cases = len(recommendations)
    cases_with_recommendations = sum(1 for r in recommendations if r['medicines'])
    
    # 医薬品の出現頻度
    medicine_frequency = Counter()
    symptom_medicine_map = defaultdict(lambda: defaultdict(int))
    input_medicine_map = defaultdict(list)
    
    # 医薬品タイプごとの分析用
    medicine_type_frequency = defaultdict(Counter)
    medicine_type_map = {}  # 製品名 -> 医薬品タイプのマッピング
    
    # 医薬品データからタイプ情報を取得
    for _, row in medicine_df.iterrows():
        product_name = str(row.get('製品名', ''))
        medicine_type = str(row.get('医薬品の種類', ''))
        if product_name and medicine_type:
            medicine_type_map[product_name] = medicine_type
    
    for rec in recommendations:
        if rec['medicines']:
            for rank, medicine in enumerate(rec['medicines'], 1):
                medicine_frequency[medicine] += 1
                for symptom in rec['symptoms']:
                    symptom_medicine_map[symptom][medicine] += 1
                input_medicine_map[rec['input']].append({
                    'medicine': medicine,
                    'rank': rank,
                    'symptoms': rec['symptoms']
                })
                
                # 医薬品タイプごとの頻度を記録
                med_type = medicine_type_map.get(medicine, '不明')
                medicine_type_frequency[med_type][medicine] += 1
    
    # トップ5の医薬品
    top5_medicines = medicine_frequency.most_common(5)
    top5_total = sum(count for _, count in top5_medicines)
    top5_percentage = (top5_total / cases_with_recommendations * 100) if cases_with_recommendations > 0 else 0
    
    # ノーシンピュアの推奨状況を詳細分析
    noshin_cases = []
    for rec in recommendations:
        if rec['medicines']:
            for medicine in rec['medicines']:
                if 'ノーシンピュア' in medicine or 'オトナノーシンピュア' in medicine:
                    noshin_cases.append({
                        'test_number': rec['test_number'],
                        'input': rec['input'],
                        'symptoms': rec['symptoms'],
                        'medicine': medicine
                    })
    
    # アセトアミノフェン含有医薬品を検索
    acetaminophen_medicines = []
    for _, row in medicine_df.iterrows():
        ingredients = str(row.get('成分', '')).lower()
        efficacy = str(row.get('効能効果', '')).lower()
        product_name = str(row.get('製品名', ''))
        
        # アセトアミノフェンのみ、またはアセトアミノフェンが主成分の医薬品を探す
        if 'アセトアミノフェン' in ingredients:
            # 他の鎮痛成分（イブプロフェン、エテンザミドなど）が含まれていないかチェック
            has_other_analgesic = any(x in ingredients for x in ['イブプロフェン', 'エテンザミド', 'ロキソプロフェン', 'アスピリン'])
            if not has_other_analgesic or 'カロナール' in product_name or 'タイレノール' in product_name:
                acetaminophen_medicines.append({
                    'product_name': product_name,
                    'manufacturer': row.get('メーカー名', ''),
                    'category': row.get('分類', ''),
                    'medicine_type': row.get('医薬品の種類', ''),
                    'efficacy': row.get('効能効果', ''),
                    'ingredients': row.get('成分', ''),
                    'age_limit': row.get('年齢制限', '')
                })
    
    # 医薬品タイプごとの偏り分析
    type_bias_analysis = {}
    for med_type, frequency_counter in medicine_type_frequency.items():
        if med_type != '不明' and len(frequency_counter) > 0:
            type_total = sum(frequency_counter.values())
            top5_type = frequency_counter.most_common(5)
            top5_type_total = sum(count for _, count in top5_type)
            top5_type_percentage = (top5_type_total / type_total * 100) if type_total > 0 else 0
            
            type_bias_analysis[med_type] = {
                'total_recommendations': type_total,
                'unique_medicines': len(frequency_counter),
                'top5_medicines': top5_type,
                'top5_total': top5_type_total,
                'top5_percentage': top5_type_percentage
            }
    
    return {
        'total_cases': total_cases,
        'cases_with_recommendations': cases_with_recommendations,
        'top5_medicines': top5_medicines,
        'top5_total': top5_total,
        'top5_percentage': top5_percentage,
        'noshin_cases': noshin_cases,
        'acetaminophen_medicines': acetaminophen_medicines,
        'symptom_medicine_map': dict(symptom_medicine_map),
        'type_bias_analysis': type_bias_analysis
    }

def generate_bias_report(analysis: Dict) -> str:
    """偏り分析レポートを生成"""
    report = []
    report.append("=" * 100)
    report.append("推奨の偏りと医薬品選択の妥当性分析レポート")
    report.append("=" * 100)
    report.append("\n")
    
    report.append("【1. 推奨の偏り分析】")
    report.append(f"総テストケース数: {analysis['total_cases']}")
    report.append(f"推奨医薬品が生成されたケース: {analysis['cases_with_recommendations']}")
    report.append(f"\n上位5つの医薬品の推奨回数: {analysis['top5_total']}回")
    report.append(f"上位5つの医薬品の推奨率: {analysis['top5_percentage']:.2f}%")
    report.append("\n上位5つの医薬品:")
    for i, (medicine, count) in enumerate(analysis['top5_medicines'], 1):
        percentage = (count / analysis['cases_with_recommendations'] * 100) if analysis['cases_with_recommendations'] > 0 else 0
        report.append(f"  {i}. {medicine}: {count}回 ({percentage:.2f}%)")
    
    report.append("\n" + "=" * 100)
    report.append("【2. ノーシンピュアの推奨状況詳細分析】")
    report.append("=" * 100)
    report.append(f"\nノーシンピュア系が推奨されたケース数: {len(analysis['noshin_cases'])}")
    
    # ノーシンピュアが推奨された症状を分析
    noshin_symptoms = Counter()
    noshin_inputs = []
    for case in analysis['noshin_cases']:
        for symptom in case['symptoms']:
            noshin_symptoms[symptom] += 1
        noshin_inputs.append(case['input'])
    
    report.append("\nノーシンピュアが推奨された主な症状:")
    for symptom, count in noshin_symptoms.most_common(10):
        report.append(f"  - {symptom}: {count}回")
    
    report.append("\nノーシンピュアが推奨された入力例（最初の20件）:")
    for i, input_text in enumerate(noshin_inputs[:20], 1):
        report.append(f"  {i}. {input_text}")
    
    report.append("\n" + "=" * 100)
    report.append("【3. アセトアミノフェン含有医薬品の検索結果】")
    report.append("=" * 100)
    report.append(f"\nアセトアミノフェン含有医薬品（カロナール等）の候補数: {len(analysis['acetaminophen_medicines'])}")
    
    if analysis['acetaminophen_medicines']:
        report.append("\nアセトアミノフェン含有医薬品のリスト:")
        for i, med in enumerate(analysis['acetaminophen_medicines'][:20], 1):
            report.append(f"\n{i}. {med['product_name']} ({med['manufacturer']})")
            report.append(f"   分類: {med['category']}")
            report.append(f"   種類: {med['medicine_type']}")
            report.append(f"   年齢制限: {med['age_limit'] if pd.notna(med['age_limit']) else 'なし'}")
            efficacy = str(med['efficacy'])
            if len(efficacy) > 150:
                report.append(f"   効能効果: {efficacy[:150]}...")
            else:
                report.append(f"   効能効果: {efficacy}")
    else:
        report.append("\n⚠️ アセトアミノフェン含有医薬品が見つかりませんでした。")
        report.append("   データベースに存在しないか、検索条件を調整する必要があります。")
    
    report.append("\n" + "=" * 100)
    report.append("【4. 問題点と改善提案】")
    report.append("=" * 100)
    report.append("\n【問題点1: 推奨の偏り】")
    report.append(f"- 上位5つの医薬品が{analysis['top5_percentage']:.2f}%の推奨率を示しており、")
    report.append("  推奨の多様性が不足している可能性があります。")
    report.append("- 同じ症状に対して、より適切な医薬品が存在する可能性があります。")
    
    report.append("\n【問題点2: ノーシンピュアの過剰推奨】")
    report.append("- ノーシンピュアは生理痛向けの医薬品であり、15歳以上が対象です。")
    report.append("- 頭痛などの一般的な痛みには、カロナール（アセトアミノフェン）の方が")
    report.append("  適切な場合が多いと考えられます。")
    report.append("- 特に以下の点で問題があります：")
    report.append("  * 胃腸への負担が少ない（NSAIDsではない）")
    report.append("  * 年齢制限が緩い（小児にも使用可能な製品がある）")
    report.append("  * 副作用リスクが低い")
    
    report.append("\n【改善提案】")
    report.append("1. スコアリングシステムの見直し：")
    report.append("   - 頭痛などの一般的な痛みには、アセトアミノフェン含有医薬品を優先")
    report.append("   - 生理痛が明示されている場合のみ、ノーシンピュアを推奨")
    report.append("   - 年齢制限を考慮した推奨ロジックの強化")
    
    report.append("\n2. 推奨の多様性向上：")
    report.append("   - 同じ症状に対して、複数の適切な医薬品を推奨")
    report.append("   - スコアが近い医薬品のランダム化またはローテーション")
    
    report.append("\n3. 症状特異性の強化：")
    report.append("   - 症状の種類に応じて、より特化した医薬品を推奨")
    report.append("   - 総合的な症状には総合薬、単一症状には特化薬を推奨")
    
    report.append("\n" + "=" * 100)
    report.append("【5. 医薬品タイプごとの偏り分析】")
    report.append("=" * 100)
    
    if analysis.get('type_bias_analysis'):
        for med_type, type_analysis in sorted(analysis['type_bias_analysis'].items(), 
                                               key=lambda x: x[1]['total_recommendations'], 
                                               reverse=True):
            report.append(f"\n【{med_type}】")
            report.append(f"  総推奨回数: {type_analysis['total_recommendations']}回")
            report.append(f"  ユニークな医薬品数: {type_analysis['unique_medicines']}種類")
            report.append(f"  上位5つの医薬品の推奨率: {type_analysis['top5_percentage']:.2f}%")
            report.append(f"  上位5つの医薬品:")
            for i, (medicine, count) in enumerate(type_analysis['top5_medicines'], 1):
                percentage = (count / type_analysis['total_recommendations'] * 100) if type_analysis['total_recommendations'] > 0 else 0
                report.append(f"    {i}. {medicine}: {count}回 ({percentage:.2f}%)")
    else:
        report.append("\n⚠️ 医薬品タイプごとの分析データがありません。")
    
    return "\n".join(report)

if __name__ == "__main__":
    print("データを読み込み中...")
    recommendations, medicine_df = load_data()
    print(f"読み込み完了: {len(recommendations)}件のテストケース, {len(medicine_df)}件の医薬品")
    
    print("偏り分析中...")
    analysis = analyze_recommendation_bias(recommendations, medicine_df)
    
    print("レポートを生成中...")
    report = generate_bias_report(analysis)
    
    # レポートをファイルに保存
    with open('bias_analysis_report.txt', 'w', encoding='utf-8') as f:
        f.write(report)
    
    print("\n" + report)
    print("\n\nレポートを 'bias_analysis_report.txt' に保存しました。")

