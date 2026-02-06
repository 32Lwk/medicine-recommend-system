"""
アプリケーション設定・定数の集約

環境変数で上書き可能な定数を定義する。
"""
import os


def _get_int(key: str, default: int) -> int:
    """環境変数から整数を取得。無効な場合はデフォルトを返す。"""
    val = os.getenv(key)
    if val is None:
        return default
    try:
        return int(val)
    except ValueError:
        return default


# セッション関連
MAX_SESSIONS = _get_int('MAX_SESSIONS', 50)  # 最大セッション数（メモリ制約を考慮）
SESSION_TIMEOUT = _get_int('SESSION_TIMEOUT_SEC', 600)  # セッションタイムアウト（秒）- 10分
CHAT_END_TIMEOUT = _get_int('CHAT_END_TIMEOUT_SEC', 300)  # チャット終了後の削除タイムアウト（秒）- 5分

# クリーンアップ関連
CLEANUP_INTERVAL = _get_int('CLEANUP_INTERVAL_SEC', 60)  # クリーンアップ実行間隔（秒）- 1分ごと
MAX_CLEANUP_DELAY = _get_int('MAX_CLEANUP_DELAY_SEC', 300)  # 高負荷時のクリーンアップ遅延（秒）- 5分
