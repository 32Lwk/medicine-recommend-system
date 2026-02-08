"""
管理画面・管理APIルート

責務: 管理画面、管理APIのルート定義
"""
from flask import Blueprint


def create_admin_routes(
    admin,
    admin_system_status,
    admin_access_stats,
    admin_performance_stats,
    admin_browser_distribution,
    admin_os_distribution,
    admin_device_distribution,
    admin_realtime_monitoring,
    admin_export_monitoring_data,
    clear_logs,
    admin_ai_control,
    admin_medicine_chat,
    get_all_sessions,
    delete_session,
    delete_all_sessions,
    update_session,
    admin_send_message,
):
    """
    管理ルートのBlueprintを作成

    Returns:
        Blueprint
    """
    bp = Blueprint('admin', __name__)
    bp.add_url_rule('/admin', view_func=admin)
    bp.add_url_rule('/admin/system_status', view_func=admin_system_status, methods=['GET'])
    bp.add_url_rule('/admin/access_stats', view_func=admin_access_stats, methods=['GET'])
    bp.add_url_rule('/admin/performance_stats', view_func=admin_performance_stats, methods=['GET'])
    bp.add_url_rule('/admin/browser_distribution', view_func=admin_browser_distribution, methods=['GET'])
    bp.add_url_rule('/admin/os_distribution', view_func=admin_os_distribution, methods=['GET'])
    bp.add_url_rule('/admin/device_distribution', view_func=admin_device_distribution, methods=['GET'])
    bp.add_url_rule('/admin/realtime_monitoring', view_func=admin_realtime_monitoring, methods=['GET'])
    bp.add_url_rule('/admin/export_monitoring_data', view_func=admin_export_monitoring_data, methods=['GET'])
    bp.add_url_rule('/clear_logs', view_func=clear_logs, methods=['POST'])
    bp.add_url_rule('/admin/ai_control', view_func=admin_ai_control, methods=['POST'])
    bp.add_url_rule('/admin/medicine_chat', view_func=admin_medicine_chat, methods=['POST'])
    bp.add_url_rule('/api/admin/sessions', view_func=get_all_sessions, methods=['GET'])
    bp.add_url_rule('/api/admin/sessions/<session_id>', view_func=delete_session, methods=['DELETE'])
    bp.add_url_rule('/api/admin/sessions/delete_all', view_func=delete_all_sessions, methods=['DELETE'])
    bp.add_url_rule('/api/admin/sessions/<session_id>', view_func=update_session, methods=['PUT'])
    bp.add_url_rule('/api/admin/send_message', view_func=admin_send_message, methods=['POST'])
    return bp
