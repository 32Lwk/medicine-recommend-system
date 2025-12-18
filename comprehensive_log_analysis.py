#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
包括的ログ分析スクリプト
log1.logを詳細に分析して、全てのセッション、チャット、推奨医薬品の詳細を出力
"""

import re
import json
import ast
from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Any, Optional

def extract_json_from_line_robust(line: str) -> Optional[Dict]:
    """行からJSONデータを堅牢に抽出"""
    # Response Data: の後のJSONを抽出
    if 'Response Data:' not in line:
        return None
    
    json_start = line.find('Response Data:') + len('Response Data:')
    json_str = line[json_start:].strip()
    
    # Python辞書形式の場合（シングルクォート）をJSON形式に変換
    if json_str.startswith('{'):
        # シングルクォートをダブルクォートに変換（ただし、文字列内のシングルクォートは除外）
        # nanをnullに変換
        json_str = json_str.replace("'", '"').replace('nan', 'null')
        
        # 括弧のバランスを確認してJSONを抽出
        brace_count = 0
        end_pos = 0
        for i, char in enumerate(json_str):
            if char == '{':
                brace_count += 1
            elif char == '}':
                brace_count -= 1
                if brace_count == 0:
                    end_pos = i + 1
                    break
        
        if end_pos > 0:
            try:
                # ast.literal_evalを使用してPython辞書として解析
                json_str_python = line[json_start:json_start+end_pos].strip()
                # シングルクォートをダブルクォートに変換（簡易版）
                # 実際にはast.literal_evalを使う方が安全
                try:
                    data = ast.literal_eval(json_str_python)
                    return data
                except:
                    # JSONとして試行
                    json_str_fixed = json_str[:end_pos].replace("'", '"').replace('nan', 'null')
                    return json.loads(json_str_fixed)
            except Exception as e:
                pass
    
    return None

def extract_session_id(line: str) -> Optional[str]:
    patterns = [
        r'Session ID: (\d+)',
        r'sid=(\d+)',
        r'セッションID: (\d+)',
        r'新規セッション作成: (\d+)',
        r'既存セッション更新: (\d+)',
    ]
    for pattern in patterns:
        match = re.search(pattern, line)
        if match:
            return match.group(1)
    return None

def extract_user_info(line: str) -> Optional[Dict[str, str]]:
    user_match = re.search(r'👤 New user created: (ユーザー\d+)', line)
    if user_match:
        return {'username': user_match.group(1), 'type': 'new'}
    
    user_match = re.search(r'👤 Existing session accessed: (ユーザー\d+)', line)
    if user_match:
        return {'username': user_match.group(1), 'type': 'existing'}
    
    user_match = re.search(r'Username: (ユーザー\d+)', line)
    if user_match:
        return {'username': user_match.group(1), 'type': 'existing'}
    
    return None

def extract_user_input(line: str) -> Optional[str]:
    patterns = [
        r'ユーザー入力: (.+)',
        r'User Message: (.+)',
        r'📝 受信メッセージ: (.+)',
    ]
    for pattern in patterns:
        match = re.search(pattern, line)
        if match:
            return match.group(1).strip()
    return None

def extract_execution_time(line: str) -> Optional[float]:
    match = re.search(r'Execution Time: ([\d.]+)s', line)
    if match:
        return float(match.group(1))
    return None

def extract_error_info(line: str) -> Optional[Dict[str, Any]]:
    error_info = {}
    
    if 'ERROR' in line or ('error' in line.lower() and 'error_type' in line):
        error_info['has_error'] = True
        
        if 'rule_based_error' in line:
            error_info['error_type'] = 'rule_based_error'
        elif 'no_candidates' in line:
            error_info['error_type'] = 'no_candidates'
        elif 'Exception' in line:
            error_info['error_type'] = 'exception'
        
        error_msg_match = re.search(r'error_message[:\'"]+([^\'"]+)', line)
        if error_msg_match:
            error_info['error_message'] = error_msg_match.group(1)
    
    return error_info if error_info else None

def analyze_log_comprehensive(file_path: str):
    """ログファイルを包括的に分析"""
    
    sessions = defaultdict(lambda: {
        'session_id': None,
        'user': None,
        'chats': [],
        'errors': [],
        'total_execution_time': 0,
        'execution_times': []
    })
    
    users = set()
    total_chats = 0
    total_errors = 0
    current_session_id = None
    current_user = None
    current_chat = {}
    chat_counter = 0
    response_data_buffer = []  # 複数行にわたるJSONを蓄積
    
    with open(file_path, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            try:
                # セッションIDの抽出
                session_id = extract_session_id(line)
                if session_id:
                    current_session_id = session_id
                    sessions[session_id]['session_id'] = session_id
                
                # ユーザー情報の抽出
                user_info = extract_user_info(line)
                if user_info:
                    current_user = user_info['username']
                    users.add(current_user)
                    if current_session_id:
                        sessions[current_session_id]['user'] = current_user
                
                # ユーザー入力の抽出
                user_input = extract_user_input(line)
                if user_input:
                    chat_counter += 1
                    current_chat = {
                        'chat_id': chat_counter,
                        'user_input': user_input,
                        'session_id': current_session_id,
                        'user': current_user,
                        'timestamp': None,
                        'response': None,
                        'response_content': None,
                        'recommended_medicines': [],
                        'execution_time': None,
                        'error': None,
                        'status': None,
                        'medicine_type': None,
                        'algorithm': None,
                        'usage_notes': None,
                        'doctor_consultation': None,
                        'additional_questions': None,
                        'critical_questions': None
                    }
                    total_chats += 1
                    if current_session_id:
                        sessions[current_session_id]['chats'].append(current_chat)
                    response_data_buffer = []  # 新しいチャット開始時にバッファをクリア
                
                # Response Data行の検出
                if 'Response Data:' in line:
                    response_data_buffer = [line]
                elif response_data_buffer and ('{' in line or '}' in line or 'recommendation' in line.lower()):
                    response_data_buffer.append(line)
                    
                    # JSONの終了を検出
                    if '}' in line and response_data_buffer:
                        full_json_str = ' '.join(response_data_buffer)
                        json_data = extract_json_from_line_robust(full_json_str)
                        if json_data and current_chat:
                            if 'recommendation' in json_data:
                                rec = json_data['recommendation']
                                current_chat['status'] = rec.get('status', 'unknown')
                                current_chat['medicine_type'] = rec.get('medicine_type')
                                current_chat['algorithm'] = rec.get('algorithm')
                                
                                # レスポンス内容の構築
                                response_parts = []
                                
                                if 'recommended_medicines' in rec and rec['recommended_medicines']:
                                    current_chat['recommended_medicines'] = rec['recommended_medicines']
                                    response_parts.append(f"推奨医薬品: {len(rec['recommended_medicines'])}件")
                                
                                if rec.get('usage_notes'):
                                    current_chat['usage_notes'] = rec.get('usage_notes')
                                    response_parts.append("使用上の注意が含まれています")
                                
                                if rec.get('doctor_consultation'):
                                    current_chat['doctor_consultation'] = rec.get('doctor_consultation')
                                    response_parts.append("医師への相談が必要な場合の情報が含まれています")
                                
                                if rec.get('additional_questions'):
                                    current_chat['additional_questions'] = rec.get('additional_questions')
                                    response_parts.append(f"追加質問: {len(rec['additional_questions'])}件")
                                
                                if rec.get('critical_questions'):
                                    current_chat['critical_questions'] = rec.get('critical_questions')
                                    response_parts.append(f"重要な質問: {len(rec['critical_questions'])}件")
                                
                                if rec.get('symptoms'):
                                    response_parts.append(f"検出された症状: {', '.join(rec['symptoms'])}")
                                
                                if response_parts:
                                    current_chat['response_content'] = ' | '.join(response_parts)
                                
                                if 'error' in rec and rec.get('error'):
                                    current_chat['error'] = {
                                        'type': rec.get('error_type', 'unknown'),
                                        'message': rec.get('error_message', ''),
                                        'reason': rec.get('reason', '')
                                    }
                                    total_errors += 1
                                    if current_session_id:
                                        sessions[current_session_id]['errors'].append(current_chat['error'])
                        response_data_buffer = []
                
                # 処理時間の抽出
                exec_time = extract_execution_time(line)
                if exec_time:
                    if current_chat:
                        current_chat['execution_time'] = exec_time
                    if current_session_id:
                        sessions[current_session_id]['execution_times'].append(exec_time)
                        sessions[current_session_id]['total_execution_time'] += exec_time
                
                # エラー情報の抽出
                error_info = extract_error_info(line)
                if error_info and current_chat and not current_chat.get('error'):
                    current_chat['error'] = error_info
                    total_errors += 1
                    if current_session_id:
                        sessions[current_session_id]['errors'].append(error_info)
                
            except Exception as e:
                if line_num % 5000 == 0:
                    print(f"処理中: {line_num}行目...", file=__import__('sys').stderr)
                continue
    
    # 詳細レポートの出力
    print("=" * 120)
    print("ログ包括的分析レポート")
    print("=" * 120)
    
    print(f"\n【基本統計】")
    print(f"ユーザー数: {len(users)}")
    print(f"ユーザー一覧: {sorted(users)}")
    print(f"総チャット数: {total_chats}")
    print(f"総エラー数: {total_errors}")
    print(f"セッション数: {len(sessions)}")
    
    print(f"\n【エラー詳細】")
    error_types = defaultdict(int)
    for session in sessions.values():
        for error in session['errors']:
            if isinstance(error, dict):
                error_type = error.get('error_type', error.get('type', 'unknown'))
                error_types[error_type] += 1
    
    for error_type, count in sorted(error_types.items()):
        print(f"  {error_type}: {count}件")
    
    print(f"\n【処理時間統計】")
    all_exec_times = []
    for session in sessions.values():
        all_exec_times.extend(session['execution_times'])
    
    if all_exec_times:
        print(f"  平均処理時間: {sum(all_exec_times) / len(all_exec_times):.3f}秒")
        print(f"  最小処理時間: {min(all_exec_times):.3f}秒")
        print(f"  最大処理時間: {max(all_exec_times):.3f}秒")
        print(f"  総処理時間: {sum(all_exec_times):.3f}秒")
        print(f"  処理時間の中央値: {sorted(all_exec_times)[len(all_exec_times)//2]:.3f}秒")
    
    print(f"\n【全セッション詳細分析】")
    print("=" * 120)
    
    for session_id, session_data in sorted(sessions.items()):
        if not session_data['chats']:
            continue
            
        print(f"\n{'='*120}")
        print(f"セッションID: {session_id}")
        print(f"ユーザー: {session_data['user'] or '不明'}")
        print(f"チャット数: {len(session_data['chats'])}")
        print(f"エラー数: {len(session_data['errors'])}")
        if session_data['execution_times']:
            avg_time = sum(session_data['execution_times']) / len(session_data['execution_times'])
            print(f"平均処理時間: {avg_time:.3f}秒")
            print(f"総処理時間: {sum(session_data['execution_times']):.3f}秒")
        
        for i, chat in enumerate(session_data['chats'], 1):
            print(f"\n  {'-'*120}")
            print(f"  チャット {i}")
            print(f"  {'-'*120}")
            print(f"  ユーザー入力: {chat.get('user_input', 'N/A')}")
            
            if chat.get('response_content'):
                print(f"  システム返信内容: {chat['response_content']}")
            
            if chat.get('execution_time'):
                print(f"  処理時間: {chat['execution_time']:.3f}秒")
                # 応答速度の評価
                if chat['execution_time'] < 1.0:
                    speed_eval = "✅ 高速"
                elif chat['execution_time'] < 3.0:
                    speed_eval = "⚠️ 普通"
                elif chat['execution_time'] < 10.0:
                    speed_eval = "⚠️ やや遅い"
                else:
                    speed_eval = "❌ 遅い"
                print(f"  応答速度評価: {speed_eval}")
            
            if chat.get('status'):
                print(f"  ステータス: {chat['status']}")
            
            if chat.get('medicine_type'):
                print(f"  医薬品の種類: {chat['medicine_type']}")
            
            if chat.get('algorithm'):
                print(f"  使用アルゴリズム: {chat['algorithm']}")
            
            if chat.get('error'):
                print(f"  ⚠️ エラー発生:")
                error = chat['error']
                if isinstance(error, dict):
                    print(f"    エラータイプ: {error.get('type', error.get('error_type', 'unknown'))}")
                    if error.get('message'):
                        msg = error['message']
                        if len(msg) > 200:
                            msg = msg[:200] + "..."
                        print(f"    エラーメッセージ: {msg}")
                    if error.get('reason'):
                        reason = error['reason']
                        if len(reason) > 200:
                            reason = reason[:200] + "..."
                        print(f"    エラー理由: {reason}")
            
            if chat.get('recommended_medicines'):
                medicines = chat['recommended_medicines']
                print(f"  推奨医薬品数: {len(medicines)}")
                
                for j, medicine in enumerate(medicines, 1):
                    print(f"\n    ─ 推奨医薬品 {j} ─")
                    if isinstance(medicine, dict):
                        print(f"      製品名: {medicine.get('product_name', medicine.get('name', 'N/A'))}")
                        print(f"      メーカー: {medicine.get('manufacturer', 'N/A')}")
                        
                        if medicine.get('rank'):
                            print(f"      ランク: {medicine.get('rank')}")
                        
                        if medicine.get('score') is not None:
                            score = medicine.get('score')
                            print(f"      スコア: {score:.3f}")
                            
                            # 適切性の評価
                            if score >= 0.8:
                                appropriateness = "✅ 適切"
                            elif score >= 0.6:
                                appropriateness = "⚠️ やや適切"
                            elif score >= 0.4:
                                appropriateness = "⚠️ 要検討"
                            else:
                                appropriateness = "❌ 不適切"
                            
                            print(f"      適切性評価: {appropriateness}")
                        
                        if medicine.get('score_level'):
                            print(f"      スコアレベル: {medicine.get('score_level')}")
                        
                        if medicine.get('reason'):
                            reason = medicine['reason']
                            if len(reason) > 150:
                                reason = reason[:150] + "..."
                            print(f"      推奨理由: {reason}")
                        
                        if medicine.get('efficacy'):
                            efficacy = medicine['efficacy']
                            if len(efficacy) > 100:
                                efficacy = efficacy[:100] + "..."
                            print(f"      効能: {efficacy}")
                        
                        if medicine.get('ingredients'):
                            ingredients = medicine['ingredients']
                            if isinstance(ingredients, str):
                                if len(ingredients) > 100:
                                    ingredients = ingredients[:100] + "..."
                            print(f"      主成分: {ingredients}")
                        
                        if medicine.get('usage_notes'):
                            usage = medicine['usage_notes']
                            if len(usage) > 150:
                                usage = usage[:150] + "..."
                            print(f"      使用上の注意: {usage}")
            
            # 出力の適切性評価
            if chat.get('error'):
                print(f"  出力適切性評価: ❌ エラーが発生しました")
            elif chat.get('recommended_medicines'):
                medicines = chat.get('recommended_medicines', [])
                if medicines:
                    # 推奨医薬品がある場合、スコアの平均で評価
                    scores = [m.get('score', 0) for m in medicines if isinstance(m, dict) and m.get('score') is not None]
                    if scores:
                        avg_score = sum(scores) / len(scores)
                        if avg_score >= 0.8:
                            appropriateness = "✅ 適切"
                        elif avg_score >= 0.6:
                            appropriateness = "⚠️ やや適切"
                        elif avg_score >= 0.4:
                            appropriateness = "⚠️ 要検討"
                        else:
                            appropriateness = "❌ 不適切"
                        print(f"  出力適切性評価: {appropriateness} (平均スコア: {avg_score:.3f})")
                    else:
                        print(f"  出力適切性評価: ⚠️ 推奨医薬品あり（スコア情報なし）")
                else:
                    print(f"  出力適切性評価: ⚠️ 推奨医薬品なし")
            elif chat.get('status') == 'error':
                print(f"  出力適切性評価: ❌ エラー")
            else:
                print(f"  出力適切性評価: ⚠️ 情報不足")
            
            print()
    
    return {
        'users': users,
        'total_chats': total_chats,
        'total_errors': total_errors,
        'sessions': dict(sessions),
        'error_types': dict(error_types),
        'execution_times': all_exec_times
    }

if __name__ == '__main__':
    import sys
    log_file = '/Users/yuto/medicine-recommend-system/log/log1.log'
    results = analyze_log_comprehensive(log_file)

