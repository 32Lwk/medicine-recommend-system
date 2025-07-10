import uuid
from datetime import datetime, date

network_logs = []
MAX_LOGS = 200

# パフォーマンス統計
performance_stats = {
    'total_requests': 0,
    'successful_requests': 0,
    'failed_requests': 0,
    'average_response_time': 0,
    'total_tokens_used': 0,
    'api_calls_today': 0,
    'last_reset_date': date.today().isoformat()
}

def add_network_log(request_type, endpoint, request_data, response_data, response_time, status, error=None):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    
    # トークン使用量を安全に取得
    tokens_used = 0
    if response_data:
        if hasattr(response_data, 'usage') and hasattr(response_data.usage, 'total_tokens'):
            tokens_used = response_data.usage.total_tokens
        elif isinstance(response_data, dict):
            tokens_used = response_data.get('usage', {}).get('total_tokens', 0)
    
    log_entry = {
        'id': str(uuid.uuid4())[:8],
        'timestamp': timestamp,
        'request_type': request_type,
        'endpoint': endpoint,
        'request_data': request_data,
        'response_data': response_data,
        'response_time': response_time,
        'status': status,
        'error': error,
        'tokens_used': tokens_used
    }
    network_logs.append(log_entry)
    
    # 日付チェックとリセット
    current_date = date.today().isoformat()
    if performance_stats['last_reset_date'] != current_date:
        performance_stats['api_calls_today'] = 0
        performance_stats['last_reset_date'] = current_date
    
    # パフォーマンス統計を更新
    performance_stats['total_requests'] += 1
    if status == 'success':
        performance_stats['successful_requests'] += 1
        # API呼び出しの場合のみ本日カウントを増加
        if 'api' in endpoint.lower() or 'openai' in endpoint.lower():
            performance_stats['api_calls_today'] += 1
    else:
        performance_stats['failed_requests'] += 1
    
    if response_time:
        # 平均レスポンス時間を更新
        current_avg = performance_stats['average_response_time']
        total_requests = performance_stats['total_requests']
        performance_stats['average_response_time'] = (current_avg * (total_requests - 1) + response_time) / total_requests
    
    if log_entry['tokens_used']:
        performance_stats['total_tokens_used'] += log_entry['tokens_used']
    
    # ログをMAX_LOGS件まで保持
    if len(network_logs) > MAX_LOGS:
        network_logs.pop(0)

def reset_performance_stats():
    """パフォーマンス統計をリセット"""
    global performance_stats
    performance_stats = {
        'total_requests': 0,
        'successful_requests': 0,
        'failed_requests': 0,
        'average_response_time': 0,
        'total_tokens_used': 0,
        'api_calls_today': 0,
        'last_reset_date': date.today().isoformat()
    } 