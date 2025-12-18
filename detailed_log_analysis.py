#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
詳細ログ分析スクリプト
ログファイルを分割して正確に分析し、すべての項目を網羅的に出力します
"""

import re
import json
from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Any, Set
import statistics

class DetailedLogAnalyzer:
    def __init__(self, log_file: str):
        self.log_file = log_file
        self.sessions = defaultdict(lambda: {
            'messages': [],
            'user_messages': [],
            'bot_responses': [],
            'recommended_medicines': [],
            'errors': [],
            'performance': []
        })
        self.unique_users = set()
        self.all_errors = []
        self.all_performance = []
        self.all_medicines = []
        self.user_inputs_with_recommendations = []
        
    def analyze_in_chunks(self, chunk_size: int = 1100):
        """ログファイルを分割して処理"""
        print("=== ログファイル分析開始 ===\n")
        
        with open(self.log_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        total_lines = len(lines)
        print(f"総行数: {total_lines}行\n")
        
        num_chunks = (total_lines // chunk_size) + (1 if total_lines % chunk_size > 0 else 0)
        print(f"分割数: {num_chunks}チャンク（各約{chunk_size}行）\n")
        
        for i in range(0, total_lines, chunk_size):
            chunk_num = (i // chunk_size) + 1
            chunk_lines = lines[i:i + chunk_size]
            print(f"チャンク {chunk_num}/{num_chunks} 処理中... ({i+1}-{min(i+chunk_size, total_lines)}行)")
            self._process_chunk(chunk_lines)
        
        print("\n=== 分析完了 ===\n")
    
    def _process_chunk(self, lines: List[str]):
        """各チャンクを処理"""
        current_session = None
        current_user_message = None
        
        for line in lines:
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
            user_msg = re.search(r'User Message: (.+)', log_content)
            if user_msg and current_session:
                msg = user_msg.group(1)
                current_user_message = msg
                self.sessions[current_session]['user_messages'].append(msg)
                self.sessions[current_session]['messages'].append({
                    'type': 'user',
                    'content': msg
                })
            
            # 受信メッセージの検出（別パターン）
            received_msg = re.search(r'📝 受信メッセージ: (.+)', log_content)
            if received_msg and current_session:
                msg = received_msg.group(1)
                if msg not in self.sessions[current_session]['user_messages']:
                    current_user_message = msg
                    self.sessions[current_session]['user_messages'].append(msg)
                    self.sessions[current_session]['messages'].append({
                        'type': 'user',
                        'content': msg
                    })
            
            # 医薬品推奨の検出
            medicine_match = re.search(r'推奨完了: (\d+)件の医薬品を推奨', log_content)
            if medicine_match and current_session:
                count = int(medicine_match.group(1))
                if current_user_message:
                    self.sessions[current_session]['recommended_medicines'].append({
                        'user_input': current_user_message,
                        'count': count
                    })
            
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
            
            # 応答時間の検出（別パターン）
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
    
    def extract_medicines_detailed(self):
        """医薬品情報を詳細に抽出"""
        print("\n=== 医薬品情報の詳細抽出開始 ===\n")
        
        with open(self.log_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # ボット応答から医薬品情報を抽出
        # JSONパターンで医薬品情報を検出
        medicine_pattern = r'"product_name":\s*"([^"]+)"'
        medicines = re.findall(medicine_pattern, content)
        
        # 各セッションの推奨医薬品とユーザー入力を関連付け
        current_session = None
        current_user_input = None
        
        for line in content.split('\n'):
            # セッションIDの検出
            session_match = re.search(r'Session ID: (\d+)', line)
            if session_match:
                current_session = session_match.group(1)
            
            # ユーザー入力の検出
            user_input = re.search(r'(?:User Message|📝 受信メッセージ): (.+)', line)
            if user_input:
                current_user_input = user_input.group(1)
            
            # 医薬品名の検出
            med_match = re.search(r'"product_name":\s*"([^"]+)"', line)
            if med_match and current_user_input and current_session:
                medicine_name = med_match.group(1)
                self.user_inputs_with_recommendations.append({
                    'session': current_session,
                    'user_input': current_user_input,
                    'medicine': medicine_name
                })
                self.all_medicines.append(medicine_name)
        
        print(f"抽出した医薬品総数: {len(self.all_medicines)}件\n")
    
    def generate_comprehensive_report(self, output_file: str):
        """包括的なレポートを生成"""
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("=" * 100 + "\n")
            f.write("詳細ログ分析レポート\n")
            f.write("=" * 100 + "\n\n")
            
            # 1. ユーザー数
            f.write("【1. ユニークユーザー数】\n")
            f.write("-" * 100 + "\n")
            f.write(f"総ユーザー数: {len(self.unique_users)}人\n")
            f.write(f"ユーザーリスト: {', '.join(sorted(self.unique_users))}\n")
            f.write("\n\n")
            
            # 2. チャット数
            f.write("【2. 総メッセージ交換数】\n")
            f.write("-" * 100 + "\n")
            total_user_msgs = sum(len(s['user_messages']) for s in self.sessions.values())
            total_bot_msgs = sum(len(s['bot_responses']) for s in self.sessions.values())
            total_msgs = total_user_msgs + total_bot_msgs
            
            f.write(f"総メッセージ数: {total_msgs}件\n")
            f.write(f"  - ユーザー入力: {total_user_msgs}件\n")
            f.write(f"  - ボット応答: {total_bot_msgs}件\n")
            f.write(f"総セッション数: {len(self.sessions)}セッション\n")
            f.write("\n\n")
            
            # 3. エラー
            f.write("【3. エラーログ】\n")
            f.write("-" * 100 + "\n")
            f.write(f"総エラー数: {len(self.all_errors)}件\n\n")
            
            if self.all_errors:
                f.write("エラー詳細リスト:\n")
                for i, error in enumerate(self.all_errors, 1):
                    f.write(f"\n[エラー {i}]\n")
                    f.write(f"  セッション: {error['session']}\n")
                    f.write(f"  メッセージ: {error['message']}\n")
            else:
                f.write("エラーは検出されませんでした。\n")
            f.write("\n\n")
            
            # 4. セッション詳細
            f.write("【4. セッション詳細（全トランスクリプト）】\n")
            f.write("-" * 100 + "\n")
            f.write(f"総セッション数: {len(self.sessions)}セッション\n\n")
            
            for session_id, data in sorted(self.sessions.items()):
                f.write(f"\n{'='*80}\n")
                f.write(f"セッションID: {session_id}\n")
                f.write(f"{'='*80}\n")
                
                f.write(f"メッセージ数: {len(data['messages'])}件\n")
                f.write(f"ユーザー入力数: {len(data['user_messages'])}件\n")
                f.write(f"推奨医薬品記録: {len(data['recommended_medicines'])}件\n")
                f.write(f"エラー数: {len(data['errors'])}件\n")
                
                if data['user_messages']:
                    f.write(f"\nユーザー入力一覧:\n")
                    for i, msg in enumerate(data['user_messages'], 1):
                        f.write(f"  [{i}] {msg}\n")
                
                if data['recommended_medicines']:
                    f.write(f"\n推奨医薬品情報:\n")
                    for i, rec in enumerate(data['recommended_medicines'], 1):
                        f.write(f"  [{i}] ユーザー入力: {rec['user_input']}\n")
                        f.write(f"       推奨件数: {rec['count']}件\n")
                
                if data['errors']:
                    f.write(f"\nエラー:\n")
                    for i, err in enumerate(data['errors'], 1):
                        f.write(f"  [{i}] {err}\n")
                
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
                f.write(f"標準偏差: {statistics.stdev(times) if len(times) > 1 else 0:.2f} ミリ秒\n")
                
                f.write(f"\n詳細データ:\n")
                for i, perf in enumerate(self.all_performance, 1):
                    f.write(f"  [{i}] セッション: {perf['session']}, 処理時間: {perf['time_ms']:.2f}ms\n")
            else:
                f.write("パフォーマンスデータが検出されませんでした。\n")
            
            f.write("\n\n")
            
            # 6. 推奨医薬品リスト
            f.write("【6. 推奨医薬品の全リスト】\n")
            f.write("-" * 100 + "\n")
            f.write(f"推奨された医薬品総数: {len(self.all_medicines)}件\n")
            f.write(f"ユニーク医薬品数: {len(set(self.all_medicines))}件\n\n")
            
            if self.all_medicines:
                unique_medicines = sorted(set(self.all_medicines))
                f.write("ユニーク医薬品リスト:\n")
                for i, med in enumerate(unique_medicines, 1):
                    count = self.all_medicines.count(med)
                    f.write(f"  [{i}] {med} （推奨回数: {count}回）\n")
            
            f.write("\n\n")
            
            # 7. 推奨医薬品の評価
            f.write("【7. 推奨医薬品の薬剤師評価】\n")
            f.write("-" * 100 + "\n")
            f.write("各ユーザー入力に対する推奨医薬品の適切性を評価します。\n\n")
            
            # ユーザー入力ごとにグループ化
            grouped = defaultdict(list)
            for item in self.user_inputs_with_recommendations:
                grouped[item['user_input']].append(item['medicine'])
            
            f.write(f"評価対象の症状入力数: {len(grouped)}件\n\n")
            
            for i, (user_input, medicines) in enumerate(sorted(grouped.items()), 1):
                f.write(f"\n{'='*80}\n")
                f.write(f"[症状入力 {i}]\n")
                f.write(f"{'='*80}\n")
                f.write(f"ユーザー入力: {user_input}\n")
                f.write(f"推奨された医薬品数: {len(medicines)}件\n\n")
                
                f.write("推奨医薬品リスト:\n")
                for j, med in enumerate(medicines, 1):
                    f.write(f"  [{j}] {med}\n")
                
                f.write("\n【薬剤師による評価】\n")
                evaluation = self._evaluate_recommendation(user_input, medicines)
                f.write(evaluation)
                f.write("\n")
            
            f.write("\n" + "=" * 100 + "\n")
            f.write("レポート終了\n")
            f.write("=" * 100 + "\n")
    
    def _evaluate_recommendation(self, user_input: str, medicines: List[str]) -> str:
        """薬剤師として推奨医薬品を評価"""
        evaluation = ""
        
        # 症状キーワードの抽出
        symptom_keywords = {
            '頭痛': ['頭痛', '頭が痛い'],
            '発熱': ['熱', '発熱', '高熱'],
            '咳': ['咳', 'せき'],
            '鼻水': ['鼻水', '鼻づまり', 'くしゃみ'],
            '喉の痛み': ['喉', 'のど', '喉が痛い'],
            '腹痛': ['腹痛', 'お腹が痛い', '胃痛'],
            '下痢': ['下痢', 'げり'],
            '便秘': ['便秘'],
            '吐き気': ['吐き気', '気持ち悪い', 'むかつき'],
            '筋肉痛': ['筋肉痛', '関節痛'],
            '神経痛': ['神経痛', 'ピリピリ'],
            '眠気': ['眠れない', '不眠'],
            '湿疹': ['湿疹', 'かゆみ', '皮膚炎'],
        }
        
        detected_symptoms = []
        for symptom, keywords in symptom_keywords.items():
            if any(keyword in user_input for keyword in keywords):
                detected_symptoms.append(symptom)
        
        evaluation += f"検出された症状: {', '.join(detected_symptoms) if detected_symptoms else '特定の症状が明確ではない'}\n\n"
        
        # 医薬品タイプの推測
        medicine_types = {
            '解熱鎮痛薬': ['アセトアミノフェン', 'イブプロフェン', 'ロキソニン', 'バファリン', 'タイレノール', 'ナロン', 'セデス', 'ノーシン'],
            '総合感冒薬': ['パブロン', 'ルル', 'ベンザ', 'コルゲン', '新コンタック'],
            '鎮咳去痰薬': ['アネトン', 'ブロン'],
            '胃腸薬': ['ガスター', '太田胃散', '正露丸', 'ビオフェルミン'],
            '鼻炎薬': ['アレジオン', 'アレグラ', 'パブロン鼻炎'],
            '外用薬': ['オロナイン', 'ムヒ', 'フェミニーナ'],
        }
        
        recommended_types = defaultdict(list)
        for med in medicines:
            for med_type, keywords in medicine_types.items():
                if any(keyword in med for keyword in keywords):
                    recommended_types[med_type].append(med)
                    break
        
        evaluation += "推奨された医薬品タイプ:\n"
        for med_type, meds in recommended_types.items():
            evaluation += f"  - {med_type}: {len(meds)}件\n"
        evaluation += "\n"
        
        # 適切性の評価
        evaluation += "【適切性評価】\n"
        
        if not detected_symptoms:
            evaluation += "⚠️ 症状が明確でないため、適切性の判断が困難です。\n"
        else:
            # 症状と医薬品の適合性をチェック
            appropriate = True
            reasons = []
            
            if '頭痛' in detected_symptoms or '発熱' in detected_symptoms or '筋肉痛' in detected_symptoms or '神経痛' in detected_symptoms:
                if '解熱鎮痛薬' in recommended_types:
                    reasons.append("✅ 頭痛・発熱・痛みに対して解熱鎮痛薬が推奨されており、適切です。")
                else:
                    appropriate = False
                    reasons.append("⚠️ 痛みや発熱の症状に対して解熱鎮痛薬が推奨されていません。")
            
            if '咳' in detected_symptoms or '喉の痛み' in detected_symptoms:
                if '鎮咳去痰薬' in recommended_types or '総合感冒薬' in recommended_types:
                    reasons.append("✅ 咳・喉の症状に対して適切な薬が推奨されています。")
                else:
                    appropriate = False
                    reasons.append("⚠️ 咳・喉の症状に対する専用薬が推奨されていません。")
            
            if '鼻水' in detected_symptoms or 'くしゃみ' in user_input:
                if '鼻炎薬' in recommended_types or '総合感冒薬' in recommended_types:
                    reasons.append("✅ 鼻症状に対して適切な薬が推奨されています。")
                else:
                    appropriate = False
                    reasons.append("⚠️ 鼻症状に対する専用薬が推奨されていません。")
            
            if '腹痛' in detected_symptoms or '下痢' in detected_symptoms or '吐き気' in detected_symptoms:
                if '胃腸薬' in recommended_types:
                    reasons.append("✅ 胃腸症状に対して適切な薬が推奨されています。")
                else:
                    appropriate = False
                    reasons.append("⚠️ 胃腸症状に対する専用薬が推奨されていません。")
            
            for reason in reasons:
                evaluation += reason + "\n"
            
            if not reasons:
                evaluation += "ℹ️ 一般的な症状パターンと推奨医薬品の適合性を確認できませんでした。\n"
            
            if appropriate and reasons:
                evaluation += "\n総合評価: ✅ 適切な推奨と考えられます。\n"
            elif not appropriate:
                evaluation += "\n総合評価: ⚠️ 一部改善の余地があります。\n"
            else:
                evaluation += "\n総合評価: ℹ️ より詳細な情報が必要です。\n"
        
        return evaluation


def main():
    log_file = '/Users/yuto/medicine-recommend-system/log/log1.log'
    output_file = '/Users/yuto/medicine-recommend-system/detailed_analysis_report.txt'
    
    print("詳細ログ分析を開始します...\n")
    
    analyzer = DetailedLogAnalyzer(log_file)
    
    # 分割処理で分析
    analyzer.analyze_in_chunks(chunk_size=1050)
    
    # 医薬品情報の詳細抽出
    analyzer.extract_medicines_detailed()
    
    # 包括的レポート生成
    print(f"\n包括的レポートを生成中: {output_file}\n")
    analyzer.generate_comprehensive_report(output_file)
    
    print(f"\n✅ 分析完了！レポートが保存されました: {output_file}\n")
    print(f"統計サマリー:")
    print(f"  - ユニークユーザー数: {len(analyzer.unique_users)}")
    print(f"  - 総セッション数: {len(analyzer.sessions)}")
    print(f"  - 総エラー数: {len(analyzer.all_errors)}")
    print(f"  - 推奨医薬品総数: {len(analyzer.all_medicines)}")
    print(f"  - ユニーク医薬品数: {len(set(analyzer.all_medicines))}")
    print(f"  - パフォーマンス測定回数: {len(analyzer.all_performance)}")


if __name__ == '__main__':
    main()
