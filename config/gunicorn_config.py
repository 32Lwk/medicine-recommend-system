# Gunicorn設定ファイル

# ワーカープロセス数（同時接続対応のため増加）
workers = 2

# ワーカークラス（同期処理で安定性重視）
worker_class = 'sync'

# タイムアウト（秒）- 処理時間を考慮して増加
# 医薬品推奨処理（最大30秒）+ 翻訳処理（最大10秒）+ バッファ
timeout = 120
# グレースフル・タイムアウト（workerの再起動時間）
graceful_timeout = 30

# バインドするアドレスとポート
import os
port = int(os.getenv('PORT', 5000))
bind = f'0.0.0.0:{port}'

# ログレベル
loglevel = 'info'

# アクセスログ
accesslog = '-'

# エラーログ
errorlog = '-'

# プロセス名
proc_name = 'medicine-recommend-app'

# ワーカーの再起動前のリクエスト数（メモリリーク対策）
max_requests = 1000
max_requests_jitter = 50

# メモリ制限（MB）- インスタンスのメモリ制限に合わせて設定
worker_memory_limit = 512

# Keep-aliveタイムアウト（短縮して接続効率を向上）
keepalive = 5

# ワーカーの応答時間を監視
worker_timeout = 120

# プリロード（メモリ効率化）
preload_app = False  # Falseにすることで各workerが独立して動作

# ログフォーマット
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s"'

