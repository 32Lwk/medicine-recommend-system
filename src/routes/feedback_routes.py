"""
フィードバックAPIルート

責務: フィードバック関連APIのルート定義とビュー実装
"""
import logging
import time

from flask import Blueprint, current_app, jsonify, request

from src.services.database import get_database

logger = logging.getLogger(__name__)


def submit_feedback():
    """フィードバックをデータベースに保存"""
    session = current_app.extensions['safe_session']
    try:
        data = request.json
        logger.info(f"📝 Feedback submission: {data}")

        db = get_database()
        if not (db and (db.connection or db.connection_pool)):
            return jsonify({'error': 'Database not available'}), 500

        required_fields = ['report_type', 'user_message', 'ai_response']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400

        session_id = session.get('_id')
        if session_id:
            current_time = time.time()
            last_feedback_time = session.get('last_feedback_time', 0)
            if current_time - last_feedback_time < 60:
                return jsonify({'error': 'Rate limit exceeded. Please wait 60 seconds.'}), 429
            session['last_feedback_time'] = current_time

        feedback_text = data.get('feedback_text', '')
        if len(feedback_text) > 1000:
            return jsonify({'error': 'Feedback text too long (max 1000 characters)'}), 400

        feedback_id = db.insert_feedback(
            report_type=data['report_type'],
            session_id=session_id,
            username=session.get('username', 'Unknown'),
            user_message=data['user_message'],
            ai_response=data['ai_response'],
            security_score=data.get('security_score'),
            feedback_text=feedback_text,
            is_google_form=data.get('is_google_form', False)
        )

        if feedback_id:
            logger.info(f"✅ Feedback saved with ID: {feedback_id}")
            if data.get('report_type') == 'negative_feedback' and session_id:
                try:
                    from src.utils.structured_logger import log_counseling_detail
                    messages = session.get('messages', [])
                    conversation_history = messages[-10:] if len(messages) > 10 else messages
                    log_counseling_detail(
                        session_id=session_id,
                        user_input=data.get('user_message', ''),
                        response=data.get('ai_response', ''),
                        conversation_history=conversation_history
                    )
                    logger.info(f"📝 不適切評価ログ記録完了 [session_id: {session_id}, feedback_id: {feedback_id}]")
                except Exception as log_error:
                    logger.warning(f"不適切評価ログ記録エラー: {log_error}")
            return jsonify({'status': 'success', 'feedback_id': feedback_id})
        return jsonify({'error': 'Failed to save feedback'}), 500
    except Exception as e:
        logger.error(f"❌ Feedback submission error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


def get_feedback_reports():
    """フィードバック報告一覧を取得（管理画面用）"""
    try:
        db = get_database()
        if not (db and (db.connection or db.connection_pool)):
            return jsonify({'error': 'Database not available'}), 500
        limit = request.args.get('limit', 100, type=int)
        unresolved_only = request.args.get('unresolved_only', 'false').lower() == 'true'
        reports = db.get_feedback_reports(limit=limit, unresolved_only=unresolved_only)
        logger.info(f"📊 Retrieved {len(reports)} feedback reports")
        return jsonify({'reports': reports})
    except Exception as e:
        import traceback
        logger.error(f"❌ Get feedback reports error: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({'error': f'Internal server error: {str(e)}'}), 500


def resolve_feedback(feedback_id):
    """フィードバックを解決済みにマーク"""
    try:
        db = get_database()
        if not (db and (db.connection or db.connection_pool)):
            return jsonify({'error': 'Database not available'}), 500
        success = db.resolve_feedback(feedback_id)
        if success:
            logger.info(f"✅ Feedback {feedback_id} marked as resolved")
            return jsonify({'status': 'success'})
        return jsonify({'error': 'Failed to resolve feedback'}), 500
    except Exception as e:
        logger.error(f"❌ Resolve feedback error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


def delete_feedback(feedback_id):
    """フィードバックを削除"""
    try:
        db = get_database()
        if not (db and (db.connection or db.connection_pool)):
            return jsonify({'error': 'Database not available'}), 500
        success = db.delete_feedback(feedback_id)
        if success:
            logger.info(f"🗑️ Feedback {feedback_id} deleted")
            return jsonify({'status': 'success'})
        return jsonify({'error': 'Failed to delete feedback'}), 500
    except Exception as e:
        logger.error(f"❌ Delete feedback error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


def create_feedback_routes():
    """フィードバックルートの Blueprint を作成（ビューは当モジュール内で定義）"""
    bp = Blueprint('feedback', __name__, url_prefix='/api')
    bp.add_url_rule('/submit_feedback', view_func=submit_feedback, methods=['POST'])
    bp.add_url_rule('/get_feedback_reports', view_func=get_feedback_reports, methods=['GET'])
    bp.add_url_rule('/resolve_feedback/<int:feedback_id>', view_func=resolve_feedback, methods=['POST'])
    bp.add_url_rule('/delete_feedback/<int:feedback_id>', view_func=delete_feedback, methods=['POST'])
    return bp
