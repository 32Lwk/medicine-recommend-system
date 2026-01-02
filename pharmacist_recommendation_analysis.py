#!/usr/bin/env python3
"""
薬剤師の視点から推奨医薬品を詳細に分析するスクリプト
ログファイルと医薬品データを照合し、推奨理由とより最適な医薬品を分析
"""
import pandas as pd
import re
from collections import Counter, defaultdict
from typing import Dict, List, Tuple
import json

def load_medicine_data(csv_path: str = "data/otc_medicine_data.csv") -> pd.DataFrame:
    """医薬品データを読み込む"""
    df = pd.read_csv(csv_path, encoding='utf-8')
    return df

def parse_test_log(log_path: str = "log/test.log") -> List[Dict]:
    """ログファイルを解析して推奨医薬品を抽出"""
    recommendations = []
    
    with open(log_path, 'r', encoding='utf-8') as f:
        current_test = None
        current_input = None
        current_symptoms = None
        current_medicines = None
        
        for line in f:
            # テストケース番号と入力内容を抽出
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
            medicine_match = re.search(r'出力: 推奨医薬品: (.+?)(?:$|処理時間)', line)
            if medicine_match:
                medicines_str = medicine_match.group(1)
                if medicines_str != "該当なし":
                    current_medicines = [m.strip() for m in medicines_str.split(',')]
                else:
                    current_medicines = []
                
                if current_test and current_input and current_medicines:
                    recommendations.append({
                        'test_number': current_test,
                        'input': current_input,
                        'symptoms': current_symptoms or [],
                        'medicines': current_medicines
                    })
    
    return recommendations

def get_medicine_info(medicine_name: str, medicine_df: pd.DataFrame) -> Dict:
    """医薬品名から詳細情報を取得"""
    # 製品名で完全一致を試す
    exact_match = medicine_df[medicine_df['製品名'] == medicine_name]
    if len(exact_match) > 0:
        row = exact_match.iloc[0]
        return {
            'product_name': row.get('製品名', ''),
            'manufacturer': row.get('メーカー名', ''),
            'classification': row.get('分類', ''),
            'medicine_type': row.get('医薬品の種類', ''),
            'efficacy': row.get('効能効果', ''),
            'ingredients': row.get('成分', ''),
            'age_limit': row.get('年齢制限', ''),
            'usage': row.get('用法用量', '')
        }
    
    # 部分一致を試す（製品名に含まれる）
    partial_match = medicine_df[medicine_df['製品名'].str.contains(medicine_name, na=False)]
    if len(partial_match) > 0:
        row = partial_match.iloc[0]
        return {
            'product_name': row.get('製品名', ''),
            'manufacturer': row.get('メーカー名', ''),
            'classification': row.get('分類', ''),
            'medicine_type': row.get('医薬品の種類', ''),
            'efficacy': row.get('効能効果', ''),
            'ingredients': row.get('成分', ''),
            'age_limit': row.get('年齢制限', ''),
            'usage': row.get('用法用量', '')
        }
    
    return None

def analyze_ingredients(ingredients_str: str) -> Dict:
    """成分を分析"""
    if pd.isna(ingredients_str) or not ingredients_str:
        return {'ingredient_list': [], 'has_acetaminophen': False, 'has_nsaids': False, 'has_ibuprofen': False, 'has_loxoprofen': False, 'ingredient_count': 0}
    
    ingredients_lower = str(ingredients_str).lower()
    ingredient_list = [ing.strip() for ing in re.split(r'[,，\s\n]+', ingredients_lower) if ing.strip()]
    
    return {
        'ingredient_list': ingredient_list,
        'ingredient_count': len(ingredient_list),
        'has_acetaminophen': 'アセトアミノフェン' in ingredients_lower,
        'has_ibuprofen': 'イブプロフェン' in ingredients_lower,
        'has_loxoprofen': 'ロキソプロフェン' in ingredients_lower,
        'has_aspirin': 'アスピリン' in ingredients_lower or 'アセチルサリチル酸' in ingredients_lower,
        'has_nsaids': any(nsaid in ingredients_lower for nsaid in ['イブプロフェン', 'ロキソプロフェン', 'アスピリン', 'アセチルサリチル酸', 'インドメタシン', 'ジクロフェナク']),
        'is_herbal': any(herb in ingredients_lower for herb in ['エキス', '散', '湯', '丸', '漢方'])
    }

