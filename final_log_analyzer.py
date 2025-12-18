#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
最終版ログ分析スクリプト
すべての医薬品推奨情報を正確に抽出し、詳細なレポートを生成します
"""

import re
import json
from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Any, Set
import statistics

class FinalLogAnalyzer:
    def __init__(self, log_file: str):
        self.log_file = log_file
        self.sessions = defaultdict(lambda: {
            'user_messages': [],
            'bot_responses': [],
            'recommended_medicines': [],
            'errors': [],
            'performance': []
        })
        self.unique_users = set()
        self.all_errors = []
        self.all_performance = []
        self.medicine_recommendations = []  # {user_input, product_name, details}
        
    def analyze_log(self):
        """ログファイルを分析"""
        print("=== 最終版ログ分析開始 ===\n")
        
        with open(self.log_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        total_lines = len(lines)
        print(f"総行数: {total_lines}行\n")
        
        current_session = None
        current_user_message = None
        
        for i, line in enumerate(lines):
            if (i + 1) % 1000 == 0:
                print(f"処理中... {i+1}/{total_lines}行")
            
            # タイムスタンプとログレベルを除去
            match = re.search(r'\d{4}-\d{2}-\d{2}T[\d:.]+Z (.+)', line)
            if not match:
                continue
            log_content = match.group(1)
            
            # セッションIDの検出
            session_match = re.search(r'Session ID: (\d+)', log_content)
            if session_match:
                current_session = session_match.group(1)
            
            # ユーザー作成の検出
            user_created = re.search(r'New user created: (ユーザー\d+)', log_content)
            if user_created:
                self.unique_users.add(user_created.group(1))
            
            # ユーザーメッセージの検出
            user_msg_patterns = [
                r'User Message: (.+)',
                r'📝 受信メッセージ: (.+)',
                r'ユーザー入力: (.+)'
            ]
            for pattern in user_msg_patterns:
                user_msg = re.search(pattern, log_content)
                if user_msg and current_session:
                    msg = user_msg.group(1).strip()
                    if msg not in self.sessions[current_session]['user_messages']:
                        current_user_message = msg
                        self.sessions[current_session]['user_messages'].append(msg)
                    break
            
            # エラーの検出
            if ' - ERROR - ' in log_content or ' - WARNING - ' in log_content:
                error_info = {
                    'session': current_session,
                    'message': log_content
                }
                self.all_errors.append(error_info)
                if current_session:
                    self.sessions[current_session]['errors'].append(log_content)
            
            # パフォーマンス（実行時間）の検出
            exec_time = re.search(r'Execution Time: ([\d.]+)s', log_content)
            if exec_time:
                time_ms = float(exec_time.group(1)) * 1000
                perf_info = {
                    'session': current_session,
                    'time_ms': time_ms
                }
                self.all_performance.append(perf_info)
                if current_session:
                    self.sessions[current_session]['performance'].append(time_ms)
            
            # 応答時間の検出
            duration_match = re.search(r'duration: (\d+)ms', log_content)
            if duration_match:
                time_ms = float(duration_match.group(1))
                perf_info = {
                    'session': current_session,
                    'time_ms': time_ms
                }
                self.all_performance.append(perf_info)
                if current_session:
                    self.sessions[current_session]['performance'].append(time_ms)
            
            # Response Dataの検出
            if 'Response Data:' in log_content and 'recommended_medicines' in log_content:
                # JSONデータを抽出
                json_match = re.search(r'Response Data: (\{.+\})', log_content)
                if json_match:
                    json_str = json_match.group(1)
                    try:
                        # JSONをパース
                        data = json.loads(json_str)
                        
                        if 'recommendation' in data and 'recommended_medicines' in data['recommendation']:
                            medicines = data['recommendation']['recommended_medicines']
                            symptoms = data['recommendation'].get('symptoms', [])
                            medicine_type = data['recommendation'].get('medicine_type', '')
                            
                            for med in medicines:
                                if isinstance(med, dict) and 'product_name' in med:
                                    med_info = {
                                        'session': current_session,
                                        'user_input': current_user_message,
                                        'product_name': med['product_name'],
                                        'manufacturer': med.get('manufacturer', ''),
                                        'medicine_type': med.get('medicine_type', medicine_type),
                                        'symptoms': symptoms,
                                        'efficacy': med.get('efficacy', ''),
                                        'reason': med.get('reason', ''),
                                        'score': med.get('score', 0),
                                        'doping_prohibited': med.get('doping_prohibited', ''),
                                        'ingredients': med.get('ingredients', ''),
                                    }
                                    self.medicine_recommendations.append(med_info)
                                    if current_session:
                                        self.sessions[current_session]['recommended_medicines'].append(med_info)
                    except json.JSONDecodeError as e:
                        # JSONのパースに失敗した場合は正規表現で抽出を試みる
                        pass
        
        print(f"\n=== 分析完了 ===\n")
        print(f"抽出した医薬品推奨総数: {len(self.medicine_recommendations)}件\n")
    
    def generate_comprehensive_report(self, output_file: str):
        """包括的なレポートを生成"""
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("=" * 100 + "\n")
            f.write("包括的ログ分析レポート（最終版）\n")
            f.write(f"生成日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("=" * 100 + "\n\n")
            
            # 1. ユーザー数
            f.write("【1. ユニークユーザー数】\n")
            f.write("-" * 100 + "\n")
            f.write(f"総ユーザー数: {len(self.unique_users)}人\n\n")
            f.write(f"ユーザーリスト:\n")
            for i, user in enumerate(sorted(self.unique_users), 1):
                f.write(f"  {i}. {user}\n")
            f.write("\n\n")
            
            # 2. チャット数
            f.write("【2. 総メッセージ交換数】\n")
            f.write("-" * 100 + "\n")
            total_user_msgs = sum(len(s['user_messages']) for s in self.sessions.values())
            total_bot_msgs = len(self.medicine_recommendations)  # 推奨があった場合はボット応答があったと仮定
            total_msgs = total_user_msgs + total_bot_msgs
            
            f.write(f"総メッセージ数: {total_msgs}件\n")
            f.write(f"  - ユーザー入力: {total_user_msgs}件\n")
            f.write(f"  - ボット応答（推奨あり）: {total_bot_msgs}件\n")
            f.write(f"総セッション数: {len(self.sessions)}セッション\n")
            f.write("\n\n")
            
            # 3. エラー
            f.write("【3. エラーログ】\n")
            f.write("-" * 100 + "\n")
            f.write(f"総エラー数: {len(self.all_errors)}件\n\n")
            
            # エラータイプ別に集計
            error_types = defaultdict(list)
            for error in self.all_errors:
                msg = error['message']
                if '症状が検出できませんでした' in msg:
                    error_types['症状検出エラー'].append(error)
                elif 'Rule-based algorithm error' in msg:
                    error_types['ルールベースアルゴリズムエラー'].append(error)
                elif 'セッションIDがDBに存在しません' in msg:
                    error_types['セッション復旧警告'].append(error)
                elif '医薬品種類が判定できませんでした' in msg:
                    error_types['医薬品種類判定エラー'].append(error)
                elif '候補医薬品が見つかりませんでした' in msg:
                    error_types['医薬品候補なしエラー'].append(error)
                elif '極端に短い入力が検出されました' in msg:
                    error_types['短い入力警告'].append(error)
                elif '404 Not Found' in msg:
                    error_types['404エラー'].append(error)
                else:
                    error_types['その他のエラー'].append(error)
            
            f.write("【エラータイプ別集計】\n")
            for error_type, errors in sorted(error_types.items(), key=lambda x: len(x[1]), reverse=True):
                f.write(f"  - {error_type}: {len(errors)}件\n")
            
            f.write("\n【詳細エラーリスト】\n")
            for i, error in enumerate(self.all_errors, 1):
                f.write(f"\n[エラー {i}]\n")
                f.write(f"  セッション: {error['session']}\n")
                # エラーメッセージが長い場合は短縮
                error_msg = error['message']
                if len(error_msg) > 200:
                    error_msg = error_msg[:200] + "..."
                f.write(f"  メッセージ: {error_msg}\n")
            
            f.write("\n\n")
            
            # 4. セッション詳細
            f.write("【4. セッション詳細（全トランスクリプト）】\n")
            f.write("-" * 100 + "\n")
            f.write(f"総セッション数: {len(self.sessions)}セッション\n\n")
            
            for session_id, data in sorted(self.sessions.items()):
                f.write(f"\n{'='*80}\n")
                f.write(f"セッションID: {session_id}\n")
                f.write(f"{'='*80}\n")
                
                f.write(f"ユーザー入力数: {len(data['user_messages'])}件\n")
                f.write(f"推奨医薬品数: {len(data['recommended_medicines'])}件\n")
                f.write(f"エラー数: {len(data['errors'])}件\n")
                f.write(f"パフォーマンス測定数: {len(data['performance'])}件\n")
                
                if data['user_messages']:
                    f.write(f"\n【ユーザー入力一覧】\n")
                    for i, msg in enumerate(data['user_messages'], 1):
                        f.write(f"  [{i}] {msg}\n")
                
                if data['recommended_medicines']:
                    f.write(f"\n【推奨医薬品一覧】\n")
                    for i, rec in enumerate(data['recommended_medicines'], 1):
                        f.write(f"  [{i}] {rec['product_name']}")
                        if rec['manufacturer']:
                            f.write(f" （{rec['manufacturer']}）")
                        f.write("\n")
                
                f.write("\n")
            
            f.write("\n\n")
            
            # 5. パフォーマンス
            f.write("【5. パフォーマンス指標】\n")
            f.write("-" * 100 + "\n")
            
            if self.all_performance:
                times = [p['time_ms'] for p in self.all_performance]
                f.write(f"総測定回数: {len(times)}回\n")
                f.write(f"平均処理時間: {statistics.mean(times):.2f} ミリ秒\n")
                f.write(f"中央値: {statistics.median(times):.2f} ミリ秒\n")
                f.write(f"最小値: {min(times):.2f} ミリ秒\n")
                f.write(f"最大値: {max(times):.2f} ミリ秒\n")
                if len(times) > 1:
                    f.write(f"標準偏差: {statistics.stdev(times):.2f} ミリ秒\n")
                
                # パーセンタイル
                sorted_times = sorted(times)
                p25 = sorted_times[len(sorted_times) // 4] if len(sorted_times) >= 4 else sorted_times[0]
                p75 = sorted_times[len(sorted_times) * 3 // 4] if len(sorted_times) >= 4 else sorted_times[-1]
                p90 = sorted_times[len(sorted_times) * 9 // 10] if len(sorted_times) >= 10 else sorted_times[-1]
                p95 = sorted_times[len(sorted_times) * 95 // 100] if len(sorted_times) >= 20 else sorted_times[-1]
                
                f.write(f"25パーセンタイル: {p25:.2f} ミリ秒\n")
                f.write(f"75パーセンタイル: {p75:.2f} ミリ秒\n")
                f.write(f"90パーセンタイル: {p90:.2f} ミリ秒\n")
                f.write(f"95パーセンタイル: {p95:.2f} ミリ秒\n")
            else:
                f.write("パフォーマンスデータが検出されませんでした。\n")
            
            f.write("\n\n")
            
            # 6. 推奨医薬品リスト
            f.write("【6. 推奨医薬品の全リスト】\n")
            f.write("-" * 100 + "\n")
            f.write(f"推奨された医薬品総数: {len(self.medicine_recommendations)}件\n")
            
            unique_medicines = {}
            for rec in self.medicine_recommendations:
                name = rec['product_name']
                if name not in unique_medicines:
                    unique_medicines[name] = {
                        'count': 0,
                        'manufacturer': rec['manufacturer'],
                        'medicine_type': rec['medicine_type'],
                        'user_inputs': [],
                        'efficacy': rec['efficacy'],
                        'ingredients': rec['ingredients']
                    }
                unique_medicines[name]['count'] += 1
                if rec['user_input'] and rec['user_input'] not in unique_medicines[name]['user_inputs']:
                    unique_medicines[name]['user_inputs'].append(rec['user_input'])
            
            f.write(f"ユニーク医薬品数: {len(unique_medicines)}件\n\n")
            
            f.write("【ユニーク医薬品詳細リスト】\n")
            for i, (name, info) in enumerate(sorted(unique_medicines.items(), key=lambda x: x[1]['count'], reverse=True), 1):
                f.write(f"\n[{i}] {name}\n")
                f.write(f"    メーカー: {info['manufacturer']}\n")
                f.write(f"    種類: {info['medicine_type']}\n")
                f.write(f"    推奨回数: {info['count']}回\n")
                if info['efficacy']:
                    efficacy_short = info['efficacy'][:100] + "..." if len(info['efficacy']) > 100 else info['efficacy']
                    f.write(f"    効能: {efficacy_short}\n")
                if info['ingredients']:
                    ingredients_short = info['ingredients'][:100] + "..." if len(info['ingredients']) > 100 else info['ingredients']
                    f.write(f"    成分: {ingredients_short}\n")
                if info['user_inputs']:
                    f.write(f"    対応症状: {', '.join(info['user_inputs'][:5])}\n")
                    if len(info['user_inputs']) > 5:
                        f.write(f"              他{len(info['user_inputs']) - 5}件\n")
            
            f.write("\n\n")
            
            # 7. 推奨医薬品の評価
            f.write("【7. 推奨医薬品の薬剤師評価】\n")
            f.write("-" * 100 + "\n")
            f.write("各ユーザー入力に対する推奨医薬品の適切性を薬剤師の観点から評価します。\n\n")
            
            # ユーザー入力ごとにグループ化
            grouped = defaultdict(list)
            for rec in self.medicine_recommendations:
                if rec['user_input']:
                    grouped[rec['user_input']].append(rec)
            
            f.write(f"評価対象の症状入力数: {len(grouped)}件\n\n")
            
            for i, (user_input, recs) in enumerate(sorted(grouped.items()), 1):
                f.write(f"\n{'='*80}\n")
                f.write(f"[症状入力 {i}] {user_input}\n")
                f.write(f"{'='*80}\n")
                f.write(f"推奨された医薬品数: {len(recs)}件\n\n")
                
                f.write("【推奨医薬品リスト】\n")
                for j, rec in enumerate(recs, 1):
                    f.write(f"  [{j}] {rec['product_name']}")
                    if rec['manufacturer']:
                        f.write(f" （{rec['manufacturer']}）")
                    f.write("\n")
                    if rec['medicine_type']:
                        f.write(f"       種類: {rec['medicine_type']}\n")
                    if rec['reason']:
                        reason_short = rec['reason'][:150] + "..." if len(rec['reason']) > 150 else rec['reason']
                        f.write(f"       推奨理由: {reason_short}\n")
                    if rec['efficacy']:
                        efficacy_short = rec['efficacy'][:100] + "..." if len(rec['efficacy']) > 100 else rec['efficacy']
                        f.write(f"       効能: {efficacy_short}\n")
                
                f.write("\n【薬剤師による適切性評価】\n")
                evaluation = self._evaluate_recommendation(user_input, recs)
                f.write(evaluation)
                f.write("\n")
            
            f.write("\n" + "=" * 100 + "\n")
            f.write("レポート終了\n")
            f.write("=" * 100 + "\n")
    
    def _evaluate_recommendation(self, user_input: str, recs: List[Dict]) -> str:
        """薬剤師として推奨医薬品を評価"""
        evaluation = ""
        
        # 症状キーワードの抽出
        symptom_keywords = {
            '頭痛': ['頭痛', '頭が痛い', '後頭部'],
            '発熱': ['熱', '発熱', '高熱'],
            '咳': ['咳', 'せき'],
            '鼻水': ['鼻水', '鼻づまり', 'くしゃみ'],
            '喉の痛み': ['喉', 'のど', '喉が痛い'],
            '腹痛': ['腹痛', 'お腹が痛い', '胃痛', 'おなかがいたい'],
            '下痢': ['下痢', 'げり'],
            '便秘': ['便秘'],
            '吐き気': ['吐き気', '気持ち悪い', 'むかつき'],
            '筋肉痛・関節痛': ['筋肉痛', '関節痛', '肩が痛い', '腰が痛い', '足が痛い', '足首が痛い', 'ふくらはぎ'],
            '神経痛': ['神経痛', 'ピリピリ', 'しびれ', '痺れ'],
            '不眠': ['眠れない', '不眠'],
            '皮膚症状': ['湿疹', 'かゆみ', '皮膚炎', '蕁麻疹', 'じんましん'],
        }
        
        detected_symptoms = []
        for symptom, keywords in symptom_keywords.items():
            if any(keyword in user_input for keyword in keywords):
                detected_symptoms.append(symptom)
        
        evaluation += f"【検出された症状】\n"
        if detected_symptoms:
            evaluation += f"  {', '.join(detected_symptoms)}\n"
        else:
            evaluation += f"  明確な症状キーワードが検出されませんでした\n"
        evaluation += "\n"
        
        # 推奨された医薬品タイプの集計
        medicine_types = defaultdict(int)
        for rec in recs:
            if rec['medicine_type']:
                medicine_types[rec['medicine_type']] += 1
        
        evaluation += "【推奨された医薬品タイプ】\n"
        if medicine_types:
            for med_type, count in sorted(medicine_types.items(), key=lambda x: x[1], reverse=True):
                evaluation += f"  - {med_type}: {count}件\n"
        else:
            evaluation += "  医薬品タイプの情報なし\n"
        evaluation += "\n"
        
        # 適切性の評価
        evaluation += "【適切性評価】\n"
        
        if not detected_symptoms:
            evaluation += "⚠️ 明確な症状が検出されないため、適切性の評価が困難です。\n"
            evaluation += "ℹ️ より具体的な症状の記述が推奨システムの精度向上につながります。\n"
        else:
            # 症状と医薬品の適合性をチェック
            appropriate_reasons = []
            warning_reasons = []
            
            if '頭痛' in detected_symptoms or '筋肉痛・関節痛' in detected_symptoms or '神経痛' in detected_symptoms:
                relevant_types = ['解熱鎮痛薬', '外用薬（皮膚）', '鎮痛薬', '外用薬']
                if any(any(rt in mt for mt in medicine_types.keys()) for rt in relevant_types):
                    appropriate_reasons.append("✅ 痛みの症状に対して適切な鎮痛薬・外用薬が推奨されています。")
                else:
                    warning_reasons.append("⚠️ 痛みの症状に対する鎮痛薬が含まれていない可能性があります。")
            
            if '喉の痛み' in detected_symptoms or '咳' in detected_symptoms:
                if any('風邪薬' in mt or '鎮咳' in mt or '去痰' in mt for mt in medicine_types.keys()):
                    appropriate_reasons.append("✅ 喉の痛みや咳に対して適切な風邪薬・鎮咳薬が推奨されています。")
                else:
                    warning_reasons.append("⚠️ 喉の症状に対する専用薬が推奨されていません。")
            
            if '鼻水' in detected_symptoms:
                if any('風邪薬' in mt or '鼻炎' in mt or 'アレルギー' in mt for mt in medicine_types.keys()):
                    appropriate_reasons.append("✅ 鼻水に対して適切な風邪薬・鼻炎薬が推奨されています。")
            
            if '腹痛' in detected_symptoms or '下痢' in detected_symptoms:
                if any('胃腸薬' in mt or '整腸' in mt for mt in medicine_types.keys()):
                    appropriate_reasons.append("✅ 胃腸症状に対して適切な胃腸薬が推奨されています。")
                else:
                    warning_reasons.append("ℹ️ 胃腸症状に特化した薬が推奨されていない可能性があります。")
            
            if '皮膚症状' in detected_symptoms:
                if any('アレルギー' in mt or '外用薬' in mt or '皮膚' in mt for mt in medicine_types.keys()):
                    appropriate_reasons.append("✅ 皮膚症状に対して適切な抗アレルギー薬・外用薬が推奨されています。")
            
            if '発熱' in detected_symptoms:
                if any('解熱' in mt or '風邪薬' in mt for mt in medicine_types.keys()):
                    appropriate_reasons.append("✅ 発熱に対して適切な解熱鎮痛薬が推奨されています。")
            
            for reason in appropriate_reasons:
                evaluation += reason + "\n"
            
            for reason in warning_reasons:
                evaluation += reason + "\n"
            
            if not appropriate_reasons and not warning_reasons:
                evaluation += "ℹ️ 標準的な症状パターンとの照合ができませんでした。\n"
                evaluation += "   特殊な症状や、一般用医薬品では対応が難しい症状の可能性があります。\n"
            
            # 総合評価
            evaluation += "\n【総合評価】\n"
            if len(appropriate_reasons) > len(warning_reasons) and appropriate_reasons:
                evaluation += "✅ 概ね適切な推奨と考えられます。\n"
                evaluation += "   推奨された医薬品は症状に対応していると評価できます。\n"
            elif len(warning_reasons) > 0:
                evaluation += "⚠️ 一部改善の余地があります。\n"
                evaluation += "   より症状に特化した薬の検討を推奨します。\n"
            else:
                evaluation += "ℹ️ さらなる詳細情報があればより精度の高い評価が可能です。\n"
                evaluation += "   症状の詳細や、症状の程度、持続期間などの情報が有用です。\n"
        
        return evaluation


def main():
    log_file = '/Users/yuto/medicine-recommend-system/log/log1.log'
    output_file = '/Users/yuto/medicine-recommend-system/final_log_analysis_report.txt'
    
    print("最終版ログ分析を開始します...\n")
    
    analyzer = FinalLogAnalyzer(log_file)
    
    # ログ分析
    analyzer.analyze_log()
    
    # 包括的レポート生成
    print(f"\n包括的レポートを生成中: {output_file}\n")
    analyzer.generate_comprehensive_report(output_file)
    
    print(f"\n✅ 分析完了！レポートが保存されました: {output_file}\n")
    print(f"\n【分析結果サマリー】")
    print(f"  - ユニークユーザー数: {len(analyzer.unique_users)}人")
    print(f"  - 総セッション数: {len(analyzer.sessions)}セッション")
    print(f"  - 総エラー数: {len(analyzer.all_errors)}件")
    print(f"  - 医薬品推奨総数: {len(analyzer.medicine_recommendations)}件")
    
    unique_meds = set(m['product_name'] for m in analyzer.medicine_recommendations)
    print(f"  - ユニーク医薬品数: {len(unique_meds)}種類")
    print(f"  - パフォーマンス測定回数: {len(analyzer.all_performance)}回")
    
    if analyzer.all_performance:
        times = [p['time_ms'] for p in analyzer.all_performance]
        print(f"  - 平均応答時間: {statistics.mean(times):.2f}ms")
        print(f"  - 中央値応答時間: {statistics.median(times):.2f}ms")
    
    # ユーザー入力ごとの推奨数を集計
    grouped = defaultdict(int)
    for rec in analyzer.medicine_recommendations:
        if rec['user_input']:
            grouped[rec['user_input']] += 1
    
    print(f"  - 評価対象の症状入力数: {len(grouped)}件")


if __name__ == '__main__':
    main()

