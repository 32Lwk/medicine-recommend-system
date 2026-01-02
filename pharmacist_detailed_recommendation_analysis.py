"""
薬剤師の視点から推奨医薬品を詳細分析するスクリプト
"""
import json
import pandas as pd
from collections import defaultdict, Counter

def load_data():
    """データを読み込む"""
    # ログ分析結果を読み込み
    with open('/Users/yuto/medicine-recommend-system/detailed_log_analysis.json', 'r', encoding='utf-8') as f:
        log_data = json.load(f)
    
    # 医薬品データを読み込み
    medicine_df = pd.read_csv('/Users/yuto/medicine-recommend-system/data/otc_medicine_data.csv')
    
    return log_data, medicine_df

def get_medicine_info(medicine_name, medicine_df):
    """医薬品の詳細情報を取得"""
    matches = medicine_df[medicine_df['製品名'].str.contains(medicine_name, na=False, regex=False)]
    if len(matches) > 0:
        matches = matches.copy()
        matches['name_length'] = matches['製品名'].str.len()
        matches = matches.sort_values('name_length', ascending=False)
        return matches.iloc[0].to_dict()
    return None

def analyze_headache_recommendations(log_data, medicine_df):
    """頭痛に対する推奨を分析"""
    symptom_medicines = log_data['symptom_medicine_counts'].get('頭痛', {})
    medicine_details = log_data['medicine_details']
    
    analysis = {
        'current_recommendations': [],
        'recommended_alternatives': [],
        'inappropriate_recommendations': []
    }
    
    # 現在推奨されている医薬品を分析
    for medicine, count in sorted(symptom_medicines.items(), key=lambda x: x[1], reverse=True):
        info = medicine_details.get(medicine, {})
        if not info:
            info = get_medicine_info(medicine, medicine_df)
        
        if info:
            efficacy = info.get('efficacy', '')
            medicine_type = info.get('medicine_type', '')
            ingredients = info.get('ingredients', '')
            
            # 効能効果に頭痛が含まれているかチェック
            has_headache_efficacy = '頭痛' in efficacy
            
            # 不適切な推奨をチェック
            inappropriate_reasons = []
            if '大柴胡湯' in medicine:
                if '高血圧に伴う頭痛' not in efficacy or '高血圧に伴う頭痛' in efficacy:
                    # 一般的な頭痛には不適切（高血圧に伴う頭痛のみ適応）
                    inappropriate_reasons.append('高血圧に伴う頭痛のみが適応。一般的な頭痛には不適切')
            
            if 'ケイブク' in medicine:
                inappropriate_reasons.append('効能効果は「打撲症」のみ。頭痛には適応外')
            
            if 'ビトラック' in medicine:
                inappropriate_reasons.append('効能効果は「ひざの痛み又はむくみ」のみ。頭痛には適応外')
            
            if inappropriate_reasons:
                analysis['inappropriate_recommendations'].append({
                    'medicine': medicine,
                    'count': count,
                    'efficacy': efficacy[:200],
                    'reasons': inappropriate_reasons
                })
            else:
                analysis['current_recommendations'].append({
                    'medicine': medicine,
                    'count': count,
                    'efficacy': efficacy[:200],
                    'has_headache_efficacy': has_headache_efficacy,
                    'medicine_type': medicine_type,
                    'ingredients': ingredients[:200] if isinstance(ingredients, str) else str(ingredients)[:200]
                })
    
    # 推奨されるべき代替医薬品を検索
    # カロナールA、ロキソニンS、タイレノールを検索
    alternative_medicines = ['カロナールＡ', 'ロキソニンＳ', 'タイレノールＡ']
    for alt_med in alternative_medicines:
        info = get_medicine_info(alt_med, medicine_df)
        if info:
            efficacy = info.get('効能効果', '')
            if '頭痛' in efficacy:
                analysis['recommended_alternatives'].append({
                    'medicine': alt_med,
                    'efficacy': efficacy[:200],
                    'medicine_type': info.get('医薬品の種類', ''),
                    'classification': info.get('分類', ''),
                    'ingredients': info.get('成分', '')[:200] if isinstance(info.get('成分', ''), str) else '',
                    'age_restriction': info.get('年齢制限', ''),
                    'advantage': get_headache_medicine_advantage(alt_med, info)
                })
    
    return analysis

