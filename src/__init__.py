# medicine-recommend application package
import os

# プロジェクトルート（data/, log/, .env 等の基準）。gunicorn/app はルートで起動する想定。
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
