#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
詳細ログ分析スクリプト - 10分割処理版
Response Data行の長いJSONを確実に読み取る
"""

import json
import ast
import re
from datetime import datetime
from collections import defaultdict, Counter
from typing import Dict, List, Any, Tuple
import statistics

class DetailedLogAnalyzer:
    def __init__(self, log_file_path: str):
        self.log_file_path = log_file_path
        self.total_lines = 0
        
        # 分析結果を格納
        self.unique_users = set()
        self.sessions = defaultdict(list)  # session_id -> messages list
        self.errors = []
        self.processing_times = []
        self.recommended_medicines = []
        self.user_inputs_and_recommendations = []
        self.chat_count = 0
        
    def analyze_in_chunks(self, num_chunks: int = 10):
        """ログファイルを分割して分析"""
        print(f"📊 ログファイル分析開始: {self.log_file_path}")
        print(f"📦 {num_chunks}個のチャンクに分割して処理します\n")
        
        # まず総行数を取得
        with open(self.log_file_path, 'r', encoding='utf-8') as f:
            self.total_lines = sum(1 for _ in f)
        
        print(f"✅ 総行数: {self.total_lines:,}行\n")
        
        # チャンクサイズを計算
        chunk_size = self.total_lines // num_chunks
        
        # 各チャンクを処理
        for chunk_idx in range(num_chunks):
            start_line = chunk_idx * chunk_size
            # 最後のチャンクは残り全部
            end_line = start_line + chunk_size if chunk_idx < num_chunks - 1 else self.total_lines
            
            print(f"🔍 チャンク {chunk_idx + 1}/{num_chunks} を処理中...")
            print(f"   行範囲: {start_line + 1:,} ~ {end_line:,}")
            
            self._process_chunk(start_line, end_line, chunk_idx + 1)
            
            print(f"✅ チャンク {chunk_idx + 1} 処理完了\n")
        
        print("=" * 80)
        print("📊 全チャンクの処理完了！結果を生成します...\n")
        
    def _process_chunk(self, start_line: int, end_line: int, chunk_num: int):
        """特定の行範囲を処理"""
        current_session = None
        current_user_message = None
        
        with open(self.log_file_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f):
                # 行範囲外はスキップ
                if line_num < start_line:
                    continue
                if line_num >= end_line:
                    break
                
                line = line.strip()
                if not line:
                    continue
                
                # ユーザー作成/アクセスログ
                if 'New user created:' in line or 'Existing session accessed:' in line:
                    user_match = re.search(r'(New user created|Existing session accessed): ([^\s]+)', line)
                    if user_match:
                        username = user_match.group(2)
                        self.unique_users.add(username)
                
                # セッションID検出
                session_match = re.search(r'Session ID: (\d+)', line)
                if session_match:
                    current_session = session_match.group(1)
                
                # ユーザーメッセージ検出
                if '📝 受信メッセージ:' in line or 'User Message:' in line:
                    msg_match = re.search(r'(📝 受信メッセージ:|User Message:)\s*(.+)$', line)
                    if msg_match:
                        user_msg = msg_match.group(2).strip()
                        current_user_message = user_msg
                        self.chat_count += 1
                        
                        if current_session:
                            self.sessions[current_session].append({
                                'type': 'user',
                                'message': user_msg,
                                'timestamp': self._extract_timestamp(line)
                            })
                
                # Response Data検出（長いJSON）
                if 'Response Data:' in line:
                    # Response Data: の後のJSONを抽出
                    response_match = re.search(r'Response Data:\s*(\{.+)$', line)
                    if response_match:
                        try:
                            response_json_str = response_match.group(1)
                            # Python辞書形式（シングルクォート）を解析
                            response_data = ast.literal_eval(response_json_str)
                            
                            self.chat_count += 1  # ボット応答もカウント
                            
                            # メッセージの抽出
                            bot_message = ''
                            if 'message' in response_data:
                                bot_message = response_data.get('message', '')
                            elif 'recommendation' in response_data:
                                # recommendationの中にメッセージがある場合
                                rec = response_data['recommendation']
                                bot_message = rec.get('message', '')
                            
                            if current_session:
                                self.sessions[current_session].append({
                                    'type': 'bot',
                                    'message': bot_message,
                                    'data': response_data,
                                    'timestamp': self._extract_timestamp(line)
                                })
                            
                            # 推奨医薬品の抽出（複数のパターンに対応）
                            medicines = []
                            
                            # パターン1: 直接medicinesキーがある場合
                            if 'medicines' in response_data:
                                medicines = response_data['medicines']
                            
                            # パターン2: recommendationの中にrecommended_medicinesがある場合
                            elif 'recommendation' in response_data:
                                rec = response_data['recommendation']
                                if 'recommended_medicines' in rec:
                                    medicines = rec['recommended_medicines']
                            
                            # パターン3: recommendationの中にmedicinesがある場合
                            elif 'recommendation' in response_data and 'medicines' in response_data['recommendation']:
                                medicines = response_data['recommendation']['medicines']
                            
                            if medicines:
                                for med in medicines:
                                    # 複数のキー名に対応
                                    med_name = (med.get('商品名') or 
                                               med.get('product_name') or 
                                               med.get('name') or 
                                               'Unknown')
                                    self.recommended_medicines.append(med_name)
                                
                                # ユーザー入力と推奨医薬品のペアを保存
                                if current_user_message:
                                    self.user_inputs_and_recommendations.append({
                                        'user_input': current_user_message,
                                        'medicines': medicines,
                                        'session_id': current_session,
                                        'timestamp': self._extract_timestamp(line)
                                    })
                        except (json.JSONDecodeError, ValueError, SyntaxError) as e:
                            # JSON/Python辞書解析エラー - デバッグ用に記録
                            if current_session:
                                self.sessions[current_session].append({
                                    'type': 'bot',
                                    'message': f'[解析エラー: {str(e)[:100]}]',
                                    'data': None,
                                    'timestamp': self._extract_timestamp(line)
                                })
                        except Exception as e:
                            # その他のエラー
                            pass
                
                # エラー検出
                if ' - ERROR - ' in line or ' - WARNING - ' in line:
                    error_type = 'ERROR' if ' - ERROR - ' in line else 'WARNING'
                    error_msg = line.split(f' - {error_type} - ', 1)[-1] if f' - {error_type} - ' in line else line
                    self.errors.append({
                        'type': error_type,
                        'message': error_msg,
                        'timestamp': self._extract_timestamp(line),
                        'line_num': line_num + 1
                    })
                
                # 処理時間検出
                if 'Execution Time:' in line or 'duration:' in line:
                    time_match = re.search(r'(Execution Time|duration):\s*([0-9.]+)\s*(s|ms)', line)
                    if time_match:
                        time_val = float(time_match.group(2))
                        unit = time_match.group(3)
                        # ミリ秒に統一
                        if unit == 's':
                            time_val *= 1000
                        self.processing_times.append(time_val)
    
    def _extract_timestamp(self, line: str) -> str:
        """行からタイムスタンプを抽出"""
        ts_match = re.search(r'(\d{4}-\d{2}-\d{2}[T\s]\d{2}:\d{2}:\d{2})', line)
        if ts_match:
            return ts_match.group(1)
        return ''
    
    def generate_report(self) -> str:
        """分析結果をレポートとして生成"""
        report = []
        report.append("=" * 100)
        report.append("詳細ログ分析レポート")
        report.append("=" * 100)
        report.append("")
        
        # 1. ユーザー数
        report.append("### 1. ユーザー数")
        report.append(f"ユニークユーザーID総数: {len(self.unique_users)}")
        report.append(f"ユーザーリスト: {sorted(list(self.unique_users))}")
        report.append("")
        
        # 2. チャット数
        report.append("### 2. チャット数")
        report.append(f"総メッセージ交換数（ユーザー入力＋ボット応答）: {self.chat_count}")
        report.append("")
        
        # 3. エラー
        report.append("### 3. エラー")
        report.append(f"エラーログ総数: {len(self.errors)}")
        
        # エラータイプごとの集計
        error_types = Counter(e['type'] for e in self.errors)
        report.append("\nエラータイプ別集計:")
        for err_type, count in error_types.most_common():
            report.append(f"  - {err_type}: {count}件")
        
        report.append("\nエラー詳細リスト:")
        for i, error in enumerate(self.errors, 1):
            report.append(f"\n{i}. [{error['type']}] 行番号: {error['line_num']}")
            report.append(f"   タイムスタンプ: {error['timestamp']}")
            report.append(f"   メッセージ: {error['message'][:200]}...")  # 最初の200文字
        report.append("")
        
        # 4. セッション詳細
        report.append("### 4. セッション詳細（全トランスクリプト）")
        report.append(f"総セッション数: {len(self.sessions)}")
        report.append("")
        
        for session_id, messages in sorted(self.sessions.items()):
            report.append(f"\n--- セッションID: {session_id} ---")
            report.append(f"メッセージ数: {len(messages)}")
            report.append("")
            
            for i, msg in enumerate(messages, 1):
                if msg['type'] == 'user':
                    report.append(f"{i}. [ユーザー入力] {msg['timestamp']}")
                    report.append(f"   {msg['message']}")
                else:
                    report.append(f"{i}. [ボット応答] {msg['timestamp']}")
                    # メッセージの最初の部分を表示
                    bot_msg = msg['message']
                    if isinstance(bot_msg, str):
                        preview = bot_msg[:500] + "..." if len(bot_msg) > 500 else bot_msg
                        report.append(f"   {preview}")
                    else:
                        report.append(f"   {str(bot_msg)[:500]}...")
                report.append("")
        
        report.append("")
        
        # 5. パフォーマンス
        report.append("### 5. パフォーマンス")
        if self.processing_times:
            avg_time = statistics.mean(self.processing_times)
            median_time = statistics.median(self.processing_times)
            min_time = min(self.processing_times)
            max_time = max(self.processing_times)
            
            report.append(f"処理時間統計（ミリ秒）:")
            report.append(f"  - 平均処理時間: {avg_time:.2f} ms")
            report.append(f"  - 中央値: {median_time:.2f} ms")
            report.append(f"  - 最小値: {min_time:.2f} ms")
            report.append(f"  - 最大値: {max_time:.2f} ms")
            report.append(f"  - サンプル数: {len(self.processing_times)}")
        else:
            report.append("処理時間のデータが見つかりませんでした。")
        report.append("")
        
        # 6. 推奨医薬品リスト
        report.append("### 6. 推奨医薬品の抽出")
        report.append(f"推奨された医薬品の総数: {len(self.recommended_medicines)}")
        
        med_counter = Counter(self.recommended_medicines)
        report.append(f"\n推奨医薬品一覧（頻度順）:")
        for med_name, count in med_counter.most_common():
            report.append(f"  - {med_name}: {count}回")
        report.append("")
        
        # 7. 推奨医薬品の評価
        report.append("### 7. 推奨医薬品の評価（薬剤師視点）")
        report.append(f"ユーザー入力と推奨医薬品のペア数: {len(self.user_inputs_and_recommendations)}")
        report.append("")
        
        for i, item in enumerate(self.user_inputs_and_recommendations, 1):
            report.append(f"\n--- 評価 {i} ---")
            report.append(f"セッションID: {item['session_id']}")
            report.append(f"タイムスタンプ: {item['timestamp']}")
            report.append(f"\n【ユーザー入力】")
            report.append(f"{item['user_input']}")
            report.append(f"\n【推奨された医薬品】")
            
            for j, med in enumerate(item['medicines'], 1):
                # 複数のキー名に対応
                med_name = (med.get('商品名') or 
                           med.get('product_name') or 
                           med.get('name') or 
                           'Unknown')
                report.append(f"\n  {j}. {med_name}")
                
                # 医薬品の詳細情報（複数のキー名に対応）
                efficacy = (med.get('効能効果') or 
                           med.get('efficacy') or 
                           med.get('効能') or '')
                if efficacy:
                    efficacy_preview = efficacy[:200] + "..." if len(efficacy) > 200 else efficacy
                    report.append(f"     効能効果: {efficacy_preview}")
                
                ingredients = (med.get('成分') or 
                              med.get('ingredients') or 
                              med.get('主成分') or '')
                if ingredients:
                    ing_str = str(ingredients)
                    ing_preview = ing_str[:200] + "..." if len(ing_str) > 200 else ing_str
                    report.append(f"     成分: {ing_preview}")
                
                # スコア
                score = (med.get('score') or 
                        med.get('total_score') or 
                        med.get('スコア') or 'N/A')
                report.append(f"     スコア: {score}")
                
                # 理由
                reason = (med.get('reason') or 
                         med.get('推奨理由') or '')
                if reason:
                    reason_preview = reason[:200] + "..." if len(reason) > 200 else reason
                    report.append(f"     推奨理由: {reason_preview}")
                
                # 薬剤師視点での評価
                evaluation = self._evaluate_medicine_appropriateness(item['user_input'], med)
                report.append(f"\n     【薬剤師評価】")
                report.append(f"     適切性: {evaluation['appropriateness']}")
                report.append(f"     理由: {evaluation['reason']}")
                report.append(f"     注意点: {evaluation['caution']}")
            
            report.append("")
        
        report.append("=" * 100)
        report.append("レポート終了")
        report.append("=" * 100)
        
        return "\n".join(report)
    
    def _evaluate_medicine_appropriateness(self, user_input: str, medicine: Dict[str, Any]) -> Dict[str, str]:
        """薬剤師視点で推奨医薬品の適切性を評価"""
        user_input_lower = user_input.lower()
        
        # 複数のキー名に対応
        med_name = (medicine.get('商品名') or 
                   medicine.get('product_name') or 
                   medicine.get('name') or 
                   'Unknown')
        
        med_effects = (medicine.get('効能効果') or 
                      medicine.get('efficacy') or 
                      medicine.get('効能') or '').lower()
        
        med_type = (medicine.get('医薬品の種類') or 
                   medicine.get('type') or 
                   medicine.get('medicine_type') or '').lower()
        
        evaluation = {
            'appropriateness': '適切',
            'reason': '',
            'caution': ''
        }
        
        # 症状キーワードと医薬品タイプのマッピング
        symptom_mappings = {
            '頭痛': ['解熱鎮痛', '鎮痛', '頭痛'],
            '発熱': ['解熱', '風邪'],
            '咳': ['咳', '去痰', '風邪'],
            '鼻': ['鼻', '風邪', 'アレルギー'],
            '喉': ['喉', '咽喉', '風邪'],
            '胃': ['胃腸', '消化'],
            '腹痛': ['胃腸', '整腸'],
            '下痢': ['整腸', '止瀉'],
            '便秘': ['便秘', '整腸'],
            '眠': ['睡眠', '催眠'],
            '疲労': ['滋養', 'ビタミン'],
            '筋肉痛': ['鎮痛', '解熱鎮痛'],
            '神経痛': ['鎮痛', '神経痛'],
            '乗り物酔い': ['乗り物酔い', '酔い止め'],
            '目': ['眼科', '目薬'],
            '皮膚': ['皮膚', '外用'],
        }
        
        # ユーザー入力から症状を検出
        detected_symptoms = []
        for symptom, keywords in symptom_mappings.items():
            if symptom in user_input:
                detected_symptoms.append(symptom)
        
        # 評価ロジック
        if not detected_symptoms:
            evaluation['appropriateness'] = '要確認'
            evaluation['reason'] = '症状が明確でないため、推奨の適切性を判断できません。'
            evaluation['caution'] = 'より詳細な症状の聞き取りが必要です。'
            return evaluation
        
        # 各症状に対して医薬品が適切かチェック
        appropriate_for_symptoms = []
        for symptom in detected_symptoms:
            keywords = symptom_mappings[symptom]
            if any(keyword in med_effects or keyword in med_type or keyword in med_name.lower() 
                   for keyword in keywords):
                appropriate_for_symptoms.append(symptom)
        
        if appropriate_for_symptoms:
            evaluation['appropriateness'] = '適切'
            evaluation['reason'] = f"検出された症状（{', '.join(detected_symptoms)}）のうち、{', '.join(appropriate_for_symptoms)}に対して有効と考えられます。"
            
            # 注意点を追加
            cautions = []
            if '頭痛' in user_input or '神経痛' in user_input:
                if 'アスピリン' in med_name or 'ロキソ' in med_name:
                    cautions.append('胃腸障害のリスクがあるため、食後服用を推奨。')
            if '眠' in user_input:
                cautions.append('運転や機械操作は避けるよう指導が必要。')
            if '妊' in user_input or '授乳' in user_input:
                cautions.append('妊娠中・授乳中の使用には注意が必要。医師への相談を推奨。')
            
            evaluation['caution'] = ' '.join(cautions) if cautions else '一般的な用法用量を守れば問題ありません。'
        else:
            evaluation['appropriateness'] = '不適切'
            evaluation['reason'] = f"検出された症状（{', '.join(detected_symptoms)}）に対して、この医薬品の効能効果が一致していません。"
            evaluation['caution'] = '他の医薬品を検討するか、症状の詳細確認が必要です。'
        
        return evaluation


def main():
    """メイン実行関数"""
    log_file = "/Users/yuto/medicine-recommend-system/log/log1.log"
    output_file = "/Users/yuto/medicine-recommend-system/detailed_analysis_report.txt"
    
    print("=" * 100)
    print("詳細ログ分析ツール")
    print("=" * 100)
    print()
    
    # 分析実行
    analyzer = DetailedLogAnalyzer(log_file)
    analyzer.analyze_in_chunks(num_chunks=10)
    
    # レポート生成
    print("📝 レポートを生成中...")
    report = analyzer.generate_report()
    
    # ファイルに保存
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"✅ レポートを保存しました: {output_file}")
    print(f"📄 レポートサイズ: {len(report):,} 文字")
    print()
    
    # サマリーを表示
    print("=" * 100)
    print("分析サマリー")
    print("=" * 100)
    print(f"ユニークユーザー数: {len(analyzer.unique_users)}")
    print(f"総チャット数: {analyzer.chat_count}")
    print(f"セッション数: {len(analyzer.sessions)}")
    print(f"エラー数: {len(analyzer.errors)}")
    print(f"推奨医薬品数: {len(analyzer.recommended_medicines)}")
    print(f"評価ペア数: {len(analyzer.user_inputs_and_recommendations)}")
    if analyzer.processing_times:
        print(f"平均処理時間: {statistics.mean(analyzer.processing_times):.2f} ms")
    print("=" * 100)


if __name__ == "__main__":
    main()