def get_headache_medicine_advantage(medicine_name, info):
    """頭痛に対する医薬品の優位性を取得"""
    advantages = []
    ingredients = str(info.get('成分', '')).lower()
    efficacy = info.get('効能効果', '')
    classification = info.get('分類', '')
    
    if 'アセトアミノフェン' in ingredients:
        advantages.append('アセトアミノフェン含有 - 胃に優しく、副作用が少ない。頭痛の第一選択として推奨される')
        advantages.append('幅広い年齢層に適用可能（15歳以上）')
        advantages.append('抗炎症作用がないため、炎症を伴わない頭痛に適している')
    
    if 'ロキソプロフェン' in ingredients:
        advantages.append('ロキソプロフェン含有 - 即効性があり、強い痛みに対応')
        advantages.append('抗炎症作用が強く、炎症を伴う頭痛に効果的')
    
    if 'イブプロフェン' in ingredients:
        advantages.append('イブプロフェン含有 - 抗炎症作用が強く、炎症を伴う頭痛に効果的')
        advantages.append('カフェイン配合で、鎮痛効果が増強される')
    
    if '第2類' in classification:
        advantages.append('第2類医薬品 - 薬剤師の説明が推奨されるが、一般販売可能')
    elif '第1類' in classification:
        advantages.append('第1類医薬品 - 薬剤師による説明が義務付けられている')
    
    if '頭痛' in efficacy and '発熱' in efficacy:
        advantages.append('頭痛・発熱の両方に効果的')
    
    return advantages

def analyze_fever_recommendations(log_data, medicine_df):
    """発熱に対する推奨を分析"""
    symptom_medicines = log_data['symptom_medicine_counts'].get('発熱', {})
    medicine_details = log_data['medicine_details']
    
    analysis = {
        'current_recommendations': [],
        'recommended_alternatives': [],
        'inappropriate_recommendations': []
    }
    
    # 現在推奨されている医薬品を分析
    for medicine, count in sorted(symptom_medicines.items(), key=lambda x: x[1], reverse=True):
        info = medicine_details.get(medicine, {})
        if not info:
            info = get_medicine_info(medicine, medicine_df)
        
        if info:
            efficacy = info.get('efficacy', '')
            medicine_type = info.get('medicine_type', '')
            
            # 効能効果に発熱が含まれているかチェック
            has_fever_efficacy = any(kw in efficacy for kw in ['発熱', '熱', '解熱'])
            
            # 不適切な推奨をチェック
            inappropriate_reasons = []
            if '大柴胡湯' in medicine:
                inappropriate_reasons.append('効能効果に発熱が含まれていない')
            
            if 'ハイゼリー' in medicine or 'ヘパリーゼ' in medicine:
                # 発熱性消耗性疾患は適切だが、解熱作用はない
                if '発熱性消耗性疾患' in efficacy:
                    # 栄養補給目的であり、解熱作用はない
                    inappropriate_reasons.append('栄養補給目的であり、解熱作用はない。解熱には適切な解熱鎮痛薬を推奨すべき')
            
            if inappropriate_reasons:
                analysis['inappropriate_recommendations'].append({
                    'medicine': medicine,
                    'count': count,
                    'efficacy': efficacy[:200],
                    'reasons': inappropriate_reasons
                })
            else:
                analysis['current_recommendations'].append({
                    'medicine': medicine,
                    'count': count,
                    'efficacy': efficacy[:200],
                    'has_fever_efficacy': has_fever_efficacy,
                    'medicine_type': medicine_type
                })
    
    # 推奨されるべき代替医薬品を検索
    alternative_medicines = ['カロナールＡ', 'ロキソニンＳ', 'タイレノールＡ']
    for alt_med in alternative_medicines:
        info = get_medicine_info(alt_med, medicine_df)
        if info:
            efficacy = info.get('効能効果', '')
            if any(kw in efficacy for kw in ['発熱', '熱', '解熱']):
                analysis['recommended_alternatives'].append({
                    'medicine': alt_med,
                    'efficacy': efficacy[:200],
                    'medicine_type': info.get('医薬品の種類', ''),
                    'classification': info.get('分類', ''),
                    'ingredients': info.get('成分', '')[:200] if isinstance(info.get('成分', ''), str) else '',
                    'advantage': get_fever_medicine_advantage(alt_med, info)
                })
    
    return analysis

def get_fever_medicine_advantage(medicine_name, info):
    """発熱に対する医薬品の優位性を取得"""
    advantages = []
    ingredients = str(info.get('成分', '')).lower()
    
    if 'アセトアミノフェン' in ingredients:
        advantages.append('アセトアミノフェン含有 - 解熱作用があり、安全性が高い')
        advantages.append('小児から使用可能（年齢制限に注意）')
        advantages.append('胃に優しく、副作用が少ない')
        advantages.append('発熱の第一選択として推奨される')
    
    if 'ロキソプロフェン' in ingredients:
        advantages.append('ロキソプロフェン含有 - 解熱作用があり、即効性がある')
        advantages.append('強い発熱に効果的')
    
    if 'イブプロフェン' in ingredients:
        advantages.append('イブプロフェン含有 - 解熱作用があり、抗炎症作用も期待できる')
        advantages.append('強い発熱に効果的')
    
    return advantages