def analyze_recommendations(recommendations: List[Dict], medicine_df: pd.DataFrame) -> Dict:
    """推奨医薬品を詳細に分析"""
    # 医薬品の出現頻度
    medicine_frequency = Counter()
    medicine_details = {}  # 医薬品名 -> 詳細情報
    symptom_medicine_map = defaultdict(lambda: defaultdict(int))
    medicine_type_distribution = Counter()
    
    # 各推奨を分析
    for rec in recommendations:
        if rec['medicines']:
            for rank, medicine in enumerate(rec['medicines'], 1):
                medicine_frequency[medicine] += 1
                
                # 医薬品の詳細情報を取得
                if medicine not in medicine_details:
                    info = get_medicine_info(medicine, medicine_df)
                    if info:
                        medicine_details[medicine] = info
                        # 成分分析を追加
                        ingredients_analysis = analyze_ingredients(info.get('ingredients', ''))
                        medicine_details[medicine].update(ingredients_analysis)
                        medicine_details[medicine]['ingredient_analysis'] = ingredients_analysis
                
                # 症状ごとのマッピング
                for symptom in rec['symptoms']:
                    symptom_medicine_map[symptom][medicine] += 1
                
                # 医薬品タイプの分布
                if medicine in medicine_details:
                    med_type = medicine_details[medicine].get('medicine_type', '不明')
                    medicine_type_distribution[med_type] += 1
    
    # トップ10の医薬品
    top10_medicines = medicine_frequency.most_common(10)
    
    return {
        'total_recommendations': len(recommendations),
        'total_unique_medicines': len(medicine_frequency),
        'top10_medicines': top10_medicines,
        'medicine_details': medicine_details,
        'symptom_medicine_map': dict(symptom_medicine_map),
        'medicine_type_distribution': dict(medicine_type_distribution)
    }

