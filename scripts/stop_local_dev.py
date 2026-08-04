#!/usr/bin/env python3
"""ローカル app.py / uvicorn（既定 5000・5001）をプロセスツリーごと停止する。"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from src.utils.port_utils import (  # noqa: E402
    get_listening_pids,
    stop_local_dev_servers,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        '--port',
        type=int,
        action='append',
        dest='ports',
        help='停止対象ポート（省略時: 5000, 5001）',
    )
    args = parser.parse_args()
    ports = tuple(args.ports) if args.ports else (5000, 5001)

    before = {port: get_listening_pids(port) for port in ports}
    killed = stop_local_dev_servers(ports)
    after = {port: get_listening_pids(port) for port in ports}

    if not any(before.values()):
        print('停止対象のローカル dev サーバーは見つかりませんでした。')
        return 0

    for port, pids in before.items():
        if pids:
            print(f'ポート {port}: PID {", ".join(map(str, pids))} を停止しました。')
    if killed:
        print(f'プロセスツリー停止: {", ".join(map(str, killed))}')

    remaining = [port for port, pids in after.items() if pids]
    if remaining:
        print(
            '警告: まだ LISTEN 中のポートがあります — '
            + ', '.join(f'{port} (PID {after[port]})' for port in remaining),
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
