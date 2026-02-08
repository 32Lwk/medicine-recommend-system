"""
ポート検出ユーティリティ

責務: ポートの利用可能性検出（find_free_port, is_port_in_use）
"""
import socket


def find_free_port(start_port: int = 5000, max_attempts: int = 100) -> int:
    """利用可能なポートを見つける"""
    for port in range(start_port, start_port + max_attempts):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('', port))
                return port
        except OSError:
            continue
    raise RuntimeError(
        f"利用可能なポートが見つかりませんでした ({start_port}-{start_port + max_attempts - 1})"
    )


def is_port_in_use(port: int) -> bool:
    """ポートが使用中かどうかをチェック"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(('', port))
            return False
        except OSError:
            return True
