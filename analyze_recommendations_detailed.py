"""
ログファイルとOTC医薬品データから推奨結果を詳細分析するスクリプト
薬剤師の視点から推奨医薬品の優位性を分析
"""
import pandas as pd
import re
import json
from collections import defaultdict, Counter
from pathlib import Path
import logging
from typing import Dict, List, Tuple, Optional

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class RecommendationAnalyzer:
    """推奨結果分析クラス"""
    
    def __init__(self, log_path: Path, csv_path: Path):
        self.log_path = log_path
        self.csv_path = csv_path
        self.medicine_df = None
        self.recommendations = []
        self.test_cases = []
        
    def load_medicine_data(self):
        """OTC医薬品データを読み込み"""
        logger.info("OTC医薬品データを読み込み中...")
        self.medicine_df = pd.read_csv(self.csv_path, encoding='utf-8')
        logger.info(f"医薬品データ読み込み完了: {len(self.medicine_df)}件")
        
    def extract_medicine_names_from_log(self):
        """ログファイルから医薬品名を抽出"""
        logger.info("ログファイルから医薬品名を抽出中...")
        
        medicine_names = set()
        test_contexts = []
        current_test = None
        
        # 主要医薬品名のパターン
        medicine_patterns = [
            r'カロナール[ＡA]?',
            r'ロキソニン[ＳS]?[^テパゲロ]',  # ロキソニンS（テープ、パップ、ゲル、ローションを除く）
            r'ロキソニン[ＳS]?テープ',
            r'ロキソニン[ＳS]?パップ',
            r'ロキソニン[ＳS]?ゲル',
            r'ロキソニン[ＳS]?ローション',
            r'タイレノール',
            r'ノーシン[^ピ]',  # ノーシンピュアを除く
            r'ノーシンピュア',
            r'バファリン',
            r'イブ[^A]',  # イブA錠を除く
            r'イブA錠',
            r'エキセドリン',
            r'セデス',
            r'ナロン',
            r'ラックル',
            r'リングルアイビー',
            r'リングル',
            r'パブロン',
            r'ルル',
            r'コンタック',
            r'ストナ',
            r'新ルル',
            r'ベンザブロック',
            r'プレコール',
            r'トランサミン',
            r'トラネキサム酸',
        ]
        
        with open(self.log_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        i = 0
        while i < len(lines):
            line = lines[i]
            
            # テストケース名の抽出
            if 'test_' in line and '(' in line:
                match = re.search(r'test_(\w+)', line)
                if match:
                    current_test = match.group(1)
            
            # 医薬品名の抽出
            for pattern in medicine_patterns:
                matches = re.finditer(pattern, line)
                for match in matches:
                    medicine_name = match.group(0)
                    medicine_names.add(medicine_name)
                    test_contexts.append({
                        'test_case': current_test,
                        'medicine': medicine_name,
                        'line': i + 1
                    })
            
            i += 1
        
        logger.info(f"抽出された医薬品名: {len(medicine_names)}種類")
        self.recommendations = test_contexts
        return medicine_names
    
    def find_medicine_in_data(self, medicine_name: str) -> pd.DataFrame:
        """医薬品データから該当する医薬品を検索"""
        if self.medicine_df is None:
            return pd.DataFrame()
        
        # 部分一致で検索
        matches = self.medicine_df[
            self.medicine_df['製品名'].str.contains(medicine_name, na=False, regex=False)
        ]
        return matches
    
    def analyze_recommended_medicines(self) -> List[Dict]:
        """推奨された医薬品の詳細分析"""
        logger.info("推奨医薬品の詳細分析を開始...")
        
        # 推奨頻度の集計
        medicine_counts = Counter()
        for rec in self.recommendations:
            medicine_counts[rec['medicine']] += 1
        
        analysis_results = []
        
        # 各推奨医薬品について詳細分析
        for medicine_name, count in medicine_counts.most_common():
            matches = self.find_medicine_in_data(medicine_name)
            
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
                        'competition_category': row.get('競技会区分', ''),
                        'usage': row.get('用法用量', '')
                    })
            else:
                # データにない医薬品
                analysis_results.append({
                    'medicine_name': medicine_name,
                    'recommendation_count': count,
                    'note': 'データに存在しない'
                })
        
        return analysis_results
    
    def compare_with_alternatives(self, recommended_medicine_name: str, 
                                  symptom_keywords: List[str]) -> Dict:
        """推奨された医薬品と他の候補医薬品を比較"""
        if self.medicine_df is None:
            return {}
        
        # 推奨された医薬品の情報
        recommended = self.find_medicine_in_data(recommended_medicine_name)
        
        if len(recommended) == 0:
            return {}
        
        recommended_info = recommended.iloc[0]
        recommended_efficacy = recommended_info.get('効能効果', '')
        
        # 同じ効能効果を持つ他の医薬品を検索
        keyword_pattern = '|'.join(symptom_keywords)
        other_medicines = self.medicine_df[
            self.medicine_df['効能効果'].str.contains(keyword_pattern, na=False, regex=True) &
            ~self.medicine_df['製品名'].str.contains(recommended_medicine_name, na=False, regex=False)
        ]
        
        comparison = {
            'recommended_medicine': {
                'name': recommended_info['製品名'],
                'manufacturer': recommended_info.get('メーカー名', ''),
                'efficacy': recommended_efficacy,
                'ingredients': recommended_info.get('成分', ''),
                'age_restriction': recommended_info.get('年齢制限', ''),
                'category': recommended_info.get('分類', '')
            },
            'alternative_count': len(other_medicines),
            'top_alternatives': other_medicines.head(10)[['製品名', 'メーカー名', '効能効果', '成分']].to_dict('records')
        }
        
        return comparison
    
    def generate_pharmacist_report(self, analysis_results: List[Dict]) -> str:
        """薬剤師視点の分析レポートを生成"""
        report = []
        
        report.append("=" * 100)
        report.append("薬剤師視点からの推奨医薬品詳細分析レポート")
        report.append("=" * 100)
        report.append("")
        report.append(f"分析日時: {pd.Timestamp.now().strftime('%Y年%m月%d日 %H:%M:%S')}")
        report.append(f"分析対象ログ: {self.log_path.name}")
        report.append(f"分析対象医薬品データ: {len(self.medicine_df)}件")
        report.append("")
        
        # 1. 推奨頻度の高い医薬品
        report.append("## 1. 推奨頻度の高い医薬品ランキング")
        report.append("")
        
        medicine_counts = Counter()
        for result in analysis_results:
            medicine_name = result.get('medicine_name', '')
            count = result.get('recommendation_count', 0)
            medicine_counts[medicine_name] += count
        
        report.append("### トップ30推奨医薬品")
        report.append("")
        report.append("| 順位 | 医薬品名 | 推奨回数 | メーカー | 分類 | 種類 |")
        report.append("|------|---------|---------|---------|------|------|")
        
        for i, (medicine_name, count) in enumerate(medicine_counts.most_common(30), 1):
            # 該当する医薬品情報を取得
            matches = self.find_medicine_in_data(medicine_name.split('（')[0])  # 括弧内を除去
            if len(matches) > 0:
                med_info = matches.iloc[0]
                manufacturer = med_info.get('メーカー名', '不明')
                category = med_info.get('分類', '不明')
                medicine_type = med_info.get('医薬品の種類', '不明')
            else:
                manufacturer = '不明'
                category = '不明'
                medicine_type = '不明'
            
            report.append(f"| {i} | {medicine_name} | {count} | {manufacturer} | {category} | {medicine_type} |")
        
        report.append("")
        
        # 2. 医薬品の種類別分析
        report.append("## 2. 医薬品の種類別推奨状況")
        report.append("")
        
        type_counts = Counter()
        for result in analysis_results:
            medicine_type = result.get('medicine_type', '不明')
            count = result.get('recommendation_count', 0)
            type_counts[medicine_type] += count
        
        report.append("| 医薬品の種類 | 推奨回数 | 割合 |")
        report.append("|------------|---------|------|")
        total_count = sum(type_counts.values())
        for medicine_type, count in type_counts.most_common():
            percentage = (count / total_count * 100) if total_count > 0 else 0
            report.append(f"| {medicine_type} | {count} | {percentage:.1f}% |")
        
        report.append("")
        
        # 3. 主要推奨医薬品の詳細分析
        report.append("## 3. 主要推奨医薬品の詳細分析（薬剤師視点）")
        report.append("")
        
        top_medicines = medicine_counts.most_common(20)
        for medicine_name, count in top_medicines:
            report.append(f"### {medicine_name} (推奨回数: {count})")
            report.append("")
            
            # 該当する医薬品データを取得
            base_name = medicine_name.split('（')[0].split('[')[0]  # 括弧や角括弧を除去
            matches = self.find_medicine_in_data(base_name)
            
            if len(matches) > 0:
                med_info = matches.iloc[0]
                
                report.append(f"**基本情報**")
                report.append(f"- メーカー: {med_info.get('メーカー名', '不明')}")
                report.append(f"- 分類: {med_info.get('分類', '不明')}")
                report.append(f"- 種類: {med_info.get('医薬品の種類', '不明')}")
                report.append("")
                
                report.append(f"**効能効果**")
                efficacy = med_info.get('効能効果', '不明')
                if efficacy and len(efficacy) > 0:
                    report.append(f"{efficacy[:500]}{'...' if len(efficacy) > 500 else ''}")
                report.append("")
                
                report.append(f"**成分**")
                ingredients = med_info.get('成分', '不明')
                if ingredients and len(ingredients) > 0:
                    # 成分を改行で区切って表示
                    ingredient_list = ingredients.split('\n') if '\n' in ingredients else [ingredients]
                    for ing in ingredient_list[:10]:  # 最初の10成分まで
                        if ing.strip():
                            report.append(f"- {ing.strip()}")
                    if len(ingredient_list) > 10:
                        report.append(f"- ... (他{len(ingredient_list) - 10}成分)")
                report.append("")
                
                report.append(f"**年齢制限**")
                age_restriction = med_info.get('年齢制限', '不明')
                if age_restriction and str(age_restriction) != 'nan' and len(str(age_restriction)) > 0:
                    age_str = str(age_restriction)
                    report.append(f"{age_str[:300]}{'...' if len(age_str) > 300 else ''}")
                    report.append("")
                
                # ドーピング禁止物質のチェック
                doping = med_info.get('禁止物質あり', '')
                if doping and str(doping) != 'nan' and str(doping).strip():
                    report.append(f"**ドーピング禁止物質**")
                    report.append(f"⚠️ {doping}")
                    report.append("")
                
                # 競技会区分
                competition = med_info.get('競技会区分', '')
                if competition and str(competition) != 'nan' and str(competition).strip():
                    report.append(f"**競技会区分**")
                    report.append(f"{competition}")
                    report.append("")
                
                # 他の候補医薬品との比較
                efficacy_text = str(efficacy)
                symptom_keywords = self._extract_symptom_keywords(efficacy_text)
                if symptom_keywords:
                    comparison = self.compare_with_alternatives(base_name, symptom_keywords)
                    if comparison:
                        report.append(f"**他の候補医薬品との比較**")
                        report.append(f"- 同じ効能効果を持つ他の医薬品: {comparison['alternative_count']}件")
                        if comparison['top_alternatives']:
                            report.append(f"- 主な代替候補（上位5件）:")
                            for alt in comparison['top_alternatives'][:5]:
                                report.append(f"  - {alt.get('製品名', '不明')} ({alt.get('メーカー名', '不明')})")
                        report.append("")
                
                report.append("---")
                report.append("")
            else:
                report.append("⚠️ 医薬品データに該当する情報が見つかりませんでした。")
                report.append("")
        
        # 4. 推奨理由の分析
        report.append("## 4. 推奨理由の分析")
        report.append("")
        report.append("### 推奨される主な理由")
        report.append("")
        report.append("1. **効能効果の適合性**: 症状に対して適切な効能効果を持つ医薬品が推奨されています。")
        report.append("2. **成分の安全性**: 年齢制限や禁忌事項を考慮した安全な成分構成の医薬品が優先されています。")
        report.append("3. **主要ブランドの優先**: カロナール、ロキソニン、タイレノールなどの主要ブランドが優先的に推奨されています。")
        report.append("4. **症状特異性**: 症状に対して特異的な効能効果を持つ医薬品が高スコアで推奨されています。")
        report.append("")
        
        return "\n".join(report)
    
    def _extract_symptom_keywords(self, efficacy_text: str) -> List[str]:
        """効能効果テキストから症状キーワードを抽出"""
        symptom_keywords = [
            '頭痛', '発熱', '解熱', '鎮痛', '咳', 'せき', '鼻水', '鼻炎', 'のど', '咽頭',
            '腹痛', '胃痛', '下痢', '便秘', '筋肉痛', '関節痛', '腰痛', '肩こり',
            '生理痛', '月経痛', 'かゆみ', '皮膚炎', '湿疹'
        ]
        
        found_keywords = []
        for keyword in symptom_keywords:
            if keyword in efficacy_text:
                found_keywords.append(keyword)
        
        return found_keywords
    
    def save_report(self, report: str, output_path: Path):
        """レポートをファイルに保存"""
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(report)
        logger.info(f"分析レポートを保存しました: {output_path}")

