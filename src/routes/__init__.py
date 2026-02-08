"""
ルート（Blueprint）パッケージ

責務: Flask Blueprint の定義とエクスポート
"""
from src.routes.main_routes import create_main_routes
from src.routes.admin_routes import create_admin_routes
from src.routes.api_routes import create_api_routes
from src.routes.feedback_routes import create_feedback_routes

__all__ = [
    'create_main_routes',
    'create_admin_routes',
    'create_api_routes',
    'create_feedback_routes',
]
