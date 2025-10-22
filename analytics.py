"""
アクセス分析モジュール
ブラウザ・端末情報の解析とアクセス監視機能
"""

import re
import json
import time
from datetime import datetime
from typing import Dict, List, Optional
import os

def parse_user_agent(user_agent: str) -> Dict:
    """
    ユーザーエージェントから詳細情報を抽出
    
    Args:
        user_agent: ユーザーエージェント文字列
    
    Returns:
        解析されたブラウザ・OS・デバイス情報
    """
    if not user_agent:
        return {
            'browser': 'Unknown',
            'browser_version': 'Unknown',
            'os': 'Unknown',
            'os_version': 'Unknown',
            'device_type': 'Unknown',
            'is_mobile': False,
            'is_tablet': False
        }
    
    # ブラウザ検出パターン
    browser_patterns = {
        'Chrome': r'Chrome/(\d+\.\d+)',
        'Firefox': r'Firefox/(\d+\.\d+)',
        'Safari': r'Version/(\d+\.\d+).*Safari',
        'Edge': r'Edg/(\d+\.\d+)',
        'Internet Explorer': r'MSIE (\d+\.\d+)',
        'Opera': r'OPR/(\d+\.\d+)'
    }
    
    # OS検出パターン
    os_patterns = {
        'Windows': r'Windows NT (\d+\.\d+)',
        'macOS': r'Mac OS X (\d+[._]\d+)',
        'Linux': r'Linux',
        'Android': r'Android (\d+\.\d+)',
        'iOS': r'iPhone OS (\d+_\d+)'
    }
    
    # デバイス種類の判定
    is_mobile = 'Mobile' in user_agent or 'Android' in user_agent
    is_tablet = 'Tablet' in user_agent or 'iPad' in user_agent
    
    if is_mobile:
        device_type = 'Mobile'
    elif is_tablet:
        device_type = 'Tablet'
    else:
        device_type = 'Desktop'
    
    # ブラウザ検出
    browser = 'Unknown'
    browser_version = 'Unknown'
    for browser_name, pattern in browser_patterns.items():
        match = re.search(pattern, user_agent)
        if match:
            browser = browser_name
            browser_version = match.group(1)
            break
    
    # OS検出
    os_name = 'Unknown'
    os_version = 'Unknown'
    for os_type, pattern in os_patterns.items():
        match = re.search(pattern, user_agent)
        if match:
            os_name = os_type
            if os_type == 'Windows':
                version_map = {
                    '10.0': 'Windows 10',
                    '6.3': 'Windows 8.1',
                    '6.2': 'Windows 8',
                    '6.1': 'Windows 7'
                }
                os_version = version_map.get(match.group(1), f"Windows {match.group(1)}")
            elif os_type == 'macOS':
                os_version = f"macOS {match.group(1).replace('_', '.')}"
            elif os_type == 'Android':
                os_version = f"Android {match.group(1)}"
            elif os_type == 'iOS':
                os_version = f"iOS {match.group(1).replace('_', '.')}"
            else:
                os_version = match.group(1)
            break
    
    return {
        'browser': browser,
        'browser_version': browser_version,
        'os': os_name,
        'os_version': os_version,
        'device_type': device_type,
        'is_mobile': is_mobile,
        'is_tablet': is_tablet
    }

def log_access_analytics(session_id: str, user_agent: str, client_ip: str, 
                        response_time: float, user_info: Dict = None) -> None:
    """
    アクセス分析ログを記録
    
    Args:
        session_id: セッションID
        user_agent: ユーザーエージェント
        client_ip: クライアントIP
        response_time: レスポンス時間（ミリ秒）
        user_info: ユーザー情報（オプション）
    """
    # ユーザーエージェント解析
    parsed_ua = parse_user_agent(user_agent)
    
    # アクセス分析データ
    analytics_data = {
        'timestamp': datetime.now().isoformat(),
        'session_id': session_id,
        'ip_address': client_ip,
        'user_agent_raw': user_agent,
        'parsed_ua': parsed_ua,
        'response_time_ms': response_time,
        'access_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'user_info': user_info or {}
    }
    
    # ログディレクトリの作成
    log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'log')
    os.makedirs(log_dir, exist_ok=True)
    
    # ログファイルに保存
    log_file = os.path.join(log_dir, 'access_analytics.jsonl')
    with open(log_file, 'a', encoding='utf-8') as f:
        f.write(json.dumps(analytics_data, ensure_ascii=False) + '\n')

