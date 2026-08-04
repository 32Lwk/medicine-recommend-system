"""app.py ローカル dev サーバー向けユーティリティ。"""

from __future__ import annotations

import pytest


def test_resolve_uvicorn_reload_windows_default_off(monkeypatch):
    monkeypatch.setattr("src.utils.dev_server.os.name", "nt", raising=False)
    monkeypatch.delenv("UVICORN_RELOAD", raising=False)

    from src.utils.dev_server import resolve_uvicorn_reload

    assert resolve_uvicorn_reload(is_development=True) is False


def test_resolve_uvicorn_reload_windows_explicit_on(monkeypatch):
    monkeypatch.setattr("src.utils.dev_server.os.name", "nt", raising=False)
    monkeypatch.setenv("UVICORN_RELOAD", "1")

    from src.utils.dev_server import resolve_uvicorn_reload

    assert resolve_uvicorn_reload(is_development=True) is True


def test_resolve_uvicorn_reload_unix_dev_default_on(monkeypatch):
    monkeypatch.setattr("src.utils.dev_server.os.name", "posix", raising=False)
    monkeypatch.delenv("UVICORN_RELOAD", raising=False)

    from src.utils.dev_server import resolve_uvicorn_reload

    assert resolve_uvicorn_reload(is_development=True) is True


def test_resolve_uvicorn_graceful_shutdown_windows_default(monkeypatch):
    monkeypatch.setattr("src.utils.dev_server.os.name", "nt", raising=False)
    monkeypatch.delenv("UVICORN_GRACEFUL_SHUTDOWN_SEC", raising=False)

    from src.utils.dev_server import resolve_uvicorn_graceful_shutdown_sec

    assert resolve_uvicorn_graceful_shutdown_sec() == 0.0


def test_resolve_uvicorn_graceful_shutdown_unix_default(monkeypatch):
    monkeypatch.setattr("src.utils.dev_server.os.name", "posix", raising=False)
    monkeypatch.delenv("UVICORN_GRACEFUL_SHUTDOWN_SEC", raising=False)

    from src.utils.dev_server import resolve_uvicorn_graceful_shutdown_sec

    assert resolve_uvicorn_graceful_shutdown_sec() == 5.0


def test_schedule_force_exit_starts_timer_once(monkeypatch):
    monkeypatch.setattr("src.utils.dev_server.os.name", "posix", raising=False)
    started: list[float] = []
    timer_holder: list = [None]
    lock = __import__("threading").Lock()
    stop_once = __import__("threading").Event()

    class FakeTimer:
        def __init__(self, delay, fn):
            started.append(delay)
            self.fn = fn

        def start(self):
            return None

        def cancel(self):
            return None

    monkeypatch.setattr("src.utils.dev_server.threading.Timer", FakeTimer)

    from src.utils.dev_server import _schedule_force_exit_on_shutdown_timeout

    _schedule_force_exit_on_shutdown_timeout(
        reason="SIGINT",
        timeout_graceful_shutdown=2.0,
        timer_holder=timer_holder,
        timer_lock=lock,
        stop_once=stop_once,
    )
    _schedule_force_exit_on_shutdown_timeout(
        reason="SIGINT",
        timeout_graceful_shutdown=2.0,
        timer_holder=timer_holder,
        timer_lock=lock,
        stop_once=stop_once,
    )

    assert started == [2.5]


def test_schedule_force_exit_immediate_on_windows(monkeypatch):
    monkeypatch.setattr("src.utils.dev_server.os.name", "nt", raising=False)
    exits: list[str] = []
    tree_stops: list[int] = []
    stop_once = __import__("threading").Event()

    monkeypatch.setattr(
        "src.utils.dev_server._dev_force_exit",
        lambda reason, stop_once=stop_once: exits.append(reason),
    )

    from src.utils.dev_server import _schedule_force_exit_on_shutdown_timeout

    _schedule_force_exit_on_shutdown_timeout(
        reason="SIGINT",
        timeout_graceful_shutdown=0.0,
        timer_holder=[None],
        timer_lock=__import__("threading").Lock(),
        stop_once=stop_once,
    )

    assert exits == ["SIGINT"]


def test_dev_force_exit_stops_process_tree_on_windows(monkeypatch):
    monkeypatch.setattr("src.utils.dev_server.os.name", "nt", raising=False)
    calls: list[str] = []
    stop_once = __import__("threading").Event()

    monkeypatch.setattr(
        "src.utils.dev_server.shutdown_background_executors",
        lambda: calls.append("shutdown"),
    )
    monkeypatch.setattr(
        "src.utils.port_utils.stop_local_dev_process_tree",
        lambda start_pid=None: calls.append("tree") or True,
    )
    monkeypatch.setattr(
        "src.utils.dev_server.os._exit",
        lambda code: calls.append(f"exit:{code}"),
    )

    from src.utils.dev_server import _dev_force_exit

    _dev_force_exit("SIGINT", stop_once=stop_once)
    assert calls == ["shutdown", "tree", "exit:0"]


def test_run_uvicorn_dev_wraps_handle_exit_and_force_exits(monkeypatch):
    monkeypatch.setattr("src.utils.dev_server.os.name", "posix", raising=False)
    calls: list[str] = []

    class FakeServer:
        def __init__(self, config):
            self.config = config

        def handle_exit(self, signum, frame):
            calls.append("original")

        def run(self):
            calls.append("run")
            self.handle_exit(2, None)

    class FakeConfig:
        def __init__(self, app, **kwargs):
            self.kwargs = kwargs

    monkeypatch.setattr("uvicorn.Config", FakeConfig)
    monkeypatch.setattr("uvicorn.Server", FakeServer)
    monkeypatch.setattr(
        "src.utils.dev_server.shutdown_background_executors",
        lambda: calls.append("shutdown"),
    )
    monkeypatch.setattr(
        "src.utils.dev_server.os._exit",
        lambda code: calls.append(f"exit:{code}"),
    )

    from src.utils.dev_server import run_uvicorn_dev

    run_uvicorn_dev("main:app", host="127.0.0.1", port=5000, reload=False)

    assert calls == ["run", "original", "shutdown", "exit:0"]


def test_shutdown_background_executors_calls_workers(monkeypatch):
    calls: list[str] = []

    def _fake_shutdown(name: str):
        calls.append(name)

    monkeypatch.setattr(
        "src.utils.dev_server._shutdown_chat_worker",
        lambda: _fake_shutdown("chat"),
    )
    monkeypatch.setattr(
        "src.utils.dev_server._shutdown_llm_executor",
        lambda: _fake_shutdown("llm"),
    )
    monkeypatch.setattr(
        "src.utils.dev_server._shutdown_processing_status_executor",
        lambda: _fake_shutdown("proc"),
    )
    monkeypatch.setattr(
        "src.utils.dev_server._shutdown_detail_log_executor",
        lambda: _fake_shutdown("detail"),
    )
    monkeypatch.setattr(
        "src.utils.dev_server._shutdown_feedback_trace_executor",
        lambda: _fake_shutdown("feedback"),
    )

    from src.utils.dev_server import shutdown_background_executors

    shutdown_background_executors()
    assert calls == ["chat", "llm", "proc", "detail", "feedback"]
