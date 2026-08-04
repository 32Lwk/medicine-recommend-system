"""
ポート検出ユーティリティ

責務: ポートの利用可能性検出、ローカル dev サーバーの停止
"""
from __future__ import annotations

import os
import re
import signal
import socket
import subprocess
import time
from typing import Iterable


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


def get_listening_pids(port: int) -> list[int]:
    """指定ポートで LISTEN しているプロセス ID を返す（OS 依存）。"""
    if os.name == 'nt':
        return _get_listening_pids_windows(port)
    return _get_listening_pids_unix(port)


def _get_listening_pids_windows(port: int) -> list[int]:
    try:
        result = subprocess.run(
            ['netstat', '-ano'],
            capture_output=True,
            text=True,
            check=False,
            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0),
        )
    except OSError:
        return []
    if result.returncode != 0:
        return []

    suffix = f':{port}'
    pids: list[int] = []
    for line in result.stdout.splitlines():
        if 'LISTENING' not in line:
            continue
        parts = line.split()
        if len(parts) < 5:
            continue
        local_addr = parts[1]
        if not local_addr.endswith(suffix):
            continue
        try:
            pid = int(parts[-1])
        except ValueError:
            continue
        if pid > 0 and pid not in pids:
            pids.append(pid)
    return pids


def _get_listening_pids_unix(port: int) -> list[int]:
    for cmd in (
        ['ss', '-ltnp', f'sport = :{port}'],
        ['lsof', '-nP', f'-iTCP:{port}', '-sTCP:LISTEN', '-t'],
    ):
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        except OSError:
            continue
        if result.returncode != 0:
            continue
        pids: list[int] = []
        if cmd[0] == 'ss':
            for match in re.finditer(r'pid=(\d+)', result.stdout):
                pid = int(match.group(1))
                if pid not in pids:
                    pids.append(pid)
        else:
            for line in result.stdout.splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    pid = int(line)
                except ValueError:
                    continue
                if pid not in pids:
                    pids.append(pid)
        if pids:
            return pids
    return []


def get_parent_pid(pid: int) -> int | None:
    """プロセスの親 PID を返す。"""
    if pid <= 0:
        return None
    if os.name == 'nt':
        try:
            result = subprocess.run(
                [
                    'powershell',
                    '-NoProfile',
                    '-Command',
                    f'(Get-CimInstance Win32_Process -Filter "ProcessId={pid}").ParentProcessId',
                ],
                capture_output=True,
                text=True,
                check=False,
                creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0),
            )
        except OSError:
            return None
        if result.returncode != 0:
            return None
        text = result.stdout.strip()
        try:
            parent = int(text)
        except ValueError:
            return None
        return parent if parent > 0 else None

    try:
        with open(f'/proc/{pid}/status', encoding='utf-8') as fh:
            for line in fh:
                if line.startswith('PPid:'):
                    parent = int(line.split()[1])
                    return parent if parent > 0 else None
    except OSError:
        return None
    return None


def get_process_command_line(pid: int) -> str | None:
    """プロセスのコマンドラインを返す。"""
    if pid <= 0:
        return None
    if os.name == 'nt':
        try:
            result = subprocess.run(
                [
                    'powershell',
                    '-NoProfile',
                    '-Command',
                    f'(Get-CimInstance Win32_Process -Filter "ProcessId={pid}").CommandLine',
                ],
                capture_output=True,
                text=True,
                check=False,
                creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0),
            )
        except OSError:
            return None
        if result.returncode != 0:
            return None
        text = result.stdout.strip()
        return text or None

    try:
        with open(f'/proc/{pid}/cmdline', 'rb') as fh:
            raw = fh.read().replace(b'\0', b' ').strip()
        if not raw:
            return None
        return raw.decode('utf-8', errors='replace')
    except OSError:
        return None


def _is_local_dev_app_process(command_line: str | None) -> bool:
    if not command_line:
        return False
    lowered = command_line.lower()
    return 'app.py' in lowered and (
        'medicine-recommend' in lowered.replace('\\', '/')
        or lowered.rstrip().endswith('app.py')
        or lowered.rstrip().endswith('app.py"')
    )


def find_local_dev_root_pid(start_pid: int | None = None) -> int | None:
    """app.py ローカル dev のプロセスツリー根（親方向に app.py を含む最上位）。"""
    pid = start_pid if start_pid is not None else os.getpid()
    root: int | None = None
    seen: set[int] = set()
    for _ in range(16):
        if pid in seen or pid <= 0:
            break
        seen.add(pid)
        if _is_local_dev_app_process(get_process_command_line(pid)):
            root = pid
        parent = get_parent_pid(pid)
        if parent is None or parent <= 0 or parent == pid:
            break
        pid = parent
    return root


def kill_process_tree(pid: int, *, force: bool = True) -> bool:
    """プロセスと子プロセスを停止する。Windows は taskkill /T を使う。"""
    if pid <= 0:
        return False
    if os.name == 'nt':
        args = ['taskkill', '/PID', str(pid), '/T']
        if force:
            args.append('/F')
        result = subprocess.run(
            args,
            capture_output=True,
            text=True,
            check=False,
            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0),
        )
        return result.returncode == 0

    sig = signal.SIGKILL if force else signal.SIGTERM
    try:
        os.kill(pid, sig)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return False


def stop_local_dev_process_tree(start_pid: int | None = None) -> bool:
    """現在または指定 PID から app.py ツリー根まで遡り、プロセスツリー全体を停止。"""
    root = find_local_dev_root_pid(start_pid)
    if root is None:
        pid = start_pid if start_pid is not None else os.getpid()
        return kill_process_tree(pid)
    return kill_process_tree(root)


def stop_local_dev_servers(
    ports: Iterable[int] = (5000, 5001),
    *,
    settle_sec: float = 0.5,
) -> list[int]:
    """ローカル app.py / uvicorn が bind しているポートのプロセスツリーを停止。"""
    target_roots: list[int] = []
    for port in ports:
        for pid in get_listening_pids(port):
            root = find_local_dev_root_pid(pid) or pid
            if root not in target_roots:
                target_roots.append(root)

    killed: list[int] = []
    for pid in target_roots:
        if kill_process_tree(pid):
            killed.append(pid)
    if killed and settle_sec > 0:
        time.sleep(settle_sec)
    return killed


def format_port_conflict_message(port: int, pids: list[int] | None = None) -> str:
    """ポート競合時に app.py が表示する案内文。"""
    pid_text = ', '.join(str(pid) for pid in (pids or get_listening_pids(port))) or '不明'
    return (
        f'ポート {port} は既に使用中です (PID: {pid_text})。\n'
        '前回の app.py / uvicorn が残っている可能性があります。\n'
        '停止: python scripts/stop_local_dev.py\n'
        '      .\\scripts\\stop-local-dev.ps1\n'
        '別ポートで起動する場合: APP_PORT_FALLBACK=1 python app.py'
    )
