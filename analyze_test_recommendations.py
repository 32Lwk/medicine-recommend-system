"""
ログファイルから推奨結果を抽出し、薬剤師の視点から分析するスクリプト
"""
import pandas as pd
import re
import json
from collections import defaultdict, Counter
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def parse_log_file(log_path):
    """ログファイルを解析して推奨結果を抽出"""
    recommendations = []
    current_test = None
    current_input = None
    current_symptoms = []
    
    with open(log_path, 'r', encoding='utf-8') as f:
        for line in f:
            # テストケース名の抽出
            if line.startswith('test_'):
                match = re.search(r'test_(\w+)', line)
                if match:
                    current_test = match.group(1)
            
            # 推奨医薬品の抽出（ログから）
            if '推奨医薬品:' in line or 'recommendations' in line.lower():
                # 医薬品名を抽出
                medicine_match = re.search(r'推奨医薬品:\s*(.+)', line)
                if medicine_match:
                    medicines_str = medicine_match.group(1).strip()
                    medicines = [m.strip() for m in medicines_str.split(',')]
                    recommendations.append({
                        'test_case': current_test,
                        'input': current_input,
                        'medicines': medicines,
                        'symptoms': current_symptoms.copy()
                    })
            
            # スコア情報の抽出
            if '最終スコア' in line or 'total_score' in line.lower():
                score_match = re.search(r'(\d+\.?\d*)', line)
                if score_match:
                    # スコア情報を保存
                    pass
            
            # 症状情報の抽出
            if '症状:' in line or 'symptom:' in line.lower():
                symptom_match = re.search(r'症状[：:]\s*(.+)', line)
                if symptom_match:
                    current_symptoms.append(symptom_match.group(1).strip())
    
    return recommendations

