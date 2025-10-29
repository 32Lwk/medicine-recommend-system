"""
失敗パターン分析スクリプト
CSVレポートから失敗パターンを抽出し、詳細な分析レポートを生成する
"""

import csv
import os
import re
from collections import Counter, defaultdict

def analyze_failure_patterns():
    """失敗パターンを分析してレポートを生成"""
    
    csv_file = 'log/attribute_test_report.csv'
    if not os.path.exists(csv_file):
        print(f"エラー: {csv_file} が見つかりません")
        return
    
    # データを読み込み
    results = []
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            results.append(row)
    
    print(f"総テストケース数: {len(results)}")
    
    # 失敗パターンの分類
    failure_categories = {
        'age_only': [],      # 年齢のみ抽出
        'gender_only': [],   # 性別のみ抽出
        'both_missing': [],  # 両方欠損
        'partial_success': [], # 一部の属性のみ抽出
        'complete_failure': [] # 完全に失敗
    }
    
    # 各ケースを分類
    for result in results:
        age = result.get('age', '').strip()
        gender = result.get('gender', '').strip()
        pregnant = result.get('pregnant', '').strip()
        breastfeeding = result.get('breastfeeding', '').strip()
        constitution = result.get('constitution', '').strip()
        medical_history = result.get('medical_history', '').strip()
        
        # 年齢と性別の抽出状況
        has_age = age and age != '' and age != 'None'
        has_gender = gender and gender != '' and gender != 'None'
        
        # その他の属性の抽出状況
        has_other_attrs = any([
            pregnant and pregnant != '' and pregnant != 'None',
            breastfeeding and breastfeeding != '' and breastfeeding != 'None',
            constitution and constitution != '' and constitution != 'None',
            medical_history and medical_history != '' and medical_history != 'None'
        ])
        
        if has_age and has_gender:
            # 両方抽出成功
            continue
        elif has_age and not has_gender:
            failure_categories['age_only'].append(result)
        elif not has_age and has_gender:
            failure_categories['gender_only'].append(result)
        elif not has_age and not has_gender:
            if has_other_attrs:
                failure_categories['partial_success'].append(result)
            else:
                failure_categories['complete_failure'].append(result)
        else:
            failure_categories['both_missing'].append(result)
    
    # 分析結果をレポートに出力
    report_file = 'log/failure_analysis_report.txt'
    os.makedirs('log', exist_ok=True)
    
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write("属性抽出失敗パターン分析レポート\n")
        f.write("=" * 80 + "\n\n")
        
        # 全体統計
        total_failures = sum(len(cases) for cases in failure_categories.values())
        f.write(f"総テストケース数: {len(results)}\n")
        f.write(f"失敗ケース数: {total_failures}\n")
        f.write(f"成功率: {(len(results) - total_failures) / len(results) * 100:.1f}%\n\n")
        
        # 各カテゴリの詳細分析
        for category, cases in failure_categories.items():
            if not cases:
                continue
                
            f.write(f"\n【{category.upper()}】({len(cases)}件)\n")
            f.write("-" * 40 + "\n")
            
            # 入力テキストの特徴分析
            text_lengths = [len(case['input']) for case in cases]
            f.write(f"入力テキスト長: 平均 {sum(text_lengths)/len(text_lengths):.1f}文字\n")
            
            # よくある失敗パターン
            common_patterns = analyze_common_patterns(cases)
            f.write("よくある失敗パターン:\n")
            for pattern, count in common_patterns.most_common(5):
                f.write(f"  - {pattern}: {count}件\n")
            
            # 具体的な失敗例（最初の5件）
            f.write("\n失敗例:\n")
            for i, case in enumerate(cases[:5], 1):
                f.write(f"{i}. 入力: {case['input']}\n")
                f.write(f"   年齢: {case.get('age', 'N/A')}\n")
                f.write(f"   性別: {case.get('gender', 'N/A')}\n")
                f.write(f"   その他: 妊娠={case.get('pregnant', 'N/A')}, 体質={case.get('constitution', 'N/A')}\n\n")
    
    print(f"分析レポートを {report_file} に保存しました")
    
    # コンソールにもサマリーを表示
    print("\n失敗パターン分析結果:")
    print("-" * 40)
    for category, cases in failure_categories.items():
        if cases:
            print(f"{category}: {len(cases)}件")

def analyze_common_patterns(cases):
    """失敗ケースの共通パターンを分析"""
    patterns = []
    
    for case in cases:
        text = case['input']
        
        # 年齢表現のパターン
        if re.search(r'\d+代', text):
            patterns.append("X代表現")
        elif re.search(r'\d+歳', text):
            patterns.append("X歳表現")
        elif re.search(r'\d+才', text):
            patterns.append("X才表現")
        
        # 性別表現のパターン
        if re.search(r'女性|女の子|お母さん|おばあちゃん', text):
            patterns.append("女性表現")
        elif re.search(r'男性|男の子|お父さん|おじいちゃん', text):
            patterns.append("男性表現")
        
        # 複雑な文構造
        if len(text) > 50:
            patterns.append("長文")
        if text.count('。') > 1:
            patterns.append("複文")
        if re.search(r'[、，]', text):
            patterns.append("読点多数")
        
        # 曖昧な表現
        if re.search(r'くらい|ぐらい|ほど|程度', text):
            patterns.append("曖昧表現")
        if re.search(r'たぶん|おそらく|もしかして', text):
            patterns.append("推測表現")
    
    return Counter(patterns)

if __name__ == "__main__":
    analyze_failure_patterns()
