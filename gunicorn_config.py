# Gunicorn設定ファイル

# ワーカープロセス数（Render無料プラン向け）
workers = 1

# I/Oに強いスレッド型ワーカー
worker_class = 'gthread'
threads = 2

# タイムアウト（秒）- Renderの約100秒制限を考慮
timeout = 90
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
max_requests = 20
max_requests_jitter = 10

# メモリ制限（MB）- Render無料プラン制限内
worker_memory_limit = 512

# Keep-aliveタイムアウトを短めに
keepalive = 2

# アプリを事前ロードしてCoWでメモリ最適化
preload_app = True