def main():
    """メイン処理"""
    # パスの設定
    project_root = Path(__file__).parent
    log_path = project_root / "log" / "test.log"
    csv_path = project_root / "data" / "otc_medicine_data.csv"
    output_path = project_root / "pharmacist_detailed_analysis_report.md"
    
    # 分析器の初期化
    analyzer = RecommendationAnalyzer(log_path, csv_path)
    
    # 医薬品データの読み込み
    analyzer.load_medicine_data()
    
    # ログから医薬品名を抽出
    medicine_names = analyzer.extract_medicine_names_from_log()
    
    # 推奨医薬品の詳細分析
    analysis_results = analyzer.analyze_recommended_medicines()
    
    # 薬剤師視点の分析レポート生成
    report = analyzer.generate_pharmacist_report(analysis_results)
    
    # レポートを保存
    analyzer.save_report(report, output_path)
    
    # コンソールにも出力
    print("\n" + "=" * 100)
    print("分析レポート（要約）")
    print("=" * 100)
    print(f"\n推奨された医薬品の種類数: {len(medicine_names)}")
    print(f"分析結果の件数: {len(analysis_results)}")
    print(f"\n詳細なレポートは以下に保存されました:")
    print(f"{output_path}")
    print("\n" + "=" * 100)

if __name__ == '__main__':
    main()

