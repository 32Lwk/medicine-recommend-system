"""
パフォーマンス監視モジュール
システムのパフォーマンス指標を監視・記録
"""

import time
import json
import os
from datetime import datetime
from typing import Dict, List, Optional
import threading

from src import PROJECT_ROOT

# psutilのインポート（利用できない場合はフォールバック）
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    print("Warning: psutil not available, system metrics will be limited")

class PerformanceMonitor:
    """パフォーマンス監視クラス"""
    
    def __init__(self):
        self.start_time = None
        self.api_call_count = 0
        self.cache_hits = 0
        self.cache_misses = 0
        self.error_count = 0
        self.request_count = 0
        self.lock = threading.Lock()
        
    def start_monitoring(self):
        """監視開始"""
        self.start_time = time.time()
        
    def get_metrics(self) -> Dict:
        """現在のメトリクスを取得"""
        with self.lock:
            current_time = time.time()
            response_time = (current_time - self.start_time) * 1000 if self.start_time else 0
            
            # システムリソース情報
            if PSUTIL_AVAILABLE:
                memory_info = psutil.virtual_memory()
                cpu_percent = psutil.cpu_percent(interval=1)
            else:
                # psutilが利用できない場合のフォールバック
                memory_info = type('obj', (object,), {'used': 0, 'percent': 0})()
                cpu_percent = 0
            
            # キャッシュヒット率の計算
            total_cache_attempts = self.cache_hits + self.cache_misses
            cache_hit_rate = (self.cache_hits / total_cache_attempts) if total_cache_attempts > 0 else 0
            
            # エラー率の計算
            error_rate = (self.error_count / self.request_count) if self.request_count > 0 else 0
            
            return {
                'response_time_ms': response_time,
                'memory_usage_mb': memory_info.used / 1024 / 1024,
                'memory_usage_percent': memory_info.percent,
                'cpu_usage_percent': cpu_percent,
                'api_calls': self.api_call_count,
                'cache_hit_rate': cache_hit_rate,
                'cache_hits': self.cache_hits,
                'cache_misses': self.cache_misses,
                'error_count': self.error_count,
                'request_count': self.request_count,
                'error_rate': error_rate,
                'timestamp': datetime.now().isoformat()
            }
    
    def increment_api_calls(self):
        """API呼び出し回数を増加"""
        with self.lock:
            self.api_call_count += 1
    
    def increment_cache_hit(self):
        """キャッシュヒット回数を増加"""
        with self.lock:
            self.cache_hits += 1
    
    def increment_cache_miss(self):
        """キャッシュミス回数を増加"""
        with self.lock:
            self.cache_misses += 1
    
    def increment_error(self):
        """エラー回数を増加"""
        with self.lock:
            self.error_count += 1
    
    def increment_request(self):
        """リクエスト回数を増加"""
        with self.lock:
            self.request_count += 1
    
    def reset_metrics(self):
        """メトリクスをリセット"""
        with self.lock:
            self.start_time = time.time()
            self.api_call_count = 0
            self.cache_hits = 0
            self.cache_misses = 0
            self.error_count = 0
            self.request_count = 0

def log_performance_metrics(monitor: PerformanceMonitor, session_id: str, 
                           operation: str, additional_data: Dict = None) -> None:
    """
    パフォーマンスメトリクスをログに記録
    
    Args:
        monitor: パフォーマンス監視インスタンス
        session_id: セッションID
        operation: 操作名
        additional_data: 追加データ
    """
    metrics = monitor.get_metrics()
    
    # ログデータ
    log_data = {
        'timestamp': datetime.now().isoformat(),
        'session_id': session_id,
        'operation': operation,
        'metrics': metrics,
        'additional_data': additional_data or {}
    }
    
    # ログディレクトリの作成
    log_dir = os.path.join(PROJECT_ROOT, 'log')
    os.makedirs(log_dir, exist_ok=True)
    
    # ログファイルに保存
    log_file = os.path.join(log_dir, 'performance_metrics.jsonl')
    with open(log_file, 'a', encoding='utf-8') as f:
        f.write(json.dumps(log_data, ensure_ascii=False) + '\n')

