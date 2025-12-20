#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ログファイル自動分析プログラム
指定されたログファイルを分析し、指定フォーマットでレポートを生成
"""

import re
import json
import ast
import sys
import os
from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path


def extract_json_from_line_robust(line_or_lines: str) -> Optional[Dict]:
    """行からJSONデータを堅牢に抽出（長いJSONに対応）"""
    # 複数行の場合は結合
    if isinstance(line_or_lines, list):
        full_line = ' '.join(line_or_lines)
    else:
        full_line = line_or_lines
    
    if 'Response Data:' not in full_line:
        return None
    
    json_start = full_line.find('Response Data:') + len('Response Data:')
    json_str = full_line[json_start:].strip()
    
    if json_str.startswith('{'):
        # 括弧のバランスを確認してJSONを抽出
        brace_count = 0
        end_pos = 0
        in_string = False
        escape_next = False
        
        for i, char in enumerate(json_str):
            if escape_next:
                escape_next = False
                continue
            
            if char == '\\':
                escape_next = True
                continue
            
            if char == '"' or char == "'":
                in_string = not in_string
                continue
            
            if not in_string:
                if char == '{':
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        end_pos = i + 1
                        break
        
        if end_pos > 0:
            try:
                json_str_python = json_str[:end_pos]
                # ast.literal_evalを使用（シングルクォート対応）
                try:
                    # nanをNoneに置換
                    json_str_python = json_str_python.replace('nan', 'None')
                    data = ast.literal_eval(json_str_python)
                    return data
                except Exception as e1:
                    # JSONとして試行（ダブルクォートに変換）
                    try:
                        # シングルクォートをダブルクォートに変換（簡易版）
                        json_str_fixed = json_str_python.replace("'", '"').replace('None', 'null')
                        return json.loads(json_str_fixed)
                    except Exception as e2:
                        # 最後の試み：ast.literal_evalで直接評価
                        try:
                            # より安全な方法：evalではなくast.literal_evalを使用
                            json_str_python = json_str[:end_pos].replace('nan', 'None')
                            data = ast.literal_eval(json_str_python)
                            return data
                        except:
                            pass
            except Exception:
                pass
    
    return None


def extract_timestamp(line: str) -> Optional[datetime]:
    """ログ行からタイムスタンプを抽出"""
    # フォーマット: 2025-12-14T00:19:03.640413474Z または 2025-12-14 00:19:03,640
    patterns = [
        r'(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})',
        r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})',
    ]
    for pattern in patterns:
        match = re.search(pattern, line)
        if match:
            try:
                ts_str = match.group(1)
                if 'T' in ts_str:
                    return datetime.fromisoformat(ts_str)
                else:
                    return datetime.strptime(ts_str, '%Y-%m-%d %H:%M:%S')
            except:
                pass
    return None


def extract_session_id(line: str) -> Optional[str]:
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


def extract_user_info(line: str) -> Optional[Dict[str, str]]:
    """ユーザー情報を抽出"""
    patterns = [
        (r'👤 New user created: (ユーザー\d+)', 'new'),
        (r'👤 Existing session accessed: (ユーザー\d+)', 'existing'),
        (r'Username: (ユーザー\d+)', 'existing'),
    ]
    for pattern, user_type in patterns:
        match = re.search(pattern, line)
        if match:
            return {'username': match.group(1), 'type': user_type}
    return None


def extract_user_input(line: str) -> Optional[str]:
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


def extract_execution_time(line: str) -> Optional[float]:
    """処理時間を抽出"""
    match = re.search(r'Execution Time: ([\d.]+)s', line)
    if match:
        return float(match.group(1))
    return None


def extract_warning(line: str) -> Optional[Dict[str, Any]]:
    """警告情報を抽出"""
    if 'WARNING' not in line:
        return None
    
    warning_info = {}
    
    # session_not_found
    if 'セッションIDがDBに存在しません' in line:
        warning_info['type'] = 'session_not_found'
        match = re.search(r'sid=(\d+)', line)
        if match:
            warning_info['session_id'] = match.group(1)
    
    # symptom_not_detected
    elif '症状が検出できませんでした' in line:
        warning_info['type'] = 'symptom_not_detected'
        match = re.search(r'症状が検出できませんでした: (.+)', line)
        if match:
            warning_info['user_input'] = match.group(1)
        warning_info['message'] = '⚠️ 症状が検出できませんでした'
    
    # not_found (robots.txtなど)
    elif '404 Not Found' in line:
        warning_info['type'] = 'not_found'
        match = re.search(r'404 Not Found: (.+)', line)
        if match:
            warning_info['url'] = match.group(1)
    
    # Rule-based algorithm error
    elif 'Rule-based algorithm error' in line or 'Rule-based' in line and 'error' in line.lower():
        warning_info['type'] = 'symptom_not_detected'
        match = re.search(r'error: (.+)', line, re.IGNORECASE)
        if match:
            warning_info['message'] = f'⚠️ Rule-based algorithm error: {match.group(1)}'
    
    return warning_info if warning_info else None


def extract_error(line: str) -> Optional[Dict[str, Any]]:
    """エラー情報を抽出"""
    if 'ERROR' in line and 'WARNING' not in line:
        error_info = {'has_error': True}
        
        if 'rule_based_error' in line:
            error_info['error_type'] = 'rule_based_error'
        elif 'no_candidates' in line:
            error_info['error_type'] = 'no_candidates'
        elif 'Exception' in line:
            error_info['error_type'] = 'exception'
        
        error_msg_match = re.search(r'error_message[:\'"]+([^\'"]+)', line)
        if error_msg_match:
            error_info['error_message'] = error_msg_match.group(1)
        
        return error_info
    return None


def extract_http_status(line: str) -> Optional[Dict[str, Any]]:
    """HTTPステータスコードを抽出"""
    # フォーマット: "GET /api/sessions HTTP/1.1" 200 175
    match = re.search(r'"([A-Z]+) ([^"]+)" (\d{3})', line)
    if match:
        method = match.group(1)
        endpoint = match.group(2).split('?')[0]  # クエリパラメータを除去
        endpoint = endpoint.replace(' HTTP/1.1', '').replace(' HTTP/1.0', '').strip()  # HTTP/1.1を除去
        status = int(match.group(3))
        return {
            'method': method,
            'endpoint': endpoint,
            'status': status
        }
    return None


def extract_api_call(line: str) -> Optional[Dict[str, Any]]:
    """API呼び出し情報を抽出"""
    # ChatGPT API
    if 'api.openai.com' in line or 'ChatGPT' in line:
        return {'type': 'ChatGPT', 'count': 1}
    
    # DeepL API
    if 'deepl.com' in line or 'DeepL' in line:
        return {'type': 'DeepL', 'count': 1}
    
    return None


def analyze_log_file(file_path: str) -> Dict[str, Any]:
    """ログファイルを包括的に分析"""
    
    sessions = defaultdict(lambda: {
        'session_id': None,
        'user': None,
        'chats': [],
        'errors': [],
        'warnings': [],
        'api_calls': 0,
        'execution_times': [],
        'first_access': None,
        'last_access': None,
        'http_requests': []
    })
    
    users = set()
    total_chats = 0
    total_errors = 0
    total_warnings = 0
    current_session_id = None
    current_user = None
    current_chat = {}
    chat_counter = 0
    response_data_buffer = []
    brace_count = 0
    
    # 統計情報
    all_timestamps = []
    http_status_codes = defaultdict(int)
    api_calls = {'ChatGPT': 0, 'DeepL': 0}
    endpoint_calls = defaultdict(int)
    
    print(f"ログファイルを読み込んでいます: {file_path}", file=sys.stderr)
    
    with open(file_path, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            try:
                # タイムスタンプ抽出
                timestamp = extract_timestamp(line)
                if timestamp:
                    all_timestamps.append(timestamp)
                
                # セッションIDの抽出
                session_id = extract_session_id(line)
                if session_id:
                    current_session_id = session_id
                    sessions[session_id]['session_id'] = session_id
                    if timestamp:
                        if not sessions[session_id]['first_access']:
                            sessions[session_id]['first_access'] = timestamp
                        sessions[session_id]['last_access'] = timestamp
                
                # ユーザー情報の抽出
                user_info = extract_user_info(line)
                if user_info:
                    current_user = user_info['username']
                    users.add(current_user)
                    if current_session_id:
                        sessions[current_session_id]['user'] = current_user
                        if timestamp:
                            if not sessions[current_session_id]['first_access']:
                                sessions[current_session_id]['first_access'] = timestamp
                            sessions[current_session_id]['last_access'] = timestamp
                
                # ユーザー入力の抽出
                user_input = extract_user_input(line)
                if user_input:
                    chat_counter += 1
                    current_chat = {
                        'chat_id': chat_counter,
                        'user_input': user_input,
                        'session_id': current_session_id,
                        'user': current_user,
                        'timestamp': timestamp,
                        'response': None,
                        'response_content': None,
                        'recommended_medicines': [],
                        'execution_time': None,
                        'error': None,
                        'warning': None,
                        'status': None,
                        'medicine_type': None,
                        'algorithm': None,
                        'symptoms': [],
                        'symptom_analysis_method': None
                    }
                    total_chats += 1
                    if current_session_id:
                        sessions[current_session_id]['chats'].append(current_chat)
                    response_data_buffer = []
                
                # Response Data行の検出（長いJSONに対応）
                if 'Response Data:' in line:
                    response_data_buffer = [line]
                    # 1行にJSONが全て含まれている場合を検出
                    json_start = line.find('Response Data:') + len('Response Data:')
                    json_str = line[json_start:].strip()
                    brace_count = json_str.count('{') - json_str.count('}')
                    
                    # 1行で完結している場合
                    if brace_count == 0 and json_str.startswith('{'):
                        json_data = extract_json_from_line_robust(line)
                        if json_data and current_chat:
                            if 'recommendation' in json_data:
                                rec = json_data['recommendation']
                                current_chat['status'] = rec.get('status', 'success')
                                current_chat['medicine_type'] = rec.get('medicine_type')
                                current_chat['algorithm'] = rec.get('algorithm', 'unknown')
                                current_chat['symptoms'] = rec.get('symptoms', [])
                                
                                # レスポンス内容の構築
                                response_parts = []
                                
                                if 'recommended_medicines' in rec and rec['recommended_medicines']:
                                    current_chat['recommended_medicines'] = rec['recommended_medicines']
                                    response_parts.append(f"推奨医薬品: {len(rec['recommended_medicines'])}件")
                                
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
                        brace_count = 0
                elif response_data_buffer:
                    response_data_buffer.append(line)
                    brace_count += line.count('{') - line.count('}')
                    
                    # JSONの終了を検出（括弧のバランスで判定）
                    if brace_count <= 0:
                        full_json_str = ' '.join(response_data_buffer)
                        json_data = extract_json_from_line_robust(full_json_str)
                        if json_data and current_chat:
                            if 'recommendation' in json_data:
                                rec = json_data['recommendation']
                                current_chat['status'] = rec.get('status', 'success')
                                current_chat['medicine_type'] = rec.get('medicine_type')
                                current_chat['algorithm'] = rec.get('algorithm', 'unknown')
                                current_chat['symptoms'] = rec.get('symptoms', [])
                                
                                # レスポンス内容の構築
                                response_parts = []
                                
                                if 'recommended_medicines' in rec and rec['recommended_medicines']:
                                    current_chat['recommended_medicines'] = rec['recommended_medicines']
                                    response_parts.append(f"推奨医薬品: {len(rec['recommended_medicines'])}件")
                                
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
                        brace_count = 0
                
                # 処理時間の抽出
                exec_time = extract_execution_time(line)
                if exec_time:
                    if current_chat:
                        current_chat['execution_time'] = exec_time
                    if current_session_id:
                        sessions[current_session_id]['execution_times'].append(exec_time)
                
                # 警告情報の抽出
                warning_info = extract_warning(line)
                if warning_info:
                    total_warnings += 1
                    if current_chat:
                        current_chat['warning'] = warning_info
                    if current_session_id:
                        sessions[current_session_id]['warnings'].append(warning_info)
                
                # エラー情報の抽出
                error_info = extract_error(line)
                if error_info and current_chat and not current_chat.get('error'):
                    current_chat['error'] = error_info
                    total_errors += 1
                    if current_session_id:
                        sessions[current_session_id]['errors'].append(error_info)
                
                # HTTPステータスコードの抽出
                http_info = extract_http_status(line)
                if http_info:
                    http_status_codes[http_info['status']] += 1
                    endpoint_calls[http_info['endpoint']] += 1
                    if current_session_id:
                        sessions[current_session_id]['http_requests'].append(http_info)
                
                # API呼び出しの抽出
                api_info = extract_api_call(line)
                if api_info:
                    api_calls[api_info['type']] += api_info['count']
                    if current_session_id:
                        sessions[current_session_id]['api_calls'] += api_info['count']
                
                # 症状分析方式の検出
                if 'ChatGPT' in line and ('症状分析' in line or 'Analyzing' in line):
                    if current_chat:
                        current_chat['symptom_analysis_method'] = 'ChatGPT'
                
                # POST処理完了の検出（返信内容の補完）
                if 'POST処理完了' in line:
                    if current_chat and not current_chat.get('response_content'):
                        if '症状検出失敗' in line:
                            current_chat['response_content'] = '症状が検出できませんでした'
                        elif 'JSON返却' in line:
                            # メッセージ数を抽出
                            msg_match = re.search(r'(\d+) messages', line)
                            if msg_match:
                                msg_count = int(msg_match.group(1))
                                if msg_count > 0:
                                    current_chat['response_content'] = f'レスポンス生成完了（{msg_count}メッセージ）'
                
                # 個別アドバイス生成完了の検出
                if '個別アドバイス生成完了' in line:
                    if current_chat:
                        char_match = re.search(r'(\d+)字', line)
                        if char_match:
                            char_count = char_match.group(1)
                            if current_chat.get('response_content'):
                                current_chat['response_content'] += f' | 個別アドバイス: {char_count}字'
                            else:
                                current_chat['response_content'] = f'個別アドバイス: {char_count}字'
                
            except Exception as e:
                if line_num % 5000 == 0:
                    print(f"処理中: {line_num}行目...", file=sys.stderr)
                continue
    
    # アクティブセッション（チャットあり）と非アクティブセッション（チャットなし）を分類
    active_sessions = [s for s in sessions.values() if s['chats']]
    inactive_sessions = [s for s in sessions.values() if not s['chats']]
    
    return {
        'sessions': dict(sessions),
        'users': users,
        'total_chats': total_chats,
        'total_errors': total_errors,
        'total_warnings': total_warnings,
        'active_sessions': active_sessions,
        'inactive_sessions': inactive_sessions,
        'all_timestamps': all_timestamps,
        'http_status_codes': dict(http_status_codes),
        'api_calls': api_calls,
        'endpoint_calls': dict(endpoint_calls),
        'total_lines': line_num
    }


def format_duration(seconds: float) -> str:
    """秒数を時間・分・秒の形式に変換"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    if hours > 0:
        return f"{hours}時間{minutes}分{secs}秒"
    elif minutes > 0:
        return f"{minutes}分{secs}秒"
    else:
        return f"{secs}秒"


