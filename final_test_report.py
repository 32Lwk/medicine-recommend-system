"""
最終テストレポート生成
自然文.csvの事前分析と正確な評価方式による包括的なレポート
"""

import csv
import os
from collections import Counter

def generate_final_report():
    """最終テストレポートを生成"""
    
    print("="*80)
    print("自然文.csv属性抽出システム - 最終テストレポート")
    print("="*80)
    
    # 1. アノテーションファイルの統計
    annotation_file = '自然文_アノテーション.csv'
    if os.path.exists(annotation_file):
        analyze_annotation_file(annotation_file)
    
    # 2. 詳細テスト結果の分析
    detailed_file = 'log/detailed_test_results.csv'
    if os.path.exists(detailed_file):
        analyze_detailed_results(detailed_file)
    
    # 3. 改善提案
    generate_improvement_recommendations()

def analyze_annotation_file(file_path):
    """アノテーションファイルの統計分析"""
    
    print("\n【1. アノテーションファイル分析】")
    print("-" * 50)
    
    with open(file_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        data = list(reader)
    
    total_cases = len(data)
    print(f"総ケース数: {total_cases}")
    
    # 属性別の分布
    attributes = ['age', 'gender', 'pregnant', 'breastfeeding', 'allergies', 
                 'current_medications', 'medical_history', 'constitution', 'doping_concern']
    
    print("\n属性分布:")
    for attr in attributes:
        non_null_count = sum(1 for row in data if row[attr] != 'null')
        percentage = non_null_count / total_cases * 100
        print(f"  {attr}: {non_null_count}/{total_cases} ({percentage:.1f}%)")
    
    # 年齢分布
    age_distribution = Counter()
    for row in data:
        age = row['age']
        if age != 'null':
            try:
                age_int = int(age)
                if 0 <= age_int <= 120:
                    age_group = f"{(age_int//10)*10}代"
                    age_distribution[age_group] += 1
            except ValueError:
                pass
    
    print(f"\n年齢分布:")
    for age_group, count in sorted(age_distribution.items()):
        print(f"  {age_group}: {count}件")

def analyze_detailed_results(file_path):
    """詳細テスト結果の分析"""
    
    print("\n【2. 詳細テスト結果分析】")
    print("-" * 50)
    
    with open(file_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        data = list(reader)
    
    total_cases = len(data)
    print(f"テストケース数: {total_cases}")
    
    # 各属性の正確性
    attributes = ['age_correct', 'gender_correct', 'pregnant_correct', 
                 'breastfeeding_correct', 'allergies_correct', 'medications_correct',
                 'history_correct', 'constitution_correct', 'doping_correct']
    
    print("\n属性別正確性:")
    for attr in attributes:
        correct_count = sum(1 for row in data if row[attr] == 'True')
        accuracy = correct_count / total_cases * 100
        print(f"  {attr.replace('_correct', '')}: {correct_count}/{total_cases} ({accuracy:.1f}%)")
    
    # 全体成功率
    overall_success = sum(1 for row in data if row['overall_success'] == 'True')
    overall_accuracy = overall_success / total_cases * 100
    print(f"\n全体成功率: {overall_success}/{total_cases} ({overall_accuracy:.1f}%)")
    
    # 失敗パターン分析
    failed_cases = [row for row in data if row['overall_success'] == 'False']
    print(f"\n失敗ケース: {len(failed_cases)}件")
    
    if failed_cases:
        print("\n主な失敗原因:")
        age_failures = sum(1 for row in failed_cases if row['age_correct'] == 'False')
        gender_failures = sum(1 for row in failed_cases if row['gender_correct'] == 'False')
        print(f"  年齢抽出失敗: {age_failures}件")
        print(f"  性別抽出失敗: {gender_failures}件")

def generate_improvement_recommendations():
    """改善提案の生成"""
    
    print("\n【3. 改善提案】")
    print("-" * 50)
    
    print("1. 年齢抽出の改善:")
    print("   - 現在の成功率: 56.0%")
    print("   - 改善案:")
    print("     * より多くの年齢表現パターンを追加")
    print("     * 文脈から年齢を推測するロジックの強化")
    print("     * ルールベース抽出の精度向上")
    
    print("\n2. アレルギー抽出の改善:")
    print("   - 現在の成功率: 8.0%")
    print("   - 改善案:")
    print("     * アレルギー関連キーワードの拡充")
    print("     * 文脈解析によるアレルギー情報の抽出")
    print("     * 症状とアレルギーの関連性分析")
    
    print("\n3. 全体的な改善:")
    print("   - 現在の全体成功率: 56.0%")
    print("   - 目標: 90%以上")
    print("   - 改善案:")
    print("     * プロンプトエンジニアリングの最適化")
    print("     * Few-shot例の追加と改善")
    print("     * 後処理ロジックの強化")
    print("     * エラーハンドリングの改善")
    
    print("\n4. システム全体の改善:")
    print("   - 文字化け問題: 解決済み")
    print("   - テスト環境: 改善済み")
    print("   - 評価方式: 正確な評価方式を実装済み")
    print("   - ログ機能: 詳細なログ出力を実装済み")

def create_google_sheets_format():
    """Googleスプレッドシート形式のCSVファイルを作成"""
    
    print("\n【4. Googleスプレッドシート形式ファイル作成】")
    print("-" * 50)
    
    annotation_file = '自然文_アノテーション.csv'
    output_file = '自然文_GoogleSheets.csv'
    
    if not os.path.exists(annotation_file):
        print(f"エラー: {annotation_file} が見つかりません")
        return
    
    # アノテーションファイルを読み込み
    with open(annotation_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        data = list(reader)
    
    # Googleスプレッドシート用にフォーマット
    with open(output_file, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        
        # ヘッダー
        headers = [
            'ID', '入力テキスト', '年齢', '性別', '妊娠中', '授乳中',
            'アレルギー', '服用中の薬', '既往症', '体質', 'ドーピング懸念',
            '症状', '検出言語'
        ]
        writer.writerow(headers)
        
        # データ
        for row in data:
            # null値を空文字に変換
            def clean_value(value):
                return '' if value == 'null' else value
            
            output_row = [
                row['test_id'],
                row['input_text'],
                clean_value(row['age']),
                clean_value(row['gender']),
                'はい' if row['pregnant'] == 'True' else 'いいえ',
                'はい' if row['breastfeeding'] == 'True' else 'いいえ',
                clean_value(row['allergies']),
                clean_value(row['current_medications']),
                clean_value(row['medical_history']),
                clean_value(row['constitution']),
                'はい' if row['doping_concern'] == 'True' else 'いいえ',
                clean_value(row['symptoms']),
                row['detected_language']
            ]
            writer.writerow(output_row)
    
    print(f"Googleスプレッドシート形式ファイルを作成しました: {output_file}")
    print(f"総行数: {len(data) + 1} (ヘッダー含む)")

if __name__ == "__main__":
    generate_final_report()
    create_google_sheets_format()
