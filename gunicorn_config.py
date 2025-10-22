# Gunicorn設定ファイル

# ワーカープロセス数（推奨: CPU数 * 2 + 1）
workers = 2

# ワーカークラス（非同期処理で効率化）
worker_class = 'gevent'
worker_connections = 1000

# タイムアウト（秒）- ChatGPT API呼び出しを考慮して大幅延長
timeout = 600

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

# ワーカーの再起動前のリクエスト数（メモリ使用量を考慮して削減）
max_requests = 200
max_requests_jitter = 20

# メモリ制限（MB）- 大幅に増加
worker_memory_limit = 1024

# Keep-aliveタイムアウト
keepalive = 5