def get_performance_statistics(log_file: str = None) -> Dict:
    """
    パフォーマンス統計を取得
    
    Args:
        log_file: ログファイルパス（オプション）
    
    Returns:
        パフォーマンス統計の辞書
    """
    if not log_file:
        log_file = os.path.join(PROJECT_ROOT, 'log', 'performance_metrics.jsonl')
    
    if not os.path.exists(log_file):
        return {
            'total_requests': 0,
            'avg_response_time': 0.0,
            'avg_memory_usage': 0.0,
            'avg_cpu_usage': 0.0,
            'avg_cache_hit_rate': 0.0,
            'error_rate': 0.0
        }
    
    response_times = []
    memory_usages = []
    cpu_usages = []
    cache_hit_rates = []
    error_rates = []
    total_requests = 0
    
    with open(log_file, 'r', encoding='utf-8') as f:
        for line in f:
            try:
                data = json.loads(line.strip())
                metrics = data.get('metrics', {})
                
                if metrics.get('response_time_ms', 0) > 0:
                    response_times.append(metrics['response_time_ms'])
                if metrics.get('memory_usage_percent', 0) > 0:
                    memory_usages.append(metrics['memory_usage_percent'])
                if metrics.get('cpu_usage_percent', 0) > 0:
                    cpu_usages.append(metrics['cpu_usage_percent'])
                if metrics.get('cache_hit_rate', 0) > 0:
                    cache_hit_rates.append(metrics['cache_hit_rate'])
                if metrics.get('error_rate', 0) > 0:
                    error_rates.append(metrics['error_rate'])
                
                total_requests += 1
                
            except (json.JSONDecodeError, KeyError):
                continue
    
    return {
        'total_requests': total_requests,
        'avg_response_time': sum(response_times) / len(response_times) if response_times else 0.0,
        'avg_memory_usage': sum(memory_usages) / len(memory_usages) if memory_usages else 0.0,
        'avg_cpu_usage': sum(cpu_usages) / len(cpu_usages) if cpu_usages else 0.0,
        'avg_cache_hit_rate': sum(cache_hit_rates) / len(cache_hit_rates) if cache_hit_rates else 0.0,
        'error_rate': sum(error_rates) / len(error_rates) if error_rates else 0.0
    }

def check_performance_alerts(monitor: PerformanceMonitor) -> List[str]:
    """
    パフォーマンスアラートをチェック
    
    Args:
        monitor: パフォーマンス監視インスタンス
    
    Returns:
        アラートメッセージのリスト
    """
    alerts = []
    metrics = monitor.get_metrics()
    
    # レスポンス時間アラート（5秒以上）
    if metrics['response_time_ms'] > 5000:
        alerts.append(f"⚠️ レスポンス時間が長すぎます: {metrics['response_time_ms']:.1f}ms")
    
    # メモリ使用率アラート（80%以上）
    if metrics['memory_usage_percent'] > 80:
        alerts.append(f"⚠️ メモリ使用率が高すぎます: {metrics['memory_usage_percent']:.1f}%")
    
    # CPU使用率アラート（90%以上）
    if metrics['cpu_usage_percent'] > 90:
        alerts.append(f"⚠️ CPU使用率が高すぎます: {metrics['cpu_usage_percent']:.1f}%")
    
    # エラー率アラート（10%以上）
    if metrics['error_rate'] > 0.1:
        alerts.append(f"⚠️ エラー率が高すぎます: {metrics['error_rate']:.1%}")
    
    # キャッシュヒット率アラート（30%未満）
    if metrics['cache_hit_rate'] < 0.3:
        alerts.append(f"⚠️ キャッシュヒット率が低すぎます: {metrics['cache_hit_rate']:.1%}")
    
    return alerts

# グローバルパフォーマンス監視インスタンス
_global_monitor = PerformanceMonitor()

def get_global_monitor() -> PerformanceMonitor:
    """グローバルパフォーマンス監視インスタンスを取得"""
    return _global_monitor