def analyze_muscle_pain_recommendations(log_data, medicine_df):
    """筋肉痛に対する推奨を分析"""
    # 筋肉痛に関連する症状を検索
    symptom_medicines = {}
    for symptom in ['筋肉痛', '関節痛', '腰痛']:
        if symptom in log_data['symptom_medicine_counts']:
            for med, count in log_data['symptom_medicine_counts'][symptom].items():
                symptom_medicines[med] = symptom_medicines.get(med, 0) + count
    
    medicine_details = log_data['medicine_details']
    
    analysis = {
        'current_recommendations': [],
        'recommended_alternatives': [],
        'inappropriate_recommendations': []
    }
    
    # 現在推奨されている医薬品を分析
    for medicine, count in sorted(symptom_medicines.items(), key=lambda x: x[1], reverse=True)[:10]:
        info = medicine_details.get(medicine, {})
        if not info:
            info = get_medicine_info(medicine, medicine_df)
        
        if info:
            efficacy = info.get('efficacy', '')
            
            # 不適切な推奨をチェック
            inappropriate_reasons = []
            if 'ケイブク' in medicine:
                inappropriate_reasons.append('効能効果は「打撲症」のみ。一般的な筋肉痛には適応外')
            
            if inappropriate_reasons:
                analysis['inappropriate_recommendations'].append({
                    'medicine': medicine,
                    'count': count,
                    'efficacy': efficacy[:200],
                    'reasons': inappropriate_reasons
                })
            else:
                has_muscle_pain_efficacy = any(kw in efficacy for kw in ['筋肉痛', '関節痛', '腰痛'])
                analysis['current_recommendations'].append({
                    'medicine': medicine,
                    'count': count,
                    'efficacy': efficacy[:200],
                    'has_muscle_pain_efficacy': has_muscle_pain_efficacy
                })
    
    # 推奨されるべき代替医薬品
    alternative_medicines = ['ロキソニンＳ', 'イブＡ錠', '雲仙散']
    for alt_med in alternative_medicines:
        info = get_medicine_info(alt_med, medicine_df)
        if info:
            efficacy = info.get('効能効果', '')
            if any(kw in efficacy for kw in ['筋肉痛', '関節痛', '腰痛']):
                analysis['recommended_alternatives'].append({
                    'medicine': alt_med,
                    'efficacy': efficacy[:200],
                    'medicine_type': info.get('医薬品の種類', ''),
                    'advantage': get_muscle_pain_medicine_advantage(alt_med, info)
                })
    
    return analysis

def get_muscle_pain_medicine_advantage(medicine_name, info):
    """筋肉痛に対する医薬品の優位性を取得"""
    advantages = []
    ingredients = str(info.get('成分', '')).lower()
    efficacy = info.get('効能効果', '')
    
    if 'ロキソプロフェン' in ingredients:
        advantages.append('ロキソプロフェン含有 - 抗炎症作用が強く、筋肉痛に効果的')
        advantages.append('即効性がある')
    
    if 'イブプロフェン' in ingredients:
        advantages.append('イブプロフェン含有 - 抗炎症作用が強く、筋肉痛に効果的')
    
    if '雲仙散' in medicine_name:
        advantages.append('効能効果に「筋肉痛」が明記されている')
        advantages.append('漢方薬として、体質に合わせた治療が可能')
        advantages.append('4歳以上から使用可能')
    
    return advantages

