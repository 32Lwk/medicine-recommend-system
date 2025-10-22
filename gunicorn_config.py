# Gunicorn設定ファイル

# ワーカープロセス数（Render無料プラン用に削減）
workers = 1

# ワーカークラス（同期処理で安定性重視）
worker_class = 'sync'

# タイムアウト（秒）- Render制限内で最適化
timeout = 300

# バインドするアドレスとポート
bind = '0.0.0.0:5000'

# ログレベル
loglevel = 'info'

# アクセスログ
accesslog = '-'

# エラーログ
errorlog = '-'

# プロセス名
proc_name = 'medicine-recommend-app'

# ワーカーの再起動前のリクエスト数（Render無料プラン用に削減）
max_requests = 100
max_requests_jitter = 10

# メモリ制限（MB）- Render無料プラン制限内
worker_memory_limit = 512

# Keep-aliveタイムアウト
keepalive = 5