def generate_report(analysis_result: Dict[str, Any], log_file_path: str) -> str:
    """指定フォーマットでレポートを生成"""
    
    log_filename = Path(log_file_path).name
    sessions = analysis_result['sessions']
    users = analysis_result['users']
    total_chats = analysis_result['total_chats']
    total_errors = analysis_result['total_errors']
    total_warnings = analysis_result['total_warnings']
    active_sessions = analysis_result['active_sessions']
    inactive_sessions = analysis_result['inactive_sessions']
    all_timestamps = analysis_result['all_timestamps']
    http_status_codes = analysis_result['http_status_codes']
    api_calls = analysis_result['api_calls']
    endpoint_calls = analysis_result['endpoint_calls']
    total_lines = analysis_result['total_lines']
    
    # 分析日時
    analysis_date = datetime.now()
    
    # 期間の計算
    if all_timestamps:
        start_time = min(all_timestamps)
        end_time = max(all_timestamps)
        duration = (end_time - start_time).total_seconds()
    else:
        start_time = None
        end_time = None
        duration = 0
    
    # 処理時間統計
    all_exec_times = []
    for session in sessions.values():
        all_exec_times.extend(session['execution_times'])
    
    # 警告タイプ別集計
    warning_types = defaultdict(int)
    warning_details = defaultdict(list)
    for session in sessions.values():
        for warning in session['warnings']:
            if isinstance(warning, dict):
                wtype = warning.get('type', 'unknown')
                warning_types[wtype] += 1
                warning_details[wtype].append(warning)
    
    # レポート生成
    report = []
    report.append(f"# {log_filename} 詳細分析レポート\n")
    report.append("## 分析日時\n")
    report.append(f"{analysis_date.year}年{analysis_date.month}月{analysis_date.day}日\n")
    report.append("## 基本統計\n")
    report.append("### ログ概要\n")
    report.append(f"- **総ログ行数**: {total_lines:,}行\n")
    
    if start_time and end_time:
        report.append(f"- **分析対象期間**: {start_time.year} {start_time.month:02d}-{start_time.day:02d} {start_time.hour:02d}:{start_time.minute:02d}:{start_time.second:02d} ～ {end_time.year} {end_time.month:02d}-{end_time.day:02d} {end_time.hour:02d}:{end_time.minute:02d}:{end_time.second:02d}\n")
        hours = int(duration // 3600)
        minutes = int((duration % 3600) // 60)
        report.append(f"- **総時間**: 約{hours}時間{minutes}分\n")
    else:
        report.append("- **分析対象期間**: データなし\n")
        report.append("- **総時間**: データなし\n")
    
    report.append("### ユーザー統計\n")
    report.append(f"- **ユーザー数**: {len(users)}名\n")
    report.append("- **ユーザー一覧**: \n")
    for user in sorted(users):
        report.append(f"  - {user}\n")
    
    report.append("### セッション統計\n")
    report.append(f"- **総セッション数**: {len(sessions)}セッション\n")
    report.append(f"- **アクティブセッション数（チャットあり）**: {len(active_sessions)}セッション\n")
    report.append(f"- **非アクティブセッション数**: {len(inactive_sessions)}セッション（セッション管理のみ）\n")
    
    report.append("### チャット統計\n")
    report.append(f"- **総チャット数**: {total_chats}件\n")
    if len(active_sessions) > 0:
        avg_chats = total_chats / len(active_sessions)
        report.append(f"- **平均チャット数/セッション**: {avg_chats:.1f}件（アクティブセッションのみ）\n")
    else:
        report.append("- **平均チャット数/セッション**: 0件\n")
    
    # 処理時間分析
    report.append("## 処理時間分析\n")
    report.append("### 処理時間統計\n")
    if all_exec_times:
        avg_time = sum(all_exec_times) / len(all_exec_times)
        min_time = min(all_exec_times)
        max_time = max(all_exec_times)
        total_time = sum(all_exec_times)
        median_time = sorted(all_exec_times)[len(all_exec_times)//2]
        
        report.append(f"- **総処理回数**: {len(all_exec_times)}回\n")
        report.append(f"- **平均処理時間**: {avg_time:.2f}秒\n")
        report.append(f"- **最小処理時間**: {min_time:.2f}秒\n")
        report.append(f"- **最大処理時間**: {max_time:.2f}秒\n")
        report.append(f"- **総処理時間**: {total_time:.2f}秒\n")
        report.append(f"- **中央値**: {median_time:.2f}秒\n")
        
        report.append("### 処理時間の分布\n")
        report.append(f"処理時間には大きなばらつきがあり、最短{min_time:.2f}秒から最長{max_time:.2f}秒まで幅広い分布を示しています。これは、症状の複雑さや推奨アルゴリズムの選択（rule_based vs AI-based）によるものと考えられます。\n")
    else:
        report.append("- **総処理回数**: 0回\n")
        report.append("- **平均処理時間**: データなし\n")
    
    # エラー・警告分析
    report.append("## エラー・警告分析\n")
    report.append("### エラー統計\n")
    report.append(f"- **総エラー数**: {total_errors}件\n")
    if total_errors == 0:
        report.append("- **エラーレベル**: なし\n")
    else:
        # エラータイプ別集計
        error_types = defaultdict(int)
        for session in sessions.values():
            for error in session['errors']:
                if isinstance(error, dict):
                    etype = error.get('error_type', error.get('type', 'unknown'))
                    error_types[etype] += 1
        if error_types:
            report.append("- **エラーレベル**: あり\n")
            for etype, count in sorted(error_types.items()):
                report.append(f"  - **{etype}**: {count}件\n")
        else:
            report.append("- **エラーレベル**: あり（詳細不明）\n")
    
    report.append("### 警告統計\n")
    report.append(f"- **総警告数**: {total_warnings}件\n")
    if warning_types:
        report.append("- **警告タイプ別**:\n")
        for wtype, count in sorted(warning_types.items()):
            report.append(f"  - **{wtype}**: {count}件\n")
            if wtype == 'session_not_found':
                report.append("    - セッションIDがDBに存在しない場合の警告\n")
                report.append("    - セッション復旧処理が実行された\n")
            elif wtype == 'not_found':
                report.append("    - robots.txtへの404エラー（システム的な問題ではない）\n")
            elif wtype == 'symptom_not_detected':
                report.append("    - ユーザーメッセージから症状が検出できなかった\n")
    
    # 警告の詳細
    if warning_details:
        report.append("### 警告の詳細\n")
        detail_num = 1
        for wtype, warnings in warning_details.items():
            if wtype == 'session_not_found':
                report.append(f"{detail_num}. **セッションIDがDBに存在しない警告（{len(warnings)}件）**\n")
                report.append("   - セッション管理の一時的な不整合が発生\n")
                report.append("   - システムは自動的にセッション復旧を試みた\n")
                report.append("   - ユーザー体験への影響は最小限\n")
                detail_num += 1
            elif wtype == 'symptom_not_detected':
                report.append(f"{detail_num}. **症状検出失敗（{len(warnings)}件）**\n")
                for i, warning in enumerate(warnings, 1):  # 全て表示
                    user_input = warning.get('user_input', '不明')
                    message = warning.get('message', '症状が検出できませんでした')
                    report.append(f"   - ユーザー入力(ユーザー{i}): 「{user_input}」\n")
                    report.append(f"   - メッセージ: 「{message}」\n")
                detail_num += 1
    
    # API呼び出し統計
    report.append("## API呼び出し統計\n")
    report.append("### API呼び出し総数\n")
    report.append(f"- **Chat_GPT_API呼び出し数**: {api_calls.get('ChatGPT', 0)}回\n")
    report.append(f"- **DeepL_API呼び出し数**: {api_calls.get('DeepL', 0)}回\n")
    
    report.append("### エンドポイント別呼び出し数\n")
    total_endpoint_calls = sum(endpoint_calls.values())
    endpoint_num = 1
    for endpoint, count in sorted(endpoint_calls.items(), key=lambda x: x[1], reverse=True):
        percentage = (count / total_endpoint_calls * 100) if total_endpoint_calls > 0 else 0
        report.append(f"{endpoint_num}. **{endpoint}**: {count}回（{percentage:.1f}%）\n")
        
        if endpoint == '/api/sessions':
            report.append("   - セッション情報の取得・更新\n")
            report.append("   - 定期的なポーリングによる呼び出しが多い\n")
        elif endpoint == '/api/main_sessions':
            report.append("   - 管理画面でのセッション一覧取得\n")
        elif endpoint == '/api/main_manual_reply_queue':
            report.append("   - 管理画面での手動返信キュー取得\n")
        elif endpoint == '/api/main_ai_control':
            report.append("   - AI制御設定の取得\n")
        elif endpoint == '/api/set_language':
            report.append("   - 言語設定の変更\n")
        elif endpoint == '/api/get_feedback_reports':
            report.append("   - フィードバックレポートの取得\n")
        
        endpoint_num += 1
    
    report.append("### API呼び出しの特徴\n")
    if endpoint_calls:
        top_endpoint = max(endpoint_calls.items(), key=lambda x: x[1])
        report.append(f"- `{top_endpoint[0]}`への呼び出しが圧倒的に多く、定期的なポーリングが行われている\n")
        report.append("- 管理画面関連のAPI呼び出しも一定数存在\n")
    
    # HTTPステータスコード統計
    report.append("## HTTPステータスコード統計\n")
    report.append("### ステータスコード別\n")
    total_http = sum(http_status_codes.values())
    for status in sorted(http_status_codes.keys()):
        count = http_status_codes[status]
        percentage = (count / total_http * 100) if total_http > 0 else 0
        status_name = {
            200: 'OK',
            204: 'No Content',
            304: 'Not Modified',
            401: 'Unauthorized',
            404: 'Not Found',
        }.get(status, 'Unknown')
        report.append(f"- **{status} {status_name}**: {count}回（{percentage:.2f}%）\n")
    
    report.append("### 分析\n")
    if total_http > 0:
        success_count = http_status_codes.get(200, 0) + http_status_codes.get(204, 0) + http_status_codes.get(304, 0)
        success_rate = (success_count / total_http * 100)
        report.append(f"- 正常なレスポンス（200, 204, 304）が{success_rate:.1f}%を占めており、システムは正常に動作している\n")
        
        if http_status_codes.get(401, 0) > 0:
            report.append("- 401エラーは認証が必要な管理画面へのアクセス試行\n")
        
        if http_status_codes.get(404, 0) > 0:
            report.append("- 404エラーはrobots.txtへのアクセス\n")
    
    # セッション別詳細分析
    report.append("## セッション別詳細分析\n")
    
    session_num = 1
    for session_id, session_data in sorted(sessions.items()):
        if not session_data['chats']:
            continue
        
        report.append(f"### セッション{session_num}: {session_id}\n")
        report.append("#### 基本情報\n")
        report.append(f"- **ユーザー**: {session_data['user'] or '不明'}\n")
        report.append(f"- **チャット数**: {len(session_data['chats'])}件\n")
        report.append(f"- **エラー数**: {len(session_data['errors'])}件\n")
        report.append(f"- **警告数**: {len(session_data['warnings'])}件\n")
        report.append(f"- **API呼び出し数**: {session_data['api_calls']}回\n")
        
        if session_data['first_access']:
            first = session_data['first_access']
            report.append(f"- **初回アクセス**: {first.year} {first.month:02d}-{first.day:02d} {first.hour:02d}:{first.minute:02d}:{first.second:02d}\n")
        else:
            report.append("- **初回アクセス**: データなし\n")
        
        if session_data['last_access']:
            last = session_data['last_access']
            report.append(f"- **最終アクセス**: {last.year} {last.month:02d}-{last.day:02d} {last.hour:02d}:{last.minute:02d}:{last.second:02d}\n")
        else:
            report.append("- **最終アクセス**: データなし\n")
        
        if session_data['first_access'] and session_data['last_access']:
            duration_sec = (session_data['last_access'] - session_data['first_access']).total_seconds()
            duration_str = format_duration(duration_sec)
            report.append(f"- **セッション継続時間**: 約{duration_str}\n")
        else:
            report.append("- **セッション継続時間**: データなし\n")
        
        if session_data['execution_times']:
            avg_time = sum(session_data['execution_times']) / len(session_data['execution_times'])
            report.append(f"- **平均処理時間**: {avg_time:.2f}秒\n")
        else:
            report.append("- **平均処理時間**: データなし\n")
        
        report.append("#### チャット詳細\n")
        
        for chat_num, chat in enumerate(session_data['chats'], 1):
            report.append(f"**チャット{chat_num}: 「ユーザー入力:{chat.get('user_input', 'N/A')}」**\n")
            
            if chat.get('timestamp'):
                ts = chat['timestamp']
                report.append(f"- **タイムスタンプ**: {ts.year} {ts.month:02d}-{ts.day:02d} {ts.hour:02d}:{ts.minute:02d}:{ts.second:02d}\n")
            
            if chat.get('execution_time'):
                report.append(f"- **処理時間**: {chat['execution_time']:.2f}秒\n")
            
            # 返信内容の構築（必ず表示）
            response_parts = []
            if chat.get('response_content'):
                response_parts.append(chat['response_content'])
            elif chat.get('recommended_medicines'):
                response_parts.append(f"推奨医薬品: {len(chat['recommended_medicines'])}件")
            elif chat.get('symptoms'):
                response_parts.append(f"検出された症状: {', '.join(chat['symptoms'])}")
            
            # エラーや警告の情報を追加
            if chat.get('error'):
                error = chat['error']
                if isinstance(error, dict):
                    error_msg = error.get('message', error.get('error_message', ''))
                    if error_msg:
                        response_parts.append(f"エラー: {error_msg}")
                    else:
                        error_type = error.get('error_type', error.get('type', 'エラー'))
                        response_parts.append(f"エラー: {error_type}")
            
            if chat.get('warning'):
                warning = chat['warning']
                if isinstance(warning, dict):
                    warning_msg = warning.get('message', '')
                    if warning_msg:
                        response_parts.append(warning_msg)
                    elif warning.get('type') == 'symptom_not_detected':
                        user_input = warning.get('user_input', chat.get('user_input', ''))
                        response_parts.append(f"⚠️ 症状が検出できませんでした: {user_input}")
            
            if response_parts:
                report.append(f"**返信内容: 「{' | '.join(response_parts)}」**\n")
            else:
                # データがない場合でも、処理時間があれば処理は実行されたと判断
                if chat.get('execution_time'):
                    report.append("**返信内容: 「処理は実行されましたが、詳細情報が取得できませんでした」**\n")
                else:
                    report.append("**返信内容: 「データなし（処理が完了していない可能性があります）」**\n")
            
            # 症状分析結果
            if chat.get('error') or (chat.get('warning') and chat.get('warning', {}).get('type') == 'symptom_not_detected'):
                report.append("- **症状分析結果**: 失敗\n")
            elif chat.get('status') == 'success' or chat.get('recommended_medicines') or chat.get('symptoms'):
                report.append("- **症状分析結果**: 成功\n")
            elif chat.get('warning'):
                report.append("- **症状分析結果**: 警告あり\n")
            else:
                report.append("- **症状分析結果**: 不明\n")
            
            if chat.get('symptom_analysis_method'):
                report.append(f"- **症状分析方式**: {chat['symptom_analysis_method']}\n")
            elif 'ChatGPT' in str(chat.get('response_content', '')):
                report.append("- **症状分析方式**: ChatGPT\n")
            
            if chat.get('symptoms'):
                report.append(f"- **抽出症状分析**: {', '.join(chat['symptoms'])}\n")
            
            if chat.get('medicine_type'):
                report.append(f"- **推奨医薬品種類**: {chat['medicine_type']}\n")
            
            if chat.get('recommended_medicines'):
                medicines = chat['recommended_medicines']
                report.append(f"- **推奨医薬品**: {len(medicines)}件\n")
                for i, med in enumerate(medicines, 1):  # 全て表示
                    if isinstance(med, dict):
                        name = med.get('product_name', med.get('name', 'N/A'))
                        mfr = med.get('manufacturer', 'N/A')
                        report.append(f"  {i}. {name}（{mfr}）\n")
            
            if chat.get('algorithm'):
                report.append(f"- **アルゴリズム**: {chat['algorithm']}\n")
            
            # 推奨医薬品分析
            if chat.get('recommended_medicines') and chat.get('symptoms'):
                report.append("- **推奨医薬品分析**\n")
                symptoms_str = ', '.join(chat['symptoms'])
                report.append(f"- **{symptoms_str}に対する推奨**（{len(chat['recommended_medicines'])}件）\n")
                
                if chat.get('algorithm'):
                    report.append(f"- **推奨アルゴリズム**: {chat['algorithm']}\n")
                
                if chat.get('execution_time'):
                    report.append(f"- **処理時間**: {chat['execution_time']:.2f}秒\n")
                
                if chat.get('timestamp'):
                    ts = chat['timestamp']
                    report.append(f"- **推奨時刻**: {ts.year} {ts.month:02d}-{ts.day:02d} {ts.hour:02d}:{ts.minute:02d}:{ts.second:02d}\n")
                
                for i, medicine in enumerate(chat['recommended_medicines'], 1):  # 全て表示
                    if isinstance(medicine, dict):
                        name = medicine.get('product_name', medicine.get('name', 'N/A'))
                        mfr = medicine.get('manufacturer', 'N/A')
                        report.append(f"{i}. **{name}**（{mfr}）\n")
                        report.append(f"   - ランク: {i}位\n")
                        
                        classification = medicine.get('classification', 'N/A')
                        report.append(f"   - 分類:{classification}\n")
                        
                        efficacy = medicine.get('efficacy', 'N/A')
                        # 効能は全て表示（制限なし）
                        report.append(f"   - 効能: {efficacy}\n")
                        
                        age_restriction = medicine.get('age_restriction')
                        if age_restriction and str(age_restriction) != 'nan':
                            report.append(f"   - 年齢制限: {age_restriction}歳以上\n")
                        else:
                            report.append("   - 年齢制限: なし\n")
                        
                        score = medicine.get('score')
                        if score is not None:
                            report.append(f"   - スコア: {score:.2f}\n")
            
            report.append("\n")
        
        session_num += 1
    
    return ''.join(report)


def main():
    """メイン処理"""
    if len(sys.argv) < 2:
        print("使用方法: python auto_log_analyzer.py <ログファイルパス>", file=sys.stderr)
        sys.exit(1)
    
    log_file_path = sys.argv[1]
    
    if not os.path.exists(log_file_path):
        print(f"エラー: ログファイルが見つかりません: {log_file_path}", file=sys.stderr)
        sys.exit(1)
    
    print("ログ分析を開始します...", file=sys.stderr)
    analysis_result = analyze_log_file(log_file_path)
    
    print("レポートを生成しています...", file=sys.stderr)
    report = generate_report(analysis_result, log_file_path)
    
    # レポートを標準出力に出力
    print(report)


if __name__ == '__main__':
    main()

