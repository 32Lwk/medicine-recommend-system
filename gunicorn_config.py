# Gunicorn設定ファイル

# ワーカープロセス数（推奨: CPU数 * 2 + 1）
workers = 2

# ワーカークラス
worker_class = 'sync'

# タイムアウト（秒）
timeout = 120

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

# ワーカーの再起動前のリクエスト数
max_requests = 1000
max_requests_jitter = 50

# Keep-aliveタイムアウト
keepalive = 5

