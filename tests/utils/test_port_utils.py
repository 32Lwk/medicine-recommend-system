"""port_utils のユニットテスト。"""

from __future__ import annotations

import pytest


def test_get_listening_pids_windows_parses_netstat(monkeypatch):
    monkeypatch.setattr('src.utils.port_utils.os.name', 'nt', raising=False)

    class Result:
        returncode = 0
        stdout = (
            '  TCP    0.0.0.0:5000           0.0.0.0:0              LISTENING       12345\n'
            '  TCP    127.0.0.1:5001         0.0.0.0:0              LISTENING       67890\n'
            '  TCP    0.0.0.0:5000           0.0.0.0:0              LISTENING       12345\n'
        )

    monkeypatch.setattr(
        'src.utils.port_utils.subprocess.run',
        lambda *args, **kwargs: Result(),
    )

    from src.utils.port_utils import get_listening_pids

    assert get_listening_pids(5000) == [12345]
    assert get_listening_pids(5001) == [67890]
    assert get_listening_pids(5002) == []


def test_kill_process_tree_windows_uses_taskkill(monkeypatch):
    monkeypatch.setattr('src.utils.port_utils.os.name', 'nt', raising=False)
    calls: list[list[str]] = []

    class Result:
        returncode = 0

    monkeypatch.setattr(
        'src.utils.port_utils.subprocess.run',
        lambda args, **kwargs: calls.append(list(args)) or Result(),
    )

    from src.utils.port_utils import kill_process_tree

    assert kill_process_tree(42) is True
    assert calls == [['taskkill', '/PID', '42', '/T', '/F']]


def test_stop_local_dev_servers_kills_listener_roots(monkeypatch):
    seen_ports: list[int] = []

    def fake_get_listening_pids(port: int) -> list[int]:
        seen_ports.append(port)
        return [port + 1000]

    def fake_find_root(pid: int) -> int:
        return pid + 5000

    kills: list[int] = []
    monkeypatch.setattr(
        'src.utils.port_utils.get_listening_pids',
        fake_get_listening_pids,
    )
    monkeypatch.setattr(
        'src.utils.port_utils.find_local_dev_root_pid',
        fake_find_root,
    )
    monkeypatch.setattr(
        'src.utils.port_utils.kill_process_tree',
        lambda pid, **kwargs: kills.append(pid) or True,
    )
    monkeypatch.setattr('src.utils.port_utils.time.sleep', lambda _sec: None)

    from src.utils.port_utils import stop_local_dev_servers

    killed = stop_local_dev_servers((5000, 5001))
    assert seen_ports == [5000, 5001]
    assert killed == [11000, 11001]


def test_find_local_dev_root_pid_walks_parents(monkeypatch):
    commands = {
        40036: r'D:\Programing\medicine-recommend\.venv\Scripts\python.exe app.py',
        10348: r'D:\Programing\medicine-recommend\.venv\Scripts\python.exe app.py',
        69900: r'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe',
    }
    parents = {40036: 10348, 10348: 69900, 69900: 0}

    monkeypatch.setattr(
        'src.utils.port_utils.get_process_command_line',
        lambda pid: commands.get(pid),
    )
    monkeypatch.setattr(
        'src.utils.port_utils.get_parent_pid',
        lambda pid: parents.get(pid),
    )

    from src.utils.port_utils import find_local_dev_root_pid

    assert find_local_dev_root_pid(40036) == 10348


def test_format_port_conflict_message_includes_stop_script():
    from src.utils.port_utils import format_port_conflict_message

    message = format_port_conflict_message(5000, [111, 222])
    assert '5000' in message
    assert '111, 222' in message
    assert 'stop_local_dev.py' in message
    assert 'APP_PORT_FALLBACK=1' in message
