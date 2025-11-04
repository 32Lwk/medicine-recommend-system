# Gunicorn設定ファイル

# ワーカープロセス数（同時接続対応のため増加）
workers = 2

# ワーカークラス（同期処理で安定性重視）
worker_class = 'sync'

# タイムアウト（秒）- Renderの制約に合わせて短縮
timeout = 120

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
keepalive = 2

