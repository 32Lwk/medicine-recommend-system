#!/usr/bin/env python3
"""
薬剤師の視点から推奨医薬品を分析するスクリプト
"""
import pandas as pd
import re
from collections import defaultdict, Counter
from typing import Dict, List, Tuple

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

def get_medicine_info(medicine_name: str, medicine_df: pd.DataFrame) -> Dict:
    """医薬品の詳細情報を取得"""
    rows = medicine_df[medicine_df['製品名'] == medicine_name]
    if rows.empty:
        return None
    
    row = rows.iloc[0]
    return {
        'product_name': row.get('製品名', ''),
        'manufacturer': row.get('メーカー名', ''),
        'category': row.get('分類', ''),
        'medicine_type': row.get('医薬品の種類', ''),
        'efficacy': row.get('効能効果', ''),
        'ingredients': row.get('成分', ''),
        'usage': row.get('用法用量', ''),
        'age_limit': row.get('年齢制限', ''),
        'doping_prohibited': row.get('禁止物質あり', ''),
        'competition_category': row.get('競技会区分', ''),
        'conditions': row.get('条件', '')
    }

def analyze_top_medicines(recommendations: List[Dict], medicine_df: pd.DataFrame) -> Dict:
    """トップ推奨医薬品を分析"""
    # 医薬品の出現頻度
    medicine_frequency = Counter()
    symptom_medicine_map = defaultdict(lambda: defaultdict(int))
    
    for rec in recommendations:
        if rec['medicines']:
            for rank, medicine in enumerate(rec['medicines'], 1):
                medicine_frequency[medicine] += 1
                for symptom in rec['symptoms']:
                    symptom_medicine_map[symptom][medicine] += 1
    
    # トップ10の医薬品を分析
    top_medicines = medicine_frequency.most_common(10)
    
    analysis = {}
    for medicine_name, count in top_medicines:
        info = get_medicine_info(medicine_name, medicine_df)
        if info:
            # この医薬品が推奨された症状を取得
            symptoms_for_this_medicine = []
            for symptom, medicines in symptom_medicine_map.items():
                if medicine_name in medicines:
                    symptoms_for_this_medicine.append({
                        'symptom': symptom,
                        'count': medicines[medicine_name]
                    })
            symptoms_for_this_medicine.sort(key=lambda x: x['count'], reverse=True)
            
            analysis[medicine_name] = {
                'info': info,
                'frequency': count,
                'top_symptoms': symptoms_for_this_medicine[:5]
            }
    
    return analysis

def find_alternative_medicines(medicine_name: str, symptom: str, medicine_df: pd.DataFrame) -> List[Dict]:
    """同じ症状に対して推奨された医薬品の代替候補を探す"""
    info = get_medicine_info(medicine_name, medicine_df)
    if not info:
        return []
    
    # 同じ効能効果を持つ医薬品を探す
    efficacy_keywords = []
    if info['efficacy']:
        # 効能効果から主要キーワードを抽出（簡易版）
        efficacy_text = str(info['efficacy']).lower()
        # 症状に関連するキーワードを抽出
        if symptom in ['頭痛', '痛']:
            efficacy_keywords = ['頭痛', '痛', '鎮痛']
        elif symptom in ['発熱', '熱']:
            efficacy_keywords = ['発熱', '熱', '解熱']
        elif symptom in ['咳']:
            efficacy_keywords = ['咳', 'せき']
        elif symptom in ['のど', 'のどの痛み']:
            efficacy_keywords = ['のど', '咽頭', '喉']
        elif symptom in ['腹痛', 'お腹']:
            efficacy_keywords = ['腹痛', '胃痛', '胃']
        elif symptom in ['鼻水', '鼻']:
            efficacy_keywords = ['鼻水', '鼻炎', '鼻']
        elif symptom in ['下痢']:
            efficacy_keywords = ['下痢', '止瀉']
        elif symptom in ['便秘']:
            efficacy_keywords = ['便秘']
    
    alternatives = []
    if efficacy_keywords:
        for _, row in medicine_df.iterrows():
            if row['製品名'] == medicine_name:
                continue
            
            efficacy = str(row.get('効能効果', '')).lower()
            if any(kw in efficacy for kw in efficacy_keywords):
                alternatives.append({
                    'product_name': row.get('製品名', ''),
                    'manufacturer': row.get('メーカー名', ''),
                    'category': row.get('分類', ''),
                    'medicine_type': row.get('医薬品の種類', ''),
                    'efficacy': row.get('効能効果', ''),
                    'ingredients': row.get('成分', '')
                })
    
    return alternatives[:10]  # 上位10件まで

