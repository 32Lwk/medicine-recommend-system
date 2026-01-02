"""
テストログから推奨医薬品を分析するスクリプト
"""
import re
import json
from collections import defaultdict, Counter
import pandas as pd

def analyze_test_log(log_file_path):
    """テストログを分析して推奨医薬品のパターンを抽出"""
    
    # 推奨医薬品と症状のマッピング
    recommendations_by_symptom = defaultdict(list)
    recommendations_count = Counter()
    symptom_patterns = defaultdict(list)
    
    with open(log_file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    current_symptom = None
    current_input = None
    
    for i, line in enumerate(lines):
        # 症状パターンの検出
        if 'テストケース' in line or '症状:' in line:
            # 症状を抽出
            symptom_match = re.search(r'症状[：:]\s*([^,\n]+)', line)
            if symptom_match:
                current_symptom = symptom_match.group(1).strip()
        
        # ユーザー入力の検出
        if '入力:' in line or 'user_input' in line.lower():
            input_match = re.search(r'入力[：:]\s*(.+?)(?:\n|$)', line)
            if input_match:
                current_input = input_match.group(1).strip()
        
        # 推奨医薬品の検出
        if '推奨医薬品:' in line:
            medicines_match = re.search(r'推奨医薬品:\s*(.+?)(?:\n|$)', line)
            if medicines_match:
                medicines_str = medicines_match.group(1).strip()
                if medicines_str != '該当なし':
                    medicines = [m.strip() for m in medicines_str.split(',')]
                    recommendations_count.update(medicines)
                    
                    if current_symptom:
                        recommendations_by_symptom[current_symptom].extend(medicines)
                        symptom_patterns[current_symptom].append({
                            'input': current_input,
                            'medicines': medicines
                        })
    
    return recommendations_by_symptom, recommendations_count, symptom_patterns

def get_medicine_info(medicine_name, medicine_df):
    """医薬品の詳細情報を取得"""
    matches = medicine_df[medicine_df['製品名'].str.contains(medicine_name, na=False, regex=False)]
    if len(matches) > 0:
        # 最も長い名前に一致するものを返す（より正確なマッチ）
        matches = matches.copy()
        matches['name_length'] = matches['製品名'].str.len()
        matches = matches.sort_values('name_length', ascending=False)
        return matches.iloc[0].to_dict()
    return None

if __name__ == '__main__':
    # ログファイルを読み込み
    log_file = '/Users/yuto/medicine-recommend-system/log/test.log'
    medicine_csv = '/Users/yuto/medicine-recommend-system/data/otc_medicine_data.csv'
    
    print("ログファイルを分析中...")
    recommendations_by_symptom, recommendations_count, symptom_patterns = analyze_test_log(log_file)
    
    # 医薬品データを読み込み
    print("医薬品データを読み込み中...")
    medicine_df = pd.read_csv(medicine_csv)
    
    print(f"\n総推奨回数: {sum(recommendations_count.values())}")
    print(f"ユニークな医薬品数: {len(recommendations_count)}")
    print(f"\n上位20件の推奨医薬品:")
    for medicine, count in recommendations_count.most_common(20):
        print(f"  {medicine}: {count}回 ({count/sum(recommendations_count.values())*100:.2f}%)")
    
    # 症状別の推奨パターンを分析
    print("\n\n=== 症状別推奨パターン ===")
    for symptom, medicines_list in sorted(recommendations_by_symptom.items(), key=lambda x: len(x[1]), reverse=True)[:20]:
        medicine_counts = Counter(medicines_list)
        print(f"\n【{symptom}】")
        print(f"  総推奨回数: {len(medicines_list)}")
        print(f"  上位5件:")
        for med, count in medicine_counts.most_common(5):
            info = get_medicine_info(med, medicine_df)
            efficacy = info.get('効能効果', 'N/A')[:100] if info else 'N/A'
            print(f"    {med}: {count}回 - 効能: {efficacy}")
    
    # JSON形式で出力（詳細分析用）
    output_data = {
        'total_recommendations': sum(recommendations_count.values()),
        'unique_medicines': len(recommendations_count),
        'top_20_medicines': dict(recommendations_count.most_common(20)),
        'recommendations_by_symptom': {
            symptom: dict(Counter(medicines_list)) 
            for symptom, medicines_list in recommendations_by_symptom.items()
        },
        'symptom_patterns': {
            symptom: patterns[:10]  # 各症状の最初の10パターン
            for symptom, patterns in symptom_patterns.items()
        }
    }
    
    with open('/Users/yuto/medicine-recommend-system/log_recommendation_analysis.json', 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    
    print("\n\n詳細分析結果を log_recommendation_analysis.json に保存しました。")