def find_better_alternatives(medicine_name: str, symptom: str, medicine_df: pd.DataFrame, 
                             current_medicine_info: Dict) -> List[Dict]:
    """より最適な医薬品を検索"""
    alternatives = []
    
    # 現在の医薬品の成分分析
    current_ingredients = current_medicine_info.get('ingredient_analysis', {})
    current_has_ibuprofen = current_ingredients.get('has_ibuprofen', False)
    current_has_acetaminophen = current_ingredients.get('has_acetaminophen', False)
    current_ingredient_count = current_ingredients.get('ingredient_count', 0)
    
    # 症状に基づいて適切な医薬品を検索
    symptom_keywords = {
        '頭痛': ['頭痛', '鎮痛', '解熱'],
        '発熱': ['発熱', '解熱', '熱'],
        '生理痛': ['生理痛', '月経痛', '鎮痛'],
        '筋肉痛': ['筋肉痛', '鎮痛', '抗炎症'],
        '関節痛': ['関節痛', '鎮痛', '抗炎症'],
        '腰痛': ['腰痛', '鎮痛', '抗炎症'],
        'のど': ['のど', '咽頭', '喉'],
        '咳': ['咳', 'せき', '鎮咳'],
        '鼻水': ['鼻水', '鼻炎', '鼻'],
        '胃痛': ['胃痛', '胃', '制酸'],
        '便秘': ['便秘', '便通'],
        '下痢': ['下痢', '止瀉']
    }
    
    search_keywords = []
    for key, keywords in symptom_keywords.items():
        if key in symptom or any(kw in symptom for kw in keywords):
            search_keywords.extend(keywords)
    
    if not search_keywords:
        return alternatives
    
    # 症状の正規化（「痛」だけの場合は「頭痛」として扱う）
    normalized_symptom = symptom
    if symptom == '痛' and '頭痛' in str(current_medicine_info.get('efficacy', '')):
        normalized_symptom = '頭痛'
    
    # 頭痛・発熱の場合、アセトアミノフェン単独製剤を優先的に検索
    if '頭痛' in normalized_symptom or '発熱' in normalized_symptom or '頭痛' in symptom or '発熱' in symptom:
        # まず、カロナールやタイレノールなどの有名な製品を直接検索
        famous_products = medicine_df[
            (medicine_df['製品名'].str.contains('カロナール', na=False, case=False) |
             medicine_df['製品名'].str.contains('タイレノール', na=False, case=False)) &
            (medicine_df['成分'].str.contains('アセトアミノフェン', na=False, case=False) &
             ~medicine_df['成分'].str.contains('イブプロフェン', na=False, case=False))
        ]
        
        for _, row in famous_products.iterrows():
            product_name = row.get('製品名', '')
            if product_name == medicine_name:
                continue
            
            info = {
                'product_name': product_name,
                'manufacturer': row.get('メーカー名', ''),
                'classification': row.get('分類', ''),
                'medicine_type': row.get('医薬品の種類', ''),
                'efficacy': row.get('効能効果', ''),
                'ingredients': row.get('成分', ''),
                'age_limit': row.get('年齢制限', ''),
                'usage': row.get('用法用量', ''),
                'priority': 'high'
            }
            
            ingredients_analysis = analyze_ingredients(info.get('ingredients', ''))
            info.update(ingredients_analysis)
            info['ingredient_analysis'] = ingredients_analysis
            
            alternatives.append(info)
        
        # 次に、アセトアミノフェン単独（イブプロフェンを含まない）を検索
        acetaminophen_only = medicine_df[
            medicine_df['成分'].str.contains('アセトアミノフェン', na=False, case=False) &
            ~medicine_df['成分'].str.contains('イブプロフェン', na=False, case=False)
        ]
        
        for _, row in acetaminophen_only.iterrows():
            product_name = row.get('製品名', '')
            if product_name == medicine_name:
                continue
            
            # 既に追加済みかチェック
            if any(alt['product_name'] == product_name for alt in alternatives):
                continue
            
            # 効能効果に頭痛または発熱が含まれているか確認
            efficacy = str(row.get('効能効果', '')).lower()
            has_relevant_efficacy = '頭痛' in efficacy or '発熱' in efficacy or '解熱' in efficacy or '鎮痛' in efficacy
            
            if has_relevant_efficacy:
                info = {
                    'product_name': product_name,
                    'manufacturer': row.get('メーカー名', ''),
                    'classification': row.get('分類', ''),
                    'medicine_type': row.get('医薬品の種類', ''),
                    'efficacy': row.get('効能効果', ''),
                    'ingredients': row.get('成分', ''),
                    'age_limit': row.get('年齢制限', ''),
                    'usage': row.get('用法用量', ''),
                    'priority': 'normal'
                }
                
                ingredients_analysis = analyze_ingredients(info.get('ingredients', ''))
                info.update(ingredients_analysis)
                info['ingredient_analysis'] = ingredients_analysis
                
                alternatives.append(info)
                
                if len(alternatives) >= 10:  # 最大10件まで
                    break
    
    # 効能効果で検索
    for keyword in search_keywords[:3]:  # 最初の3つのキーワードで検索
        matches = medicine_df[
            medicine_df['効能効果'].str.contains(keyword, na=False, case=False)
        ]
        
        for _, row in matches.iterrows():
            product_name = row.get('製品名', '')
            if product_name == medicine_name:
                continue
            
            # 既に追加済みかチェック
            if any(alt['product_name'] == product_name for alt in alternatives):
                continue
            
            info = {
                'product_name': product_name,
                'manufacturer': row.get('メーカー名', ''),
                'classification': row.get('分類', ''),
                'medicine_type': row.get('医薬品の種類', ''),
                'efficacy': row.get('効能効果', ''),
                'ingredients': row.get('成分', ''),
                'age_limit': row.get('年齢制限', ''),
                'usage': row.get('用法用量', ''),
                'priority': 'normal'
            }
            
            # 成分分析を追加
            ingredients_analysis = analyze_ingredients(info.get('ingredients', ''))
            info.update(ingredients_analysis)
            info['ingredient_analysis'] = ingredients_analysis
            
            alternatives.append(info)
            
            if len(alternatives) >= 15:  # 最大15件まで
                break
        
        if len(alternatives) >= 15:
            break
    
    # 優先度順にソート（高優先度を先に）
    alternatives.sort(key=lambda x: (x.get('priority', 'normal') == 'high', 
                                     -x.get('ingredient_analysis', {}).get('ingredient_count', 999)))
    
    return alternatives[:10]  # 上位10件を返す

