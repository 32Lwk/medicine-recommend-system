"""
包括的な推奨結果分析スクリプト
薬剤師の視点から推奨医薬品の優位性を詳細に分析
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

class ComprehensiveRecommendationAnalyzer:
    """包括的な推奨結果分析クラス"""
    
    def __init__(self, log_path: Path, csv_path: Path):
        self.log_path = log_path
        self.csv_path = csv_path
        self.medicine_df = None
        self.bonus_scores = defaultdict(list)  # 医薬品名 -> ボーナススコアのリスト
        self.recommendation_contexts = []
        
    def load_medicine_data(self):
        """OTC医薬品データを読み込み"""
        logger.info("OTC医薬品データを読み込み中...")
        self.medicine_df = pd.read_csv(self.csv_path, encoding='utf-8')
        logger.info(f"医薬品データ読み込み完了: {len(self.medicine_df)}件")
        
    def extract_bonus_scores_from_log(self):
        """ログファイルからボーナススコア情報を抽出"""
        logger.info("ログファイルからボーナススコア情報を抽出中...")
        
        bonus_patterns = [
            (r'主要解熱鎮痛薬ボーナス.*?カロナール[ＡA]\s*[=＝]\s*([\+\-]?\d+\.?\d*)', 'カロナールＡ'),
            (r'主要解熱鎮痛薬ボーナス.*?タイレノール\s*[=＝]\s*([\+\-]?\d+\.?\d*)', 'タイレノール'),
            (r'主要解熱鎮痛薬ボーナス.*?ロキソニン[ＳS]\s*[=＝]\s*([\+\-]?\d+\.?\d*)', 'ロキソニンＳ'),
            (r'主要解熱鎮痛薬ボーナス.*?ロキソニン[ＳS]プレミアム\s*[=＝]\s*([\+\-]?\d+\.?\d*)', 'ロキソニンＳプレミアム'),
            (r'主要解熱鎮痛薬ボーナス.*?ロキソニン[ＳS]クイック\s*[=＝]\s*([\+\-]?\d+\.?\d*)', 'ロキソニンＳクイック'),
            (r'主要解熱鎮痛薬ボーナス.*?ロキソニン[ＳS]テープ\s*[=＝]\s*([\+\-]?\d+\.?\d*)', 'ロキソニンＳテープ'),
            (r'主要解熱鎮痛薬ボーナス.*?ロキソニン[ＳS]パップ\s*[=＝]\s*([\+\-]?\d+\.?\d*)', 'ロキソニンＳパップ'),
            (r'主要解熱鎮痛薬ボーナス.*?ロキソニン[ＳS]ゲル\s*[=＝]\s*([\+\-]?\d+\.?\d*)', 'ロキソニンＳゲル'),
        ]
        
        with open(self.log_path, 'r', encoding='utf-8') as f:
            for line in f:
                for pattern, medicine_name in bonus_patterns:
                    match = re.search(pattern, line)
                    if match:
                        score = float(match.group(1))
                        self.bonus_scores[medicine_name].append(score)
        
        logger.info(f"抽出されたボーナススコア: {len(self.bonus_scores)}種類の医薬品")
        for medicine, scores in self.bonus_scores.items():
            logger.info(f"  {medicine}: {len(scores)}回 (平均: {sum(scores)/len(scores):.2f})")
    
    def find_medicine_in_data(self, medicine_name: str) -> pd.DataFrame:
        """医薬品データから該当する医薬品を検索"""
        if self.medicine_df is None:
            return pd.DataFrame()
        
        # 部分一致で検索
        matches = self.medicine_df[
            self.medicine_df['製品名'].str.contains(medicine_name, na=False, regex=False)
        ]
        return matches
    
    def analyze_medicine_advantages(self, medicine_name: str, medicine_info: pd.Series) -> Dict:
        """医薬品の優位性を分析"""
        advantages = {
            'safety': [],
            'efficacy': [],
            'usability': [],
            'special_features': []
        }
        
        # 成分分析
        ingredients = str(medicine_info.get('成分', ''))
        
        # アセトアミノフェン含有（安全性が高い）
        if 'アセトアミノフェン' in ingredients:
            advantages['safety'].append('アセトアミノフェン含有により、胃への負担が少なく安全性が高い')
            advantages['special_features'].append('胃が弱い方にも適している')
        
        # イブプロフェン含有（抗炎症作用）
        if 'イブプロフェン' in ingredients or 'ロキソプロフェン' in ingredients:
            advantages['efficacy'].append('NSAIDs含有により、抗炎症作用があり痛みや熱に効果的')
            advantages['special_features'].append('炎症を伴う痛みに特に効果的')
        
        # 年齢制限の分析
        age_restriction = medicine_info.get('年齢制限', '')
        if age_restriction and str(age_restriction) != 'nan':
            try:
                age = float(age_restriction)
                if age <= 7:
                    advantages['usability'].append(f'7歳以上から使用可能で、小児にも適している')
                elif age <= 15:
                    advantages['usability'].append(f'15歳以上から使用可能')
            except:
                pass
        
        # ドーピング禁止物質の有無
        doping = medicine_info.get('禁止物質あり', '')
        if doping and str(doping) != 'nan' and str(doping).strip() == '禁止物質なし':
            advantages['special_features'].append('ドーピング禁止物質を含まないため、アスリートにも適している')
        
        # 効能効果の広さ
        efficacy = str(medicine_info.get('効能効果', ''))
        efficacy_keywords = ['頭痛', '発熱', '解熱', '鎮痛', '筋肉痛', '関節痛', '生理痛']
        matched_keywords = [kw for kw in efficacy_keywords if kw in efficacy]
        if len(matched_keywords) >= 3:
            advantages['efficacy'].append(f'複数の症状に対応可能（{", ".join(matched_keywords)}）')
        
        return advantages
    
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
        recommended_ingredients = str(recommended_info.get('成分', ''))
        
        # 同じ効能効果を持つ他の医薬品を検索
        keyword_pattern = '|'.join(symptom_keywords)
        other_medicines = self.medicine_df[
            self.medicine_df['効能効果'].str.contains(keyword_pattern, na=False, regex=True) &
            ~self.medicine_df['製品名'].str.contains(recommended_medicine_name, na=False, regex=False)
        ]
        
        # 成分の違いを分析
        ingredient_differences = []
        if 'アセトアミノフェン' in recommended_ingredients:
            # アセトアミノフェン含有の他の医薬品
            acetaminophen_alternatives = other_medicines[
                other_medicines['成分'].str.contains('アセトアミノフェン', na=False, regex=False)
            ]
            ingredient_differences.append({
                'feature': 'アセトアミノフェン含有',
                'advantage': '胃への負担が少なく、安全性が高い',
                'alternative_count': len(acetaminophen_alternatives)
            })
        
        if 'イブプロフェン' in recommended_ingredients or 'ロキソプロフェン' in recommended_ingredients:
            # NSAIDs含有の他の医薬品
            nsaid_alternatives = other_medicines[
                other_medicines['成分'].str.contains('イブプロフェン|ロキソプロフェン', na=False, regex=True)
            ]
            ingredient_differences.append({
                'feature': 'NSAIDs含有',
                'advantage': '抗炎症作用があり、炎症を伴う痛みに効果的',
                'alternative_count': len(nsaid_alternatives)
            })
        
        comparison = {
            'recommended_medicine': {
                'name': recommended_info['製品名'],
                'manufacturer': recommended_info.get('メーカー名', ''),
                'efficacy': recommended_efficacy,
                'ingredients': recommended_ingredients,
                'age_restriction': recommended_info.get('年齢制限', ''),
                'category': recommended_info.get('分類', ''),
                'bonus_score': self.bonus_scores.get(recommended_medicine_name, [0])[0] if self.bonus_scores.get(recommended_medicine_name) else 0
            },
            'alternative_count': len(other_medicines),
            'ingredient_differences': ingredient_differences,
            'top_alternatives': other_medicines.head(10)[['製品名', 'メーカー名', '効能効果', '成分']].to_dict('records')
        }
        
        return comparison
    
    def generate_comprehensive_report(self) -> str:
        """包括的な分析レポートを生成"""
        report = []
        
        report.append("=" * 100)
        report.append("薬剤師視点からの推奨医薬品包括的分析レポート")
        report.append("=" * 100)
        report.append("")
        report.append(f"分析日時: {pd.Timestamp.now().strftime('%Y年%m月%d日 %H:%M:%S')}")
        report.append(f"分析対象ログ: {self.log_path.name}")
        report.append(f"分析対象医薬品データ: {len(self.medicine_df)}件")
        report.append("")
        
        # 主要解熱鎮痛薬の分析
        report.append("## 1. 主要解熱鎮痛薬の推奨理由分析")
        report.append("")
        
        major_medicines = ['カロナールＡ', 'タイレノール', 'ロキソニンＳ', 'ロキソニンＳプレミアム', 'ロキソニンＳクイック']
        
        for medicine_name in major_medicines:
            if medicine_name not in self.bonus_scores:
                continue
            
            matches = self.find_medicine_in_data(medicine_name)
            if len(matches) == 0:
                continue
            
            med_info = matches.iloc[0]
            bonus_score = self.bonus_scores[medicine_name][0] if self.bonus_scores[medicine_name] else 0
            
            report.append(f"### {medicine_name} (ボーナススコア: +{bonus_score})")
            report.append("")
            
            report.append(f"**基本情報**")
            report.append(f"- メーカー: {med_info.get('メーカー名', '不明')}")
            report.append(f"- 分類: {med_info.get('分類', '不明')}")
            report.append(f"- 種類: {med_info.get('医薬品の種類', '不明')}")
            report.append("")
            
            # 優位性の分析
            advantages = self.analyze_medicine_advantages(medicine_name, med_info)
            
            report.append(f"**推奨される理由（薬剤師視点）**")
            report.append("")
            
            if advantages['safety']:
                report.append("**安全性の優位性:**")
                for adv in advantages['safety']:
                    report.append(f"- {adv}")
                report.append("")
            
            if advantages['efficacy']:
                report.append("**有効性の優位性:**")
                for adv in advantages['efficacy']:
                    report.append(f"- {adv}")
                report.append("")
            
            if advantages['usability']:
                report.append("**使用の容易さ:**")
                for adv in advantages['usability']:
                    report.append(f"- {adv}")
                report.append("")
            
            if advantages['special_features']:
                report.append("**特別な特徴:**")
                for adv in advantages['special_features']:
                    report.append(f"- {adv}")
                report.append("")
            
            # 成分情報
            ingredients = med_info.get('成分', '')
            if ingredients and str(ingredients) != 'nan':
                report.append(f"**主成分:**")
                ingredient_list = str(ingredients).split('\n') if '\n' in str(ingredients) else [str(ingredients)]
                for ing in ingredient_list[:5]:
                    if ing.strip():
                        report.append(f"- {ing.strip()}")
                report.append("")
            
            # 効能効果
            efficacy = med_info.get('効能効果', '')
            if efficacy and str(efficacy) != 'nan':
                report.append(f"**効能効果:**")
                report.append(f"{efficacy[:300]}{'...' if len(str(efficacy)) > 300 else ''}")
                report.append("")
            
            # 他の候補医薬品との比較
            efficacy_text = str(efficacy)
            symptom_keywords = self._extract_symptom_keywords(efficacy_text)
            if symptom_keywords:
                comparison = self.compare_with_alternatives(medicine_name, symptom_keywords)
                if comparison:
                    report.append(f"**他の候補医薬品との比較:**")
                    report.append(f"- 同じ効能効果を持つ他の医薬品: {comparison['alternative_count']}件")
                    
                    if comparison['ingredient_differences']:
                        report.append(f"- 成分による優位性:")
                        for diff in comparison['ingredient_differences']:
                            report.append(f"  - {diff['feature']}: {diff['advantage']} (同成分含有の他の医薬品: {diff['alternative_count']}件)")
                    
                    report.append("")
            
            report.append("---")
            report.append("")
        
        # 推奨理由の総括
        report.append("## 2. 推奨医薬品の優位性の総括")
        report.append("")
        report.append("### 2.1 安全性の観点")
        report.append("")
        report.append("推奨される医薬品は、以下の点で安全性が高いと評価されています:")
        report.append("")
        report.append("1. **アセトアミノフェン含有製剤**: 胃への負担が少なく、胃が弱い方や高齢者にも適している")
        report.append("2. **年齢制限の明確性**: 適切な年齢制限が設定されており、小児への使用可否が明確")
        report.append("3. **ドーピング禁止物質**: アスリートにも使用可能な製剤が推奨される場合がある")
        report.append("")
        
        report.append("### 2.2 有効性の観点")
        report.append("")
        report.append("推奨される医薬品は、以下の点で有効性が高いと評価されています:")
        report.append("")
        report.append("1. **主要ブランドの優先**: カロナール、ロキソニン、タイレノールなどの主要ブランドは、")
        report.append("   長年の使用実績と臨床データに基づき、高い有効性が確認されています")
        report.append("2. **症状特異性**: 症状に対して特異的な効能効果を持つ医薬品が優先的に推奨されます")
        report.append("3. **成分の適切性**: 症状に応じた適切な成分構成（アセトアミノフェン、NSAIDsなど）が選択されます")
        report.append("")
        
        report.append("### 2.3 使用の容易さの観点")
        report.append("")
        report.append("推奨される医薬品は、以下の点で使用しやすいと評価されています:")
        report.append("")
        report.append("1. **用法用量の明確性**: 添付文書に記載された用法用量が明確で、自己管理がしやすい")
        report.append("2. **剤形の多様性**: 錠剤、カプセル、坐薬、外用薬など、症状や年齢に応じた剤形が選択可能")
        report.append("3. **情報提供の充実**: 薬剤師が適切な情報提供を行いやすい製品が推奨されます")
        report.append("")
        
        report.append("### 2.4 ボーナススコアによる優先順位付け")
        report.append("")
        report.append("システムでは、主要解熱鎮痛薬に対して以下のボーナススコアが設定されています:")
        report.append("")
        for medicine_name, scores in sorted(self.bonus_scores.items(), key=lambda x: -x[1][0] if x[1] else 0):
            avg_score = sum(scores) / len(scores) if scores else 0
            report.append(f"- **{medicine_name}**: +{avg_score:.1f} (推奨回数: {len(scores)}回)")
        report.append("")
        report.append("このボーナススコアにより、主要ブランドが優先的に推奨される仕組みになっています。")
        report.append("")
        
        # より最適な医薬品の提案
        report.append("## 3. より最適な医薬品の検討")
        report.append("")
        report.append("### 3.1 症状別の最適な選択")
        report.append("")
        report.append("**頭痛・発熱の場合:**")
        report.append("- **カロナールA / タイレノール**: アセトアミノフェン含有により、胃への負担が少なく安全性が高い")
        report.append("- **ロキソニンS**: 抗炎症作用があり、炎症を伴う痛みに効果的")
        report.append("")
        report.append("**筋肉痛・関節痛の場合:**")
        report.append("- **ロキソニンSテープ / パップ / ゲル**: 外用薬により、局所的に作用し副作用リスクが低い")
        report.append("- **ロキソニンS**: 内服薬としても有効")
        report.append("")
        report.append("**生理痛の場合:**")
        report.append("- **ノーシンピュア**: アセトアミノフェン含有で安全性が高い")
        report.append("- **ロキソニンS**: 抗炎症作用により効果的")
        report.append("")
        
        report.append("### 3.2 年齢・体質による最適な選択")
        report.append("")
        report.append("**小児（7歳以上）:**")
        report.append("- アセトアミノフェン含有製剤が推奨（胃への負担が少ない）")
        report.append("- 年齢制限を必ず確認")
        report.append("")
        report.append("**高齢者・胃が弱い方:**")
        report.append("- アセトアミノフェン含有製剤が推奨（NSAIDsは胃への負担がある）")
        report.append("")
        report.append("**アスリート:**")
        report.append("- ドーピング禁止物質を含まない製剤を選択")
        report.append("")
        
        report.append("### 3.3 剤形による最適な選択")
        report.append("")
        report.append("**内服薬:**")
        report.append("- 全身的な効果が期待できる")
        report.append("- 複数の症状に対応可能")
        report.append("")
        report.append("**外用薬（テープ、パップ、ゲル）:**")
        report.append("- 局所的に作用し、副作用リスクが低い")
        report.append("- 筋肉痛、関節痛、腰痛などに適している")
        report.append("")
        report.append("**坐薬:**")
        report.append("- 小児の発熱時に有効")
        report.append("- 内服が困難な場合に適している")
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
        logger.info(f"包括的分析レポートを保存しました: {output_path}")

def main():
    """メイン処理"""
    # パスの設定
    project_root = Path(__file__).parent
    log_path = project_root / "log" / "test.log"
    csv_path = project_root / "data" / "otc_medicine_data.csv"
    output_path = project_root / "pharmacist_comprehensive_analysis_report.md"
    
    # 分析器の初期化
    analyzer = ComprehensiveRecommendationAnalyzer(log_path, csv_path)
    
    # 医薬品データの読み込み
    analyzer.load_medicine_data()
    
    # ログからボーナススコア情報を抽出
    analyzer.extract_bonus_scores_from_log()
    
    # 包括的な分析レポート生成
    report = analyzer.generate_comprehensive_report()
    
    # レポートを保存
    analyzer.save_report(report, output_path)
    
    # コンソールにも出力
    print("\n" + "=" * 100)
    print("包括的分析レポート（要約）")
    print("=" * 100)
    print(f"\nボーナススコアが設定された医薬品: {len(analyzer.bonus_scores)}種類")
    print(f"\n詳細なレポートは以下に保存されました:")
    print(f"{output_path}")
    print("\n" + "=" * 100)

if __name__ == '__main__':
    main()