def extract_recommendations_from_test_log(log_path):
    """test.logから推奨結果を抽出（より詳細な解析）"""
    recommendations = []
    test_cases = []
    current_test = None
    
    with open(log_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    i = 0
    while i < len(lines):
        line = lines[i]
        
        # テストケース名の抽出
        if 'test_' in line and '(' in line:
            match = re.search(r'test_(\w+)', line)
            if match:
                current_test = match.group(1)
                # 次の行に説明がある場合
                if i + 1 < len(lines):
                    next_line = lines[i + 1]
                    if '...' in next_line:
                        description = next_line.strip()
                        test_cases.append({
                            'test_name': current_test,
                            'description': description
                        })
        
        # 推奨医薬品が生成されたケースの抽出
        if '推奨医薬品が生成されたケース' in line:
            match = re.search(r'(\d+)', line)
            if match:
                logger.info(f"推奨医薬品が生成されたケース数: {match.group(1)}")
        
        # 医薬品名の抽出（ログ内の医薬品名パターン）
        medicine_patterns = [
            r'カロナール[ＡA]?\s*[=＝]\s*([\+\-]?\d+\.?\d*)',
            r'ロキソニン[ＳS]?\s*[=＝]\s*([\+\-]?\d+\.?\d*)',
            r'タイレノール\s*[=＝]\s*([\+\-]?\d+\.?\d*)',
            r'ノーシン\s*[=＝]\s*([\+\-]?\d+\.?\d*)',
        ]
        
        for pattern in medicine_patterns:
            match = re.search(pattern, line)
            if match:
                medicine_name = pattern.split('[')[0]
                score = float(match.group(1))
                recommendations.append({
                    'test_case': current_test,
                    'medicine': medicine_name,
                    'score': score,
                    'line': i + 1
                })
        
        i += 1
    
    return recommendations, test_cases

def analyze_recommendations_with_medicine_data(recommendations, medicine_df):
    """OTC医薬品データと照合して分析"""
    analysis_results = []
    
    # 推奨された医薬品の集計
    recommended_medicines = Counter()
    for rec in recommendations:
        for medicine in rec.get('medicines', []):
            recommended_medicines[medicine] += 1
    
    # 各推奨医薬品の詳細情報を取得
    for medicine_name, count in recommended_medicines.most_common():
        # 医薬品データから該当する医薬品を検索
        matches = medicine_df[medicine_df['製品名'].str.contains(medicine_name, na=False, regex=False)]
        
        if len(matches) > 0:
            for idx, row in matches.iterrows():
                analysis_results.append({
                    'medicine_name': row['製品名'],
                    'manufacturer': row.get('メーカー名', ''),
                    'category': row.get('分類', ''),
                    'medicine_type': row.get('医薬品の種類', ''),
                    'efficacy': row.get('効能効果', ''),
                    'age_restriction': row.get('年齢制限', ''),
                    'ingredients': row.get('成分', ''),
                    'recommendation_count': count,
                    'doping_substance': row.get('禁止物質あり', ''),
                    'competition_category': row.get('競技会区分', '')
                })
        else:
            # データにない医薬品
            analysis_results.append({
                'medicine_name': medicine_name,
                'recommendation_count': count,
                'note': 'データに存在しない'
            })
    
    return analysis_results

def compare_medicines(medicine_df, recommended_medicine_name, symptom_category):
    """推奨された医薬品と他の候補医薬品を比較"""
    # 推奨された医薬品の情報
    recommended = medicine_df[medicine_df['製品名'].str.contains(recommended_medicine_name, na=False, regex=False)]
    
    if len(recommended) == 0:
        return None
    
    recommended_info = recommended.iloc[0]
    
    # 同じ症状カテゴリの他の医薬品を検索
    symptom_keywords = {
        '頭痛': ['頭痛', '鎮痛', '解熱'],
        '発熱': ['発熱', '解熱', '熱'],
        '咳': ['咳', 'せき', '鎮咳'],
        '鼻水': ['鼻水', '鼻炎', '鼻'],
        'のどの痛み': ['のど', '咽頭', '喉'],
        '腹痛': ['腹痛', '胃痛', '胃'],
        '下痢': ['下痢', '軟便'],
        '便秘': ['便秘', '便通'],
        '筋肉痛': ['筋肉痛', '肩こり', '腰痛']
    }
    
    keywords = symptom_keywords.get(symptom_category, [])
    
    # 同じ効能効果を持つ他の医薬品を検索
    other_medicines = medicine_df[
        medicine_df['効能効果'].str.contains('|'.join(keywords), na=False, regex=True) &
        ~medicine_df['製品名'].str.contains(recommended_medicine_name, na=False, regex=False)
    ]
    
    comparison = {
        'recommended_medicine': recommended_info.to_dict(),
        'alternative_medicines': other_medicines.head(10).to_dict('records'),
        'total_alternatives': len(other_medicines)
    }
    
    return comparison

def generate_pharmacist_analysis(analysis_results, medicine_df):
    """薬剤師の視点からの分析レポートを生成"""
    report = []
    
    report.append("=" * 80)
    report.append("薬剤師視点からの推奨医薬品分析レポート")
    report.append("=" * 80)
    report.append("")
    
    # 1. 推奨頻度の高い医薬品
    report.append("## 1. 推奨頻度の高い医薬品トップ20")
    report.append("")
    
    medicine_counts = Counter()
    for result in analysis_results:
        medicine_name = result.get('medicine_name', '')
        count = result.get('recommendation_count', 0)
        medicine_counts[medicine_name] += count
    
    for i, (medicine_name, count) in enumerate(medicine_counts.most_common(20), 1):
        report.append(f"{i}. {medicine_name}: {count}回推奨")
    
    report.append("")
    
    # 2. 医薬品の種類別分析
    report.append("## 2. 医薬品の種類別推奨状況")
    report.append("")
    
    type_counts = Counter()
    for result in analysis_results:
        medicine_type = result.get('medicine_type', '不明')
        count = result.get('recommendation_count', 0)
        type_counts[medicine_type] += count
    
    for medicine_type, count in type_counts.most_common():
        report.append(f"- {medicine_type}: {count}回")
    
    report.append("")
    
    # 3. 主要医薬品の詳細分析
    report.append("## 3. 主要推奨医薬品の詳細分析")
    report.append("")
    
    top_medicines = medicine_counts.most_common(10)
    for medicine_name, count in top_medicines:
        report.append(f"### {medicine_name} (推奨回数: {count})")
        
        # 該当する医薬品データを取得
        matches = medicine_df[medicine_df['製品名'].str.contains(medicine_name, na=False, regex=False)]
        if len(matches) > 0:
            med_info = matches.iloc[0]
            report.append(f"- メーカー: {med_info.get('メーカー名', '不明')}")
            report.append(f"- 分類: {med_info.get('分類', '不明')}")
            report.append(f"- 種類: {med_info.get('医薬品の種類', '不明')}")
            report.append(f"- 効能効果: {med_info.get('効能効果', '不明')[:100]}...")
            report.append(f"- 年齢制限: {med_info.get('年齢制限', '不明')}")
            
            # 成分情報
            ingredients = med_info.get('成分', '')
            if ingredients:
                report.append(f"- 主成分: {ingredients[:200]}...")
            
            report.append("")
    
    return "\n".join(report)

def main():
    """メイン処理"""
    # パスの設定
    project_root = Path(__file__).parent
    log_path = project_root / "log" / "test.log"
    csv_path = project_root / "data" / "otc_medicine_data.csv"
    output_path = project_root / "pharmacist_analysis_report.md"
    
    logger.info("ログファイルの解析を開始...")
    
    # OTC医薬品データの読み込み
    logger.info("OTC医薬品データを読み込み中...")
    medicine_df = pd.read_csv(csv_path, encoding='utf-8')
    logger.info(f"医薬品データ読み込み完了: {len(medicine_df)}件")
    
    # ログファイルから推奨結果を抽出
    logger.info("ログファイルから推奨結果を抽出中...")
    recommendations, test_cases = extract_recommendations_from_test_log(log_path)
    logger.info(f"抽出された推奨結果: {len(recommendations)}件")
    logger.info(f"抽出されたテストケース: {len(test_cases)}件")
    
    # より詳細な解析のため、テストファイルから直接推奨結果を抽出
    # 実際の推奨結果はテスト実行時に生成されるため、
    # テストファイルを実行して推奨結果を取得する必要がある
    
    # 分析結果の生成
    logger.info("分析結果を生成中...")
    analysis_results = analyze_recommendations_with_medicine_data(recommendations, medicine_df)
    
    # 薬剤師視点の分析レポート生成
    report = generate_pharmacist_analysis(analysis_results, medicine_df)
    
    # レポートをファイルに保存
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(report)
    
    logger.info(f"分析レポートを保存しました: {output_path}")
    print(report)

if __name__ == '__main__':
    main()