def generate_pharmacist_analysis_report(analysis: Dict, medicine_df: pd.DataFrame) -> str:
    """薬剤師の視点からの詳細分析レポートを生成"""
    report = []
    report.append("=" * 120)
    report.append("薬剤師の視点からの推奨医薬品詳細分析レポート")
    report.append("=" * 120)
    report.append("\n")
    
    report.append(f"【分析対象】")
    report.append(f"  総推奨ケース数: {analysis['total_recommendations']}件")
    report.append(f"  ユニークな医薬品数: {analysis['total_unique_medicines']}種類")
    report.append(f"\n")
    
    # 医薬品タイプの分布
    report.append("【医薬品タイプの分布】")
    for med_type, count in sorted(analysis['medicine_type_distribution'].items(), 
                                   key=lambda x: x[1], reverse=True):
        percentage = (count / analysis['total_recommendations'] * 100) if analysis['total_recommendations'] > 0 else 0
        report.append(f"  {med_type}: {count}回 ({percentage:.2f}%)")
    report.append("\n")
    
    # トップ10の医薬品の詳細分析
    report.append("=" * 120)
    report.append("【トップ10推奨医薬品の詳細分析】")
    report.append("=" * 120)
    report.append("\n")
    
    for rank, (medicine_name, count) in enumerate(analysis['top10_medicines'], 1):
        percentage = (count / analysis['total_recommendations'] * 100) if analysis['total_recommendations'] > 0 else 0
        report.append(f"【{rank}位】 {medicine_name}")
        report.append(f"  推奨回数: {count}回 ({percentage:.2f}%)")
        report.append("\n")
        
        if medicine_name in analysis['medicine_details']:
            info = analysis['medicine_details'][medicine_name]
            
            report.append(f"  【基本情報】")
            report.append(f"    メーカー: {info.get('manufacturer', '不明')}")
            report.append(f"    分類: {info.get('classification', '不明')}")
            report.append(f"    医薬品タイプ: {info.get('medicine_type', '不明')}")
            report.append(f"    年齢制限: {info.get('age_limit', 'なし') if pd.notna(info.get('age_limit')) else 'なし'}")
            report.append("\n")
            
            # 成分分析
            ingredients = info.get('ingredients', '')
            if ingredients and pd.notna(ingredients):
                ingredient_analysis = info.get('ingredient_analysis', {})
                report.append(f"  【成分分析】")
                report.append(f"    成分数: {ingredient_analysis.get('ingredient_count', 0)}")
                report.append(f"    主成分: {', '.join(ingredient_analysis.get('ingredient_list', [])[:5])}")
                
                if ingredient_analysis.get('has_acetaminophen'):
                    report.append(f"    ✓ アセトアミノフェン含有（胃への負担が少ない）")
                if ingredient_analysis.get('has_ibuprofen'):
                    report.append(f"    ✓ イブプロフェン含有（NSAIDs、抗炎症作用あり）")
                if ingredient_analysis.get('has_loxoprofen'):
                    report.append(f"    ✓ ロキソプロフェン含有（NSAIDs、強力な鎮痛・抗炎症）")
                if ingredient_analysis.get('has_aspirin'):
                    report.append(f"    ✓ アスピリン含有（NSAIDs、小児には注意）")
                if ingredient_analysis.get('is_herbal'):
                    report.append(f"    ✓ 漢方薬・生薬製剤")
                report.append("\n")
            
            # 効能効果
            efficacy = info.get('efficacy', '')
            if efficacy and pd.notna(efficacy):
                efficacy_short = str(efficacy)[:200] + "..." if len(str(efficacy)) > 200 else str(efficacy)
                report.append(f"  【効能効果】")
                report.append(f"    {efficacy_short}")
                report.append("\n")
            
            # 推奨理由の分析
            report.append(f"  【推奨理由の分析】")
            
            # 症状ごとの推奨回数
            symptom_counts = []
            for symptom, medicines in analysis['symptom_medicine_map'].items():
                if medicine_name in medicines:
                    symptom_counts.append((symptom, medicines[medicine_name]))
            
            if symptom_counts:
                symptom_counts.sort(key=lambda x: x[1], reverse=True)
                report.append(f"    主な推奨症状:")
                for symptom, symptom_count in symptom_counts[:5]:
                    report.append(f"      - {symptom}: {symptom_count}回")
                report.append("\n")
            
            # 薬剤師の視点からの評価
            report.append(f"  【薬剤師の視点からの評価】")
            
            # 成分数による評価
            ingredient_count = ingredient_analysis.get('ingredient_count', 0) if 'ingredient_analysis' in info else 0
            if ingredient_count <= 3:
                report.append(f"    ✓ 特化型医薬品（成分数: {ingredient_count}）: 特定の症状に特化しており、副作用リスクが低い")
            elif ingredient_count <= 5:
                report.append(f"    ○ 中程度の特化型（成分数: {ingredient_count}）: バランスの取れた配合")
            else:
                report.append(f"    △ 総合型医薬品（成分数: {ingredient_count}）: 複数症状に対応可能だが、不要な成分も含まれる可能性")
            
            # アセトアミノフェンの評価
            if ingredient_analysis.get('has_acetaminophen') and not ingredient_analysis.get('has_nsaids'):
                report.append(f"    ✓ アセトアミノフェン単独: 胃への負担が少なく、小児にも使用可能（年齢制限による）")
                report.append(f"       → 頭痛・発熱に適している")
            
            # NSAIDsの評価
            if ingredient_analysis.get('has_nsaids'):
                if ingredient_analysis.get('has_ibuprofen'):
                    report.append(f"    ✓ イブプロフェン含有: 抗炎症作用があり、炎症を伴う痛み（筋肉痛、関節痛）に適している")
                    report.append(f"       → 15歳未満には使用不可、胃への負担に注意")
                if ingredient_analysis.get('has_loxoprofen'):
                    report.append(f"    ✓ ロキソプロフェン含有: 強力な鎮痛・抗炎症作用、炎症を伴う痛みに適している")
                    report.append(f"       → 15歳未満には使用不可、胃への負担に注意")
            
            # 漢方薬の評価
            if ingredient_analysis.get('is_herbal'):
                report.append(f"    ✓ 漢方薬・生薬製剤: 体質に合わせた選択が重要、副作用が少ない傾向")
            
            report.append("\n")
            
            # より最適な医薬品の検索
            report.append(f"  【より最適な医薬品の検討】")
            if symptom_counts:
                main_symptom = symptom_counts[0][0]
                # 現在の医薬品の成分分析を取得
                current_ingredient_analysis = info.get('ingredient_analysis', {})
                current_has_ibuprofen = current_ingredient_analysis.get('has_ibuprofen', False)
                current_has_acetaminophen = current_ingredient_analysis.get('has_acetaminophen', False)
                
                alternatives = find_better_alternatives(medicine_name, main_symptom, medicine_df, info)
                
                if alternatives:
                    report.append(f"    主症状「{main_symptom}」に対する代替候補:")
                    for i, alt in enumerate(alternatives[:5], 1):  # 上位5件
                        alt_ingredient_analysis = alt.get('ingredient_analysis', {})
                        report.append(f"\n    {i}. {alt['product_name']} ({alt.get('manufacturer', '不明')})")
                        report.append(f"       分類: {alt.get('classification', '不明')}")
                        report.append(f"       成分数: {alt_ingredient_analysis.get('ingredient_count', 0)}")
                        report.append(f"       年齢制限: {alt.get('age_limit', 'なし') if pd.notna(alt.get('age_limit')) else 'なし'}")
                        
                        # 成分の詳細
                        if alt_ingredient_analysis.get('has_acetaminophen'):
                            report.append(f"       ✓ アセトアミノフェン含有")
                        if alt_ingredient_analysis.get('has_ibuprofen'):
                            report.append(f"       ✓ イブプロフェン含有（NSAIDs）")
                        if alt_ingredient_analysis.get('has_loxoprofen'):
                            report.append(f"       ✓ ロキソプロフェン含有（NSAIDs）")
                        
                        # なぜより適切かの理由
                        reasons = []
                        if alt_ingredient_analysis.get('has_acetaminophen') and not alt_ingredient_analysis.get('has_nsaids'):
                            if '頭痛' in main_symptom or '発熱' in main_symptom:
                                reasons.append("アセトアミノフェン単独で頭痛・発熱に適している（胃への負担が少ない）")
                                if current_has_ibuprofen:
                                    reasons.append("イブプロフェンより胃への負担が少ない")
                        if alt_ingredient_analysis.get('has_nsaids'):
                            if '筋肉痛' in main_symptom or '関節痛' in main_symptom or '腰痛' in main_symptom:
                                reasons.append("NSAIDsで炎症を伴う痛みに適している")
                        if alt_ingredient_analysis.get('ingredient_count', 0) < ingredient_count:
                            reasons.append(f"成分数が少なく（{alt_ingredient_analysis.get('ingredient_count', 0)} vs {ingredient_count}）、特化型")
                        if alt.get('priority') == 'high':
                            reasons.append("【高優先度】頭痛・発熱に特に適したアセトアミノフェン単独製剤")
                        
                        if reasons:
                            report.append(f"       推奨理由:")
                            for reason in reasons:
                                report.append(f"         - {reason}")
                else:
                    report.append(f"    代替候補の検索中に該当する医薬品が見つかりませんでした。")
            report.append("\n")
            
            report.append("-" * 120)
            report.append("\n")
    
    return "\n".join(report)

if __name__ == "__main__":
    print("データを読み込み中...")
    medicine_df = load_medicine_data()
    print(f"医薬品データ読み込み完了: {len(medicine_df)}件")
    
    print("ログファイルを解析中...")
    recommendations = parse_test_log()
    print(f"推奨ケース読み込み完了: {len(recommendations)}件")
    
    print("推奨医薬品を分析中...")
    analysis = analyze_recommendations(recommendations, medicine_df)
    
    print("薬剤師の視点からの分析レポートを生成中...")
    report = generate_pharmacist_analysis_report(analysis, medicine_df)
    
    # レポートをファイルに保存
    output_file = 'pharmacist_analysis_report.txt'
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print("\n" + report)
    print(f"\n\nレポートを '{output_file}' に保存しました。")

