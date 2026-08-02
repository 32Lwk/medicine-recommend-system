"""ローカル dev サーバー（app.py）向けの reload 判定と停止処理。"""
from __future__ import annotations

import logging
import os
import signal
import threading
from typing import Any

logger = logging.getLogger(__name__)


def resolve_uvicorn_reload(*, is_development: bool) -> bool:
    """UVICORN_RELOAD 未指定時は Windows では reload しない（Ctrl+C / 子プロセス残留対策）。"""
    reload_env = os.getenv("UVICORN_RELOAD", "").strip().lower()
    if reload_env in ("1", "true", "yes"):
        return True
    if reload_env in ("0", "false", "no"):
        return False
    if os.name == "nt":
        return False
    return is_development


def resolve_uvicorn_graceful_shutdown_sec() -> float:
    """graceful shutdown 上限。Windows 未指定時は 0s（即時切断 — Ctrl+C 残留対策）。"""
    default = "0" if os.name == "nt" else "5"
    raw = os.getenv("UVICORN_GRACEFUL_SHUTDOWN_SEC", default).strip()
    try:
        return max(0.0, float(raw))
    except ValueError:
        return 0.0 if os.name == "nt" else 5.0


def _force_exit_delay_sec(timeout_graceful_shutdown: float) -> float:
    if os.name == "nt":
        # PowerShell は Ctrl+C 後すぐプロンプトを返すため、猶予は最小限にする。
        return max(0.15, float(timeout_graceful_shutdown) + 0.15)
    return max(0.5, float(timeout_graceful_shutdown) + 0.5)


def _dev_force_exit(reason: str, *, stop_once: threading.Event) -> None:
    """ThreadPoolExecutor 等の非 daemon ワーカーごとプロセスを終了する。"""
    if stop_once.is_set():
        return
    stop_once.set()
    logger.info("停止 (%s)", reason)
    shutdown_background_executors()
    os._exit(0)


def _schedule_force_exit_on_shutdown_timeout(
    *,
    reason: str,
    timeout_graceful_shutdown: float,
    timer_holder: list[threading.Timer | None],
    timer_lock: threading.Lock,
    stop_once: threading.Event,
) -> None:
    """Ctrl+C 後、uvicorn graceful shutdown が完了しない場合に os._exit する。"""
    if os.name == "nt":
        _dev_force_exit(reason, stop_once=stop_once)
        return

    with timer_lock:
        if timer_holder[0] is not None:
            return
        delay = _force_exit_delay_sec(timeout_graceful_shutdown)
        logger.info(
            "停止シグナル (%s) — graceful shutdown 最大 %.1fs（超過時は強制終了）",
            reason,
            timeout_graceful_shutdown,
        )

        def _force_exit() -> None:
            logger.warning(
                "graceful shutdown が %.1fs 以内に完了しませんでした — 強制終了します",
                delay,
            )
            _dev_force_exit(f"{reason} (timeout)", stop_once=stop_once)

        timer = threading.Timer(delay, _force_exit)
        timer.daemon = True
        timer_holder[0] = timer
        timer.start()


def _install_windows_console_ctrl_handler(on_stop) -> None:
    """signal より先に Console Ctrl+C を拾う（PowerShell で PS だけ戻る残留対策）。"""
    import ctypes
    from ctypes import wintypes

    kernel32 = ctypes.windll.kernel32
    handler_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.DWORD)

    @handler_type
    def _handler(ctrl_type: int) -> bool:
        # 0=CTRL_C, 1=CTRL_BREAK, 2=CTRL_CLOSE, 5=LOGOFF, 6=SHUTDOWN
        if ctrl_type in (0, 1, 2):
            on_stop(f"console-{ctrl_type}")
            return True
        return False

    if not kernel32.SetConsoleCtrlHandler(_handler, True):
        logger.debug("SetConsoleCtrlHandler の登録に失敗しました")


def run_uvicorn_dev(app: str, **uvicorn_kwargs: Any) -> None:
    """uvicorn ローカル dev 起動。Windows で Ctrl+C 後にプロセスが残留しないよう強制終了する。"""
    import uvicorn

    timeout_graceful_shutdown = float(
        uvicorn_kwargs.get("timeout_graceful_shutdown", resolve_uvicorn_graceful_shutdown_sec())
    )
    reload = bool(uvicorn_kwargs.get("reload", False))
    timer_holder: list[threading.Timer | None] = [None]
    timer_lock = threading.Lock()
    stop_once = threading.Event()

    def _on_stop(reason: str) -> None:
        _schedule_force_exit_on_shutdown_timeout(
            reason=reason,
            timeout_graceful_shutdown=timeout_graceful_shutdown,
            timer_holder=timer_holder,
            timer_lock=timer_lock,
            stop_once=stop_once,
        )

    if os.name == "nt":
        _install_windows_console_ctrl_handler(_on_stop)

    try:
        if reload:
            _install_reload_stop_watchdog(_on_stop)
            uvicorn.run(app, **uvicorn_kwargs)
        else:
            config = uvicorn.Config(app, **uvicorn_kwargs)
            server = uvicorn.Server(config)
            original_handle_exit = server.handle_exit

            def handle_exit(signum: int, frame: Any) -> None:
                sig_name = "SIGINT" if signum == signal.SIGINT else str(signum)
                if os.name == "nt":
                    _on_stop(sig_name)
                    return
                _on_stop(sig_name)
                original_handle_exit(signum, frame)

            server.handle_exit = handle_exit  # type: ignore[method-assign]
            server.run()
    except KeyboardInterrupt:
        _on_stop("KeyboardInterrupt")
    finally:
        timer = timer_holder[0]
        if timer is not None:
            timer.cancel()
        _dev_force_exit("shutdown complete", stop_once=stop_once)


def _install_reload_stop_watchdog(on_stop) -> None:
    """reload 監督プロセス向け: SIGINT / SIGBREAK で強制終了タイマーを開始。"""

    def _combined(signum: int, frame: Any) -> None:
        sig_name = "SIGINT" if signum == signal.SIGINT else str(signum)
        on_stop(sig_name)
        if os.name != "nt":
            raise KeyboardInterrupt

    signal.signal(signal.SIGINT, _combined)
    if hasattr(signal, "SIGBREAK"):
        signal.signal(signal.SIGBREAK, _combined)


def shutdown_background_executors() -> None:
    """Ctrl+C 後に ThreadPoolExecutor の非 daemon ワーカーがプロセスを留めないよう解放。"""
    for label, import_fn in (
        ("chat_worker", _shutdown_chat_worker),
        ("llm_async", _shutdown_llm_executor),
        ("proc_status", _shutdown_processing_status_executor),
        ("detail_log", _shutdown_detail_log_executor),
        ("feedback_trace", _shutdown_feedback_trace_executor),
    ):
        try:
            import_fn()
        except Exception as exc:
            logger.debug("executor shutdown skipped (%s): %s", label, exc)


def _shutdown_chat_worker() -> None:
    from src.services.chat_worker import shutdown_chat_executor

    shutdown_chat_executor()


def _shutdown_llm_executor() -> None:
    from src.core.llm_client import shutdown_llm_executor

    shutdown_llm_executor()


def _shutdown_processing_status_executor() -> None:
    from src.services.processing_status import shutdown_processing_status_executor

    shutdown_processing_status_executor()


def _shutdown_detail_log_executor() -> None:
    from src.utils.structured_logger import shutdown_detail_log_executor

    shutdown_detail_log_executor()


def _shutdown_feedback_trace_executor() -> None:
    from src.services.feedback_trace import shutdown_feedback_trace_executor

    shutdown_feedback_trace_executor()