def get_browser_distribution(log_file: str = None) -> Dict:
    """
    ブラウザ分布を取得
    
    Args:
        log_file: ログファイルパス（オプション）
    
    Returns:
        ブラウザ分布の辞書
    """
    if not log_file:
        log_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'log', 'access_analytics.jsonl')
    
    if not os.path.exists(log_file):
        return {}
    
    browser_counts = {}
    
    with open(log_file, 'r', encoding='utf-8') as f:
        for line in f:
            try:
                data = json.loads(line.strip())
                browser = data.get('parsed_ua', {}).get('browser', 'Unknown')
                browser_counts[browser] = browser_counts.get(browser, 0) + 1
            except (json.JSONDecodeError, KeyError):
                continue
    
    total = sum(browser_counts.values())
    if total == 0:
        return {}
    
    return {browser: {'count': count, 'percentage': (count / total) * 100} 
            for browser, count in browser_counts.items()}

def get_os_distribution(log_file: str = None) -> Dict:
    """
    OS分布を取得
    
    Args:
        log_file: ログファイルパス（オプション）
    
    Returns:
        OS分布の辞書
    """
    if not log_file:
        log_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'log', 'access_analytics.jsonl')
    
    if not os.path.exists(log_file):
        return {}
    
    os_counts = {}
    
    with open(log_file, 'r', encoding='utf-8') as f:
        for line in f:
            try:
                data = json.loads(line.strip())
                os_name = data.get('parsed_ua', {}).get('os', 'Unknown')
                os_counts[os_name] = os_counts.get(os_name, 0) + 1
            except (json.JSONDecodeError, KeyError):
                continue
    
    total = sum(os_counts.values())
    if total == 0:
        return {}
    
    return {os_name: {'count': count, 'percentage': (count / total) * 100} 
            for os_name, count in os_counts.items()}

def get_device_distribution(log_file: str = None) -> Dict:
    """
    デバイス種類分布を取得
    
    Args:
        log_file: ログファイルパス（オプション）
    
    Returns:
        デバイス分布の辞書
    """
    if not log_file:
        log_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'log', 'access_analytics.jsonl')
    
    if not os.path.exists(log_file):
        return {}
    
    device_counts = {}
    
    with open(log_file, 'r', encoding='utf-8') as f:
        for line in f:
            try:
                data = json.loads(line.strip())
                device_type = data.get('parsed_ua', {}).get('device_type', 'Unknown')
                device_counts[device_type] = device_counts.get(device_type, 0) + 1
            except (json.JSONDecodeError, KeyError):
                continue
    
    total = sum(device_counts.values())
    if total == 0:
        return {}
    
    return {device_type: {'count': count, 'percentage': (count / total) * 100} 
            for device_type, count in device_counts.items()}

def calculate_avg_response_time(log_file: str = None) -> float:
    """
    平均レスポンス時間を計算
    
    Args:
        log_file: ログファイルパス（オプション）
    
    Returns:
        平均レスポンス時間（ミリ秒）
    """
    if not log_file:
        log_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'log', 'access_analytics.jsonl')
    
    if not os.path.exists(log_file):
        return 0.0
    
    response_times = []
    
    with open(log_file, 'r', encoding='utf-8') as f:
        for line in f:
            try:
                data = json.loads(line.strip())
                response_time = data.get('response_time_ms', 0)
                if response_time > 0:
                    response_times.append(response_time)
            except (json.JSONDecodeError, KeyError):
                continue
    
    return sum(response_times) / len(response_times) if response_times else 0.0

def get_access_statistics(log_file: str = None) -> Dict:
    """
    アクセス統計を取得
    
    Args:
        log_file: ログファイルパス（オプション）
    
    Returns:
        アクセス統計の辞書
    """
    if not log_file:
        log_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'log', 'access_analytics.jsonl')
    
    if not os.path.exists(log_file):
        return {
            'total_accesses': 0,
            'browser_distribution': {},
            'os_distribution': {},
            'device_distribution': {},
            'avg_response_time': 0.0
        }
    
    return {
        'total_accesses': sum(1 for _ in open(log_file, 'r', encoding='utf-8')),
        'browser_distribution': get_browser_distribution(log_file),
        'os_distribution': get_os_distribution(log_file),
        'device_distribution': get_device_distribution(log_file),
        'avg_response_time': calculate_avg_response_time(log_file)
    }