def generate_comprehensive_report():
    """包括的な分析レポートを生成"""
    log_data, medicine_df = load_data()
    
    report = []
    report.append("# 薬剤師の視点からの推奨医薬品詳細分析レポート")
    report.append("")
    report.append("## 分析概要")
    report.append(f"- **総推奨ケース数**: {log_data['total_cases']}件")
    report.append(f"- **ユニークな医薬品数**: {log_data['unique_medicines']}件")
    report.append("")
    
    # 頭痛の分析
    report.append("## 1. 頭痛に対する推奨分析")
    headache_analysis = analyze_headache_recommendations(log_data, medicine_df)
    
    report.append("### 1.1 現在推奨されている医薬品")
    for rec in headache_analysis['current_recommendations']:
        report.append(f"\n**{rec['medicine']}** ({rec['count']}回)")
        report.append(f"- 効能効果: {rec['efficacy']}")
        report.append(f"- 頭痛への効能効果: {'あり' if rec['has_headache_efficacy'] else 'なし'}")
        report.append(f"- 種類: {rec['medicine_type']}")
    
    report.append("\n### 1.2 不適切な推奨")
    for rec in headache_analysis['inappropriate_recommendations']:
        report.append(f"\n**{rec['medicine']}** ({rec['count']}回)")
        for reason in rec['reasons']:
            report.append(f"- ❌ {reason}")
    
    report.append("\n### 1.3 より適切な代替医薬品（推奨されるべき）")
    for alt in headache_analysis['recommended_alternatives']:
        report.append(f"\n**{alt['medicine']}**")
        report.append(f"- 効能効果: {alt['efficacy']}")
        report.append(f"- 分類: {alt['classification']}")
        report.append(f"- 優位性:")
        for adv in alt['advantage']:
            report.append(f"  - ✅ {adv}")
    
    # 発熱の分析
    report.append("\n\n## 2. 発熱に対する推奨分析")
    fever_analysis = analyze_fever_recommendations(log_data, medicine_df)
    
    report.append("### 2.1 現在推奨されている医薬品")
    for rec in fever_analysis['current_recommendations']:
        report.append(f"\n**{rec['medicine']}** ({rec['count']}回)")
        report.append(f"- 効能効果: {rec['efficacy']}")
        report.append(f"- 発熱への効能効果: {'あり' if rec['has_fever_efficacy'] else 'なし'}")
    
    report.append("\n### 2.2 不適切な推奨")
    for rec in fever_analysis['inappropriate_recommendations']:
        report.append(f"\n**{rec['medicine']}** ({rec['count']}回)")
        for reason in rec['reasons']:
            report.append(f"- ❌ {reason}")
    
    report.append("\n### 2.3 より適切な代替医薬品（推奨されるべき）")
    for alt in fever_analysis['recommended_alternatives']:
        report.append(f"\n**{alt['medicine']}**")
        report.append(f"- 効能効果: {alt['efficacy']}")
        report.append(f"- 優位性:")
        for adv in alt['advantage']:
            report.append(f"  - ✅ {adv}")
    
    # 筋肉痛の分析
    report.append("\n\n## 3. 筋肉痛に対する推奨分析")
    muscle_analysis = analyze_muscle_pain_recommendations(log_data, medicine_df)
    
    report.append("### 3.1 現在推奨されている医薬品")
    for rec in muscle_analysis['current_recommendations'][:5]:
        report.append(f"\n**{rec['medicine']}** ({rec['count']}回)")
        report.append(f"- 効能効果: {rec['efficacy']}")
        report.append(f"- 筋肉痛への効能効果: {'あり' if rec['has_muscle_pain_efficacy'] else 'なし'}")
    
    report.append("\n### 3.2 不適切な推奨")
    for rec in muscle_analysis['inappropriate_recommendations']:
        report.append(f"\n**{rec['medicine']}** ({rec['count']}回)")
        for reason in rec['reasons']:
            report.append(f"- ❌ {reason}")
    
    report.append("\n### 3.3 より適切な代替医薬品（推奨されるべき）")
    for alt in muscle_analysis['recommended_alternatives']:
        report.append(f"\n**{alt['medicine']}**")
        report.append(f"- 効能効果: {alt['efficacy']}")
        report.append(f"- 優位性:")
        for adv in alt['advantage']:
            report.append(f"  - ✅ {adv}")
    
    # 総合評価
    report.append("\n\n## 4. 総合評価と改善提案")
    report.append("\n### 4.1 主要な問題点")
    report.append("1. **効能効果に含まれていない症状への推奨**: 大柴胡湯（一般的な頭痛）、ケイブク（頭痛）、ビトラックＳ（頭痛）など")
    report.append("2. **主要解熱鎮痛薬が推奨されていない**: カロナールA、ロキソニンS、タイレノールが頭痛・発熱に対して推奨されていない")
    report.append("3. **栄養補給薬が発熱に推奨されている**: ハイゼリー、ヘパリーゼなど（解熱作用はない）")
    
    report.append("\n### 4.2 改善提案")
    report.append("1. 効能効果チェックの強化（実装済み）")
    report.append("2. 主要解熱鎮痛薬の優先推奨（実装済み）")
    report.append("3. 発熱に対する栄養補給薬の除外")
    
    report_text = '\n'.join(report)
    
    # レポートを保存
    with open('/Users/yuto/medicine-recommend-system/pharmacist_detailed_recommendation_analysis.md', 'w', encoding='utf-8') as f:
        f.write(report_text)
    
    print(report_text)
    print("\n\nレポートを pharmacist_detailed_recommendation_analysis.md に保存しました。")

if __name__ == '__main__':
    generate_comprehensive_report()