def generate_pharmacist_report(analysis: Dict, recommendations: List[Dict], medicine_df: pd.DataFrame) -> str:
    """薬剤師の視点からの分析レポートを生成"""
    report = []
    report.append("=" * 100)
    report.append("薬剤師の視点から見た推奨医薬品の分析レポート")
    report.append("=" * 100)
    report.append("\n")
    report.append("【分析概要】")
    report.append(f"- 総テストケース数: {len(recommendations)}")
    report.append(f"- 推奨医薬品が生成されたケース: {sum(1 for r in recommendations if r['medicines'])}")
    report.append(f"- 分析対象医薬品数: {len(analysis)}")
    report.append("\n")
    
    for rank, (medicine_name, data) in enumerate(analysis.items(), 1):
        info = data['info']
        frequency = data['frequency']
        top_symptoms = data['top_symptoms']
        
        report.append("=" * 100)
        report.append(f"【{rank}位】 {medicine_name}")
        report.append("=" * 100)
        report.append(f"\n推奨頻度: {frequency}回")
        report.append(f"\n【基本情報】")
        report.append(f"- メーカー: {info['manufacturer']}")
        report.append(f"- 分類: {info['category']}")
        report.append(f"- 種類: {info['medicine_type']}")
        report.append(f"- 年齢制限: {info['age_limit'] if pd.notna(info['age_limit']) else 'なし'}")
        report.append(f"- ドーピング禁止物質: {info['doping_prohibited'] if pd.notna(info['doping_prohibited']) else 'なし'}")
        
        report.append(f"\n【効能効果】")
        efficacy = str(info['efficacy'])
        if len(efficacy) > 200:
            report.append(f"{efficacy[:200]}...")
        else:
            report.append(efficacy)
        
        report.append(f"\n【主要成分】")
        ingredients = str(info['ingredients'])
        if len(ingredients) > 300:
            report.append(f"{ingredients[:300]}...")
        else:
            report.append(ingredients)
        
        report.append(f"\n【主に推奨される症状】")
        for symptom_data in top_symptoms:
            report.append(f"- {symptom_data['symptom']}: {symptom_data['count']}回")
        
        # 薬剤師の視点からの評価
        report.append(f"\n【薬剤師の視点からの評価】")
        
        # 効能特異性の評価
        if top_symptoms:
            main_symptom = top_symptoms[0]['symptom']
            efficacy_lower = str(info['efficacy']).lower()
            symptom_lower = main_symptom.lower()
            
            # 効能効果に症状が明記されているか
            if symptom_lower in efficacy_lower or any(synonym in efficacy_lower for synonym in ['痛', '熱', '咳', 'のど', '鼻']):
                report.append("✓ 効能特異性: 症状に対して効能効果が明確に記載されており、適応性が高い")
            else:
                report.append("⚠ 効能特異性: 症状と効能効果の関連性がやや弱い可能性")
        
        # 成分の評価
        ingredients_str = str(info['ingredients']).lower()
        if 'アセトアミノフェン' in ingredients_str or 'イブプロフェン' in ingredients_str:
            report.append("✓ 成分: 一般的な解熱鎮痛成分を含んでおり、安全性が確立されている")
        elif 'カフェイン' in ingredients_str:
            report.append("⚠ 成分: カフェイン含有のため、就寝前の服用や過剰摂取に注意が必要")
        
        # 分類の評価
        if info['category'] == '指定第2類':
            report.append("✓ 安全性: 指定第2類医薬品で、比較的安全性が高い")
        elif info['category'] == '第2類':
            report.append("✓ 安全性: 第2類医薬品で、適切な情報提供により安全に使用可能")
        elif info['category'] == '第3類':
            report.append("✓ 安全性: 第3類医薬品で、リスクが低い")
        
        # 年齢制限の評価
        if pd.notna(info['age_limit']) and str(info['age_limit']).strip():
            age_limit = str(info['age_limit'])
            if '15' in age_limit or '15歳' in age_limit:
                report.append("⚠ 年齢制限: 15歳未満は服用不可のため、小児には推奨できない")
            elif '4' in age_limit or '4歳' in age_limit:
                report.append("⚠ 年齢制限: 4歳未満は服用不可のため、乳幼児には推奨できない")
        
        # 代替医薬品の検討
        if top_symptoms:
            main_symptom = top_symptoms[0]['symptom']
            alternatives = find_alternative_medicines(medicine_name, main_symptom, medicine_df)
            if alternatives:
                report.append(f"\n【同じ症状に対する代替候補医薬品（参考）】")
                for i, alt in enumerate(alternatives[:5], 1):
                    report.append(f"{i}. {alt['product_name']} ({alt['manufacturer']})")
                    report.append(f"   種類: {alt['medicine_type']}")
                    report.append(f"   効能: {str(alt['efficacy'])[:100]}...")
        
        report.append("\n")
    
    return "\n".join(report)

if __name__ == "__main__":
    print("データを読み込み中...")
    recommendations, medicine_df = load_data()
    print(f"読み込み完了: {len(recommendations)}件のテストケース, {len(medicine_df)}件の医薬品")
    
    print("分析中...")
    analysis = analyze_top_medicines(recommendations, medicine_df)
    
    print("レポートを生成中...")
    report = generate_pharmacist_report(analysis, recommendations, medicine_df)
    
    # レポートをファイルに保存
    with open('pharmacist_analysis_report.txt', 'w', encoding='utf-8') as f:
        f.write(report)
    
    print("\n" + report)
    print("\n\nレポートを 'pharmacist_analysis_report.txt' に保存しました。")

