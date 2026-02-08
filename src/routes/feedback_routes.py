"""
フィードバックAPIルート

責務: フィードバック関連APIのルート定義
"""
from flask import Blueprint


def create_feedback_routes(
    submit_feedback,
    get_feedback_reports,
    resolve_feedback,
    delete_feedback,
):
    """
    フィードバックルートのBlueprintを作成

    Returns:
        Blueprint
    """
    bp = Blueprint('feedback', __name__, url_prefix='/api')
    bp.add_url_rule('/submit_feedback', view_func=submit_feedback, methods=['POST'])
    bp.add_url_rule('/get_feedback_reports', view_func=get_feedback_reports, methods=['GET'])
    bp.add_url_rule('/resolve_feedback/<int:feedback_id>', view_func=resolve_feedback, methods=['POST'])
    bp.add_url_rule('/delete_feedback/<int:feedback_id>', view_func=delete_feedback, methods=['POST'])
    return bp
