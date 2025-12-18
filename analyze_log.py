#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ログファイル分析スクリプト
log1.logを分析して、ユーザー数、チャット数、エラー、各セッションの詳細、推奨医薬品、処理時間などを抽出
"""

import re
import json
from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Any

def parse_log_line(line: str) -> Dict[str, Any]:
    """ログ行を解析"""
    # タイムスタンプとログレベルの抽出
    timestamp_match = re.search(r'(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d+Z)', line)
    level_match = re.search(r' - (INFO|WARNING|ERROR) - ', line)
    
    result = {
        'timestamp': timestamp_match.group(1) if timestamp_match else None,
        'level': level_match.group(1) if level_match else None,
        'raw': line
    }
    
    # ログメッセージの抽出
    if ' - ' in line:
        parts = line.split(' - ', 2)
        if len(parts) >= 3:
            result['message'] = parts[2].strip()
    
    return result

def extract_session_id(line: str) -> str:
    """セッションIDを抽出"""
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

def extract_user_info(line: str) -> Dict[str, str]:
    """ユーザー情報を抽出"""
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

def extract_user_input(line: str) -> str:
    """ユーザー入力を抽出"""
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

def extract_execution_time(line: str) -> float:
    """処理時間を抽出（秒）"""
    match = re.search(r'Execution Time: ([\d.]+)s', line)
    if match:
        return float(match.group(1))
    return None

def extract_recommendation_data(line: str) -> Dict[str, Any]:
    """推奨医薬品データを抽出"""
    if 'Response Data:' in line or 'recommendation' in line.lower():
        # JSONデータを抽出
        json_match = re.search(r'Response Data: ({.+})', line)
        if json_match:
            try:
                data = json.loads(json_match.group(1))
                return data
            except:
                pass
        
        # 推奨医薬品の情報を抽出
        medicine_match = re.search(r'recommended_medicines.*?(\[.*?\])', line, re.DOTALL)
        if medicine_match:
            try:
                medicines = json.loads(medicine_match.group(1))
                return {'recommended_medicines': medicines}
            except:
                pass
    
    return None

def extract_error_info(line: str) -> Dict[str, Any]:
    """エラー情報を抽出"""
    error_info = {}
    
    if 'ERROR' in line or 'error' in line.lower():
        error_info['has_error'] = True
        
        # エラータイプ
        if 'rule_based_error' in line:
            error_info['error_type'] = 'rule_based_error'
        elif 'no_candidates' in line:
            error_info['error_type'] = 'no_candidates'
        elif 'Exception' in line:
            error_info['error_type'] = 'exception'
        
        # エラーメッセージ
        error_msg_match = re.search(r'error_message[:\'"]+([^\'"]+)', line)
        if error_msg_match:
            error_info['error_message'] = error_msg_match.group(1)
    
    return error_info if error_info else None

def analyze_log_file(file_path: str):
    """ログファイルを分析"""
    
    # データ構造
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
                    current_chat = {
                        'user_input': user_input,
                        'session_id': current_session_id,
                        'user': current_user,
                        'timestamp': None,
                        'response': None,
                        'recommended_medicines': [],
                        'execution_time': None,
                        'error': None,
                        'status': None
                    }
                    total_chats += 1
                    if current_session_id:
                        sessions[current_session_id]['chats'].append(current_chat)
                
                # 処理時間の抽出
                exec_time = extract_execution_time(line)
                if exec_time:
                    if current_chat:
                        current_chat['execution_time'] = exec_time
                    if current_session_id:
                        sessions[current_session_id]['execution_times'].append(exec_time)
                        sessions[current_session_id]['total_execution_time'] += exec_time
                
                # 推奨医薬品データの抽出
                rec_data = extract_recommendation_data(line)
                if rec_data and current_chat:
                    if 'recommendation' in rec_data:
                        rec = rec_data['recommendation']
                        current_chat['status'] = rec.get('status', 'unknown')
                        if 'recommended_medicines' in rec:
                            current_chat['recommended_medicines'] = rec['recommended_medicines']
                        if 'error' in rec and rec.get('error'):
                            current_chat['error'] = {
                                'type': rec.get('error_type', 'unknown'),
                                'message': rec.get('error_message', '')
                            }
                            total_errors += 1
                            if current_session_id:
                                sessions[current_session_id]['errors'].append(current_chat['error'])
                
                # エラー情報の抽出
                error_info = extract_error_info(line)
                if error_info and current_chat:
                    current_chat['error'] = error_info
                    total_errors += 1
                    if current_session_id:
                        sessions[current_session_id]['errors'].append(error_info)
                
                # POST処理完了の検出
                if 'POST処理完了' in line:
                    if current_chat and current_session_id:
                        # チャット完了
                        pass
                
            except Exception as e:
                print(f"Error processing line {line_num}: {e}")
                continue
    
    # 結果の出力
    print("=" * 80)
    print("ログ分析結果")
    print("=" * 80)
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
    
    for error_type, count in error_types.items():
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
    
    print(f"\n【セッション別詳細】")
    for session_id, session_data in sorted(sessions.items()):
        if session_data['chats']:  # チャットがあるセッションのみ
            print(f"\n--- セッションID: {session_id} ---")
            print(f"ユーザー: {session_data['user']}")
            print(f"チャット数: {len(session_data['chats'])}")
            print(f"エラー数: {len(session_data['errors'])}")
            if session_data['execution_times']:
                avg_time = sum(session_data['execution_times']) / len(session_data['execution_times'])
                print(f"平均処理時間: {avg_time:.3f}秒")
            
            for i, chat in enumerate(session_data['chats'], 1):
                print(f"\n  チャット {i}:")
                print(f"    ユーザー入力: {chat.get('user_input', 'N/A')}")
                if chat.get('execution_time'):
                    print(f"    処理時間: {chat['execution_time']:.3f}秒")
                if chat.get('status'):
                    print(f"    ステータス: {chat['status']}")
                if chat.get('error'):
                    print(f"    エラー: {chat['error']}")
                if chat.get('recommended_medicines'):
                    print(f"    推奨医薬品数: {len(chat['recommended_medicines'])}")
                    for j, medicine in enumerate(chat['recommended_medicines'][:3], 1):  # 最初の3つだけ表示
                        if isinstance(medicine, dict):
                            name = medicine.get('product_name', medicine.get('name', 'N/A'))
                            print(f"      {j}. {name}")
    
    return {
        'users': users,
        'total_chats': total_chats,
        'total_errors': total_errors,
        'sessions': dict(sessions),
        'error_types': dict(error_types),
        'execution_times': all_exec_times
    }

if __name__ == '__main__':
    log_file = '/Users/yuto/medicine-recommend-system/log/log1.log'
    results = analyze_log_file(log_file)
    
    # JSON形式で保存（オプション）
    # with open('log_analysis_results.json', 'w', encoding='utf-8') as f:
    #     json.dump(results, f, ensure_ascii=False, indent=2, default=str)

