#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
推奨医薬品の適切性評価スクリプト
ユーザー入力と推奨医薬品の詳細な分析
"""

import re
import json
from collections import defaultdict
from datetime import datetime

LOG_FILE = "/Users/yuto/medicine-recommend-system/log/log1.log"

# 分析データ
evaluation_data = {
    'recommendations': [],
    'no_recommendations': [],
    'errors': [],
}

def extract_user_input_and_recommendations():
    """ユーザー入力と推奨結果を詳細に抽出"""
    
    print("📊 ログファイルから詳細データを抽出中...\n")
    
    with open(LOG_FILE, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    current_user_input = None
    current_session = None
    in_recommendation_block = False
    recommendation_medicines = []
    recommendation_json = {}
    
    for idx, line in enumerate(lines):
        # セッションIDの検出
        session_match = re.search(r'(?:Session ID|session ID)[:：]\s*(\d+)', line)
        if session_match:
            current_session = session_match.group(1)
        
        # ユーザー入力の検出
        if 'ユーザー入力:' in line:
            user_input_match = re.search(r'ユーザー入力[:：]\s*(.+)', line)
            if user_input_match:
                current_user_input = user_input_match.group(1).strip()
                timestamp_match = re.match(r'^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})', line)
                current_timestamp = timestamp_match.group(1) if timestamp_match else None
        
        # 症状分析結果の検出
        if 'ChatGPT応答:' in line and current_user_input:
            # 次の数行でJSONを収集
            json_start = idx
            json_lines = []
            for j in range(idx, min(idx + 10, len(lines))):
                json_lines.append(lines[j])
                if '}' in lines[j] and '"symptoms"' in ''.join(json_lines):
                    try:
                        json_text = ''.join(json_lines).split('ChatGPT応答:')[-1].strip()
                        json_data = json.loads(json_text)
                        detected_symptoms = json_data.get('symptoms', [])
                        medicine_type = json_data.get('medicine_type', '')
                    except:
                        pass
                    break
        
        # 推奨医薬品の検出（JSONフォーマット）
        if '"recommended_medicines":' in line:
            in_recommendation_block = True
            recommendation_medicines = []
        
        if in_recommendation_block and '"product_name":' in line:
            name_match = re.search(r'"product_name":\s*"([^"]+)"', line)
            manufacturer_match = re.search(r'"manufacturer":\s*"([^"]+)"', line)
            
            if name_match:
                med_name = name_match.group(1)
                manufacturer = manufacturer_match.group(1) if manufacturer_match else "不明"
                
                # 理由を探す
                reason = ""
                for j in range(idx, min(idx + 5, len(lines))):
                    reason_match = re.search(r'"reason":\s*"([^"]+)"', lines[j])
                    if reason_match:
                        reason = reason_match.group(1)
                        break
                
                recommendation_medicines.append({
                    'name': med_name,
                    'manufacturer': manufacturer,
                    'reason': reason
                })
        
        # 推奨結果の終了
        if '=== 推奨結果 ===' in line and current_user_input:
            if recommendation_medicines:
                evaluation_data['recommendations'].append({
                    'user_input': current_user_input,
                    'session': current_session,
                    'timestamp': current_timestamp,
                    'medicines': recommendation_medicines.copy(),
                    'detected_symptoms': detected_symptoms if 'detected_symptoms' in locals() else [],
                    'medicine_type': medicine_type if 'medicine_type' in locals() else ''
                })
            recommendation_medicines = []
            in_recommendation_block = False
        
        # エラーや医薬品が見つからなかったケース
        if '医薬品が見つかりませんでした' in line or '推奨システムエラー' in line:
            if current_user_input:
                # 前後の行からエラー理由を探す
                error_reason = ""
                for j in range(max(0, idx-5), min(idx+10, len(lines))):
                    if 'エラー理由:' in lines[j]:
                        reason_match = re.search(r'エラー理由:</strong>\s*([^<]+)', lines[j])
                        if reason_match:
                            error_reason = reason_match.group(1).strip()
                            break
                
                evaluation_data['no_recommendations'].append({
                    'user_input': current_user_input,
                    'session': current_session,
                    'timestamp': current_timestamp,
                    'reason': error_reason or '該当する医薬品が見つかりませんでした'
                })

def evaluate_recommendation_quality():
    """推奨の質を評価"""
    
    print("=" * 100)
    print("📋 推奨医薬品の詳細評価")
    print("=" * 100)
    print()
    
    # 症状キーワードと期待される医薬品タイプのマッピング
    expected_medicines = {
        '頭痛': {
            'types': ['解熱鎮痛薬', '鎮痛薬'],
            'examples': ['ロキソニン', 'イブ', 'バファリン', 'タイレノール', 'ノーシン', 'セデス'],
            'severity': 'medium'
        },
        '腰痛': {
            'types': ['解熱鎮痛薬', '鎮痛薬', '外用薬'],
            'examples': ['ロキソニン', 'ボルタレン', 'バンテリン'],
            'severity': 'medium'
        },
        '腰が痛い': {
            'types': ['解熱鎮痛薬', '鎮痛薬'],
            'examples': ['ロキソニン', 'ボルタレン'],
            'severity': 'medium'
        },
        '喉が痛い': {
            'types': ['風邪薬', '咽喉薬'],
            'examples': ['ペラック', 'のどぬーる', 'ルル', 'パブロン'],
            'severity': 'low'
        },
        '蕁麻疹': {
            'types': ['抗アレルギー薬', '皮膚疾患薬'],
            'examples': ['ナリピット', 'ダーマン', '十味敗毒散'],
            'severity': 'medium'
        },
        '鼻水': {
            'types': ['風邪薬', '抗アレルギー薬'],
            'examples': ['パブロン', 'アレグラ', 'アレジオン'],
            'severity': 'low'
        },
        '熱': {
            'types': ['解熱鎮痛薬', '風邪薬'],
            'examples': ['ロキソニン', 'バファリン', 'ルル'],
            'severity': 'high'
        },
        '眠い': {
            'types': [],
            'examples': [],
            'severity': 'non-medical',
            'note': '医薬品の適応ではない可能性が高い'
        },
        '心が痛い': {
            'types': [],
            'examples': [],
            'severity': 'non-medical',
            'note': '精神的な症状、または医薬品の適応外'
        },
        '緊張': {
            'types': [],
            'examples': [],
            'severity': 'non-medical',
            'note': '市販薬での対応は限定的'
        },
        '足': {
            'types': ['解熱鎮痛薬', '外用薬'],
            'examples': ['ロキソニン', 'バンテリン', 'フェイタス'],
            'severity': 'medium'
        },
    }
    
    evaluations = []
    
    # 推奨があったケースの評価
    print(f"📊 推奨があったケース: {len(evaluation_data['recommendations'])}件\n")
    
    for i, rec in enumerate(evaluation_data['recommendations'], 1):
        user_input = rec['user_input']
        medicines = rec['medicines']
        
        print(f"{'=' * 80}")
        print(f"評価 {i}: {user_input}")
        print(f"{'=' * 80}")
        print(f"セッション: {rec['session']}")
        print(f"時刻: {rec['timestamp']}")
        print(f"検出された症状: {rec.get('detected_symptoms', [])}")
        print(f"医薬品タイプ: {rec.get('medicine_type', '')}")
        print()
        
        # ユーザー入力から症状を判定
        matched_symptoms = []
        for symptom, info in expected_medicines.items():
            if symptom in user_input:
                matched_symptoms.append((symptom, info))
        
        if not matched_symptoms:
            print("⚠️ **入力から明確な症状キーワードが検出されませんでした**")
            print(f"   ユーザー入力: 「{user_input}」")
            print()
        
        # 推奨された医薬品
        print(f"推奨された医薬品 ({len(medicines)}件):")
        for j, med in enumerate(medicines, 1):
            print(f"  {j}. {med['name']} (製造: {med['manufacturer']})")
            if med.get('reason'):
                print(f"     理由: {med['reason']}")
        print()
        
        # 適切性の評価
        print("**適切性評価**:")
        
        if not matched_symptoms:
            print("❓ 評価困難 - 入力から明確な症状が判定できないため、適切性の評価が難しい")
            evaluation_score = "不明"
        else:
            is_appropriate = False
            evaluation_details = []
            
            for symptom, expected in matched_symptoms:
                print(f"\n症状「{symptom}」に対する評価:")
                
                # 深刻度のチェック
                severity = expected.get('severity', 'unknown')
                if severity == 'non-medical':
                    print(f"  ⚠️ この症状は市販薬での対応が適切でない可能性があります")
                    print(f"     理由: {expected.get('note', '')}")
                    evaluation_details.append(f"「{symptom}」は市販薬の適応外の可能性")
                    continue
                elif severity == 'high':
                    print(f"  ⚠️ 深刻度が高い症状です - 医療機関の受診を推奨すべき")
                
                # 推奨された医薬品が適切かチェック
                for med in medicines:
                    med_name = med['name']
                    
                    # 期待される医薬品の例と照合
                    if any(exp in med_name for exp in expected['examples']):
                        print(f"  ✅ {med_name}: 「{symptom}」の治療に適切")
                        is_appropriate = True
                        evaluation_details.append(f"✅ {med_name} - 適切")
                    else:
                        # 医薬品タイプが合致するかチェック
                        if rec.get('medicine_type') in expected['types']:
                            print(f"  ✓ {med_name}: 医薬品タイプは適切（{rec.get('medicine_type')}）")
                            evaluation_details.append(f"✓ {med_name} - タイプは適切")
                        else:
                            print(f"  ⚠️ {med_name}: 一般的な推奨とは異なる可能性")
                            evaluation_details.append(f"⚠️ {med_name} - 要確認")
            
            if is_appropriate:
                evaluation_score = "適切"
            elif evaluation_details:
                evaluation_score = "部分的に適切"
            else:
                evaluation_score = "要確認"
        
        evaluations.append({
            'user_input': user_input,
            'score': evaluation_score,
            'medicines': medicines,
            'matched_symptoms': [s[0] for s in matched_symptoms]
        })
        
        print(f"\n総合評価: {evaluation_score}")
        print()
    
    # 推奨がなかったケースの評価
    print(f"\n{'=' * 100}")
    print(f"📊 推奨がなかったケース: {len(evaluation_data['no_recommendations'])}件")
    print(f"{'=' * 100}\n")
    
    for i, no_rec in enumerate(evaluation_data['no_recommendations'], 1):
        user_input = no_rec['user_input']
        
        print(f"{'=' * 80}")
        print(f"ケース {i}: {user_input}")
        print(f"{'=' * 80}")
        print(f"セッション: {no_rec['session']}")
        print(f"時刻: {no_rec['timestamp']}")
        print(f"理由: {no_rec['reason']}")
        print()
        
        # このケースで推奨がなかったことが適切かを評価
        matched_symptoms = []
        for symptom, info in expected_medicines.items():
            if symptom in user_input:
                matched_symptoms.append((symptom, info))
        
        if matched_symptoms:
            print("**評価**:")
            for symptom, expected in matched_symptoms:
                severity = expected.get('severity', 'unknown')
                if severity == 'non-medical':
                    print(f"✅ 適切な対応 - 「{symptom}」は市販薬の適応外である可能性が高い")
                    print(f"   {expected.get('note', '')}")
                elif expected['examples']:
                    print(f"⚠️ 改善の余地あり - 「{symptom}」に対して推奨できる医薬品が存在する")
                    print(f"   例: {', '.join(expected['examples'][:3])}")
                else:
                    print(f"✅ 適切な対応 - 「{symptom}」に対する明確な市販薬が限定的")
        else:
            print("✅ 適切な対応 - 入力から明確な症状が判定できず、推奨が困難")
        
        print()
    
    # サマリー
    print(f"\n{'=' * 100}")
    print("📊 評価サマリー")
    print(f"{'=' * 100}\n")
    
    if evaluations:
        score_counts = defaultdict(int)
        for ev in evaluations:
            score_counts[ev['score']] += 1
        
        print("推奨の適切性分布:")
        for score, count in sorted(score_counts.items()):
            percentage = (count / len(evaluations)) * 100
            print(f"  - {score}: {count}件 ({percentage:.1f}%)")
        print()
    
    print(f"推奨あり: {len(evaluation_data['recommendations'])}件")
    print(f"推奨なし: {len(evaluation_data['no_recommendations'])}件")
    print(f"総評価ケース: {len(evaluation_data['recommendations']) + len(evaluation_data['no_recommendations'])}件")
    print()
    
    return evaluations

def generate_evaluation_report(evaluations):
    """評価レポートを生成"""
    
    report = []
    report.append("# 📊 推奨医薬品の適切性評価レポート\n")
    report.append(f"**分析日時**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    report.append(f"**対象ファイル**: `{LOG_FILE}`\n")
    report.append("\n" + "=" * 100 + "\n")
    
    report.append("\n## エグゼクティブサマリー\n")
    report.append(f"- **推奨があったケース**: {len(evaluation_data['recommendations'])}件\n")
    report.append(f"- **推奨がなかったケース**: {len(evaluation_data['no_recommendations'])}件\n")
    
    if evaluations:
        score_counts = defaultdict(int)
        for ev in evaluations:
            score_counts[ev['score']] += 1
        
        report.append(f"\n### 推奨の適切性分布:\n")
        for score, count in sorted(score_counts.items(), key=lambda x: -x[1]):
            percentage = (count / len(evaluations)) * 100
            report.append(f"- **{score}**: {count}件 ({percentage:.1f}%)\n")
    
    report.append("\n" + "=" * 100 + "\n")
    
    # 詳細評価
    report.append("\n## 詳細評価\n")
    
    report.append("\n### 推奨があったケースの評価\n")
    
    for i, rec in enumerate(evaluation_data['recommendations'], 1):
        report.append(f"\n#### ケース {i}: {rec['user_input']}\n")
        report.append(f"- **セッション**: `{rec['session']}`\n")
        report.append(f"- **時刻**: {rec['timestamp']}\n")
        report.append(f"- **検出された症状**: {', '.join(rec.get('detected_symptoms', [])) or 'なし'}\n")
        report.append(f"- **医薬品タイプ**: {rec.get('medicine_type', 'なし')}\n")
        
        report.append(f"\n**推奨された医薬品** ({len(rec['medicines'])}件):\n")
        for med in rec['medicines']:
            report.append(f"- {med['name']} (製造: {med['manufacturer']})\n")
            if med.get('reason'):
                report.append(f"  - 推奨理由: {med['reason']}\n")
        
        # 評価結果を追加
        eval_result = next((e for e in evaluations if e['user_input'] == rec['user_input']), None)
        if eval_result:
            report.append(f"\n**総合評価**: {eval_result['score']}\n")
        
        report.append("\n" + "-" * 80 + "\n")
    
    # 推奨がなかったケース
    report.append("\n### 推奨がなかったケースの評価\n")
    
    for i, no_rec in enumerate(evaluation_data['no_recommendations'], 1):
        report.append(f"\n#### ケース {i}: {no_rec['user_input']}\n")
        report.append(f"- **セッション**: `{no_rec['session']}`\n")
        report.append(f"- **時刻**: {no_rec['timestamp']}\n")
        report.append(f"- **理由**: {no_rec['reason']}\n")
        
        report.append("\n" + "-" * 80 + "\n")
    
    # 結論と推奨事項
    report.append("\n" + "=" * 100 + "\n")
    report.append("\n## 結論と推奨事項\n")
    
    if len(evaluation_data['recommendations']) > 0:
        success_rate = (len([e for e in evaluations if e['score'] == '適切']) / len(evaluations)) * 100
        report.append(f"\n### 推奨の適切性: {success_rate:.1f}%\n")
        
        if success_rate >= 80:
            report.append("\n✅ **優秀**: 推奨システムは高い精度で適切な医薬品を推奨しています。\n")
        elif success_rate >= 60:
            report.append("\n✓ **良好**: 推奨システムは概ね適切に機能していますが、改善の余地があります。\n")
        else:
            report.append("\n⚠️ **要改善**: 推奨システムの精度向上が必要です。\n")
    
    report.append("\n### 改善提案:\n")
    report.append("1. 症状が不明確な入力に対する質問機能の強化\n")
    report.append("2. 市販薬の適応外の症状に対する適切なガイダンス\n")
    report.append("3. 深刻度の高い症状に対する医療機関受診の推奨強化\n")
    
    report.append("\n" + "=" * 100 + "\n")
    
    # ファイルに保存
    output_file = "/Users/yuto/medicine-recommend-system/medicine_recommendation_evaluation_report.md"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(''.join(report))
    
    print(f"✅ 評価レポート保存完了: {output_file}\n")
    
    return ''.join(report)

def main():
    print("=" * 100)
    print("📊 推奨医薬品の適切性評価ツール")
    print("=" * 100)
    print()
    
    # データ抽出
    extract_user_input_and_recommendations()
    
    print(f"\n抽出完了:")
    print(f"  - 推奨あり: {len(evaluation_data['recommendations'])}件")
    print(f"  - 推奨なし: {len(evaluation_data['no_recommendations'])}件\n")
    
    # 評価実施
    evaluations = evaluate_recommendation_quality()
    
    # レポート生成
    report = generate_evaluation_report(evaluations)
    
    print("=" * 100)
    print("🎉 評価完了")
    print("=" * 100)

if __name__ == "__main__":
    main()

