#!/usr/bin/env python3
"""Create sub-issues only (continuation)."""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = "32Lwk/medicine-recommend-system"
FOOTER = "\n\n---\n_2026-06-11 調査に基づき自動作成。ロードマップ: #71_"

SUB_ISSUES = [
    (31, "安全回帰: red_team.jsonl 作成", """## 目的
`tests/fixtures/safety/red_team.jsonl` を作成し、安全回帰テストを有効化。

## 対象テスト
`tests/integration/test_safety_regression.py`

## ケース例（5件以上）
- プロンプトインジェクション → Physical に流れない
- 緊急ワード誤判定 → 挨拶が Emergency にならない
- 禁忌薬要求 → 推奨されない

## 工数: **8–16h** | 親: #31 | 関連: #73""", ["scoring", "enhancement", "P1"], "2026-Q2 Core"),

    (31, "ルーティング golden: routing_golden.jsonl 作成", """## 目的
`tests/fixtures/routing/routing_golden.jsonl` を作成。

## 対象テスト
`tests/routing/test_routing_golden.py`

## ケース例（10件以上）
- Physical / Ask / Emotional / Emergency / Other
- Concierge 挨拶 → Other + concierge_intent
- 比較質問 → （将来）medicine_comparison

## 工数: **8–16h** | 親: #31 | 関連: #73, #75""", ["scoring", "enhancement", "P1"], "2026-Q2 Core"),

    (48, "bug: ask_agent.py 引数順不一致の修正", """## 目的
`chat_with_medicine_context` への引数渡しを修正。

## 現状のバグ
```python
# ask_agent.py（誤り）
chat_with_medicine_context(user_text, recommended_medicines, medicine_list or [], ...)
# 正しいシグネチャ: (user_message, conversation_history, recommended_medicines, ...)
```

## 影響
- `handle_ask_category` 経路でコンテキストが壊れる（現状はデッドコードだが #64 前に修正必須）
- メイン経路 `run_medicine_question_qa` は正しい

## 実装
1. 引数をキーワード明示に修正
2. 単体テスト追加
3. `handle_ask_category` の呼び出し元を確認 or 削除

## 工数: **4h** | 優先度: **P1** | 親: #48 | ブロッカー: #64""", ["comparison", "bug", "P1"], "2026-Q3 Comparison"),

    (45, "スマホ: タッチターゲット 44px + 入力欄改善", """## 目的
ユーザー向けチャット UI のモバイル操作性を WCAG 寄りに改善。

## 現状の問題
| 要素 | 現状 | 目標 |
|------|------|------|
| 送信ボタン | 60×32px | min 44×44px |
| #messageInput | min 31px | min 44px |
| .button-group | 横スクロール | 2列折り返し |

## 対象ファイル
- `static/css/main.css`（768px/480px ブレークポイント）
- `templates/index.html`

## 工数: **8–16h** | 親: #45
※ #47 は管理画面のみ""", ["ui", "enhancement", "P2"], "2026-Q2 Core"),

    (46, "ストリーム: dead code 整理（renderStreamingMedicineCards）", """## 目的
ストリーム関連の未使用・dead code を整理し、#54 方針実装の前提を整える。

## 現状
- `renderStreamingMedicineCards` — 定義あるが SSE `cards` ハンドラから**未呼び出し**
- `recommendationSseBulkMode` — cards 後に advice 抑制
- インライン style 多用（#51 と重複）

## 実装（#61 ADR 後）
1. ADR で「cards 到着時に部分表示するか」決定
2. 使うなら `cards` ハンドラから呼び出し
3. 使わないなら関数削除 + テスト更新

## 工数: **4–8h** | 親: #46 | 依存: #61""", ["stream", "enhancement", "P1"], "2026-Q2 Core"),

    (55, "LINE: Rich Menu 実装", """## 目的
LINE 友だち追加時・トーク画面下部に Rich Menu を表示。

## メニュー案
- 症状相談を始める
- このツールについて
- 終了

## 工数: **16–24h** | 月額: $0 | 親: #55
## 優先度: P2（#57 本番後でも可）""", ["line", "enhancement", "P2"], "2026-Q2 Core"),

    (55, "LINE: Messaging API sandbox 自動 smoke テスト", """## 目的
#56 手動 E2E を補完する自動 smoke テスト（可能な範囲）。

## スコープ
- Flex 生成の snapshot テスト（既存 `test_line_flex_*`）
- （任意）LINE sandbox への統合テスト — API トークン要

## 工数: **8–16h** | 親: #55 | 関連: #56, #63""", ["line", "enhancement", "P2"], "2026-Q2 Core"),

    (27, "医薬品画像: Web カルーセル UI", """## 目的
Web チャットに推奨医薬品のパッケージ画像カルーセルを表示。

## 現状
- LINE: `flex_messages.py` は hero URL 対応（#70 ingest 待ち）
- Web: `main.js` はテキストリストのみ

## 参照
- `docs/未踏/docs/carousel_mockup.html`

## 工数: **16–24h** | 親: #27 | 依存: #70 データ

## 受け入れ条件
- [ ] 推奨 Top3 に画像表示（またはプレースホルダー）""", ["data", "ui", "enhancement", "P2"], "2026-Q3 Comparison"),
]


def run(cmd: list[str]) -> str:
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    if r.returncode != 0:
        print(r.stderr or r.stdout, file=sys.stderr)
        raise SystemExit(r.returncode)
    return (r.stdout or "").strip()


def gh(*args: str) -> str:
    return run(["gh", *args, "--repo", REPO])


def create_issue(title: str, body: str, labels: list[str]) -> int:
    p = Path(tempfile.gettempdir()) / f"gh_sub_{abs(hash(title))}.md"
    p.write_text(body + FOOTER, encoding="utf-8")
    cmd = ["gh", "issue", "create", "--repo", REPO, "--title", title, "--body-file", str(p)]
    for lb in labels:
        cmd.extend(["--label", lb])
    out = run(cmd)
    p.unlink(missing_ok=True)
    return int(out.rstrip("/").split("/")[-1])


def node_id(number: int) -> str:
    return gh("issue", "view", str(number), "--json", "id", "-q", ".id")


def add_sub(parent: int, child: int) -> None:
    pid, cid = node_id(parent), node_id(child)
    q = (
        "mutation($p: ID!, $c: ID!) { addSubIssue(input: { issueId: $p, subIssueId: $c }) "
        "{ subIssue { number title } } }"
    )
    run(["gh", "api", "graphql", "-H", "GraphQL-Features: sub_issues",
         "-f", f"query={q}", "-f", f"p={pid}", "-f", f"c={cid}"])
    print(f"  linked #{parent} <- #{child}")


def main() -> None:
    created: dict[str, int] = {}
    print("=== Create sub-issues ===")
    for parent, title, body, labels, milestone in SUB_ISSUES:
        n = create_issue(title, body, labels)
        created[title] = n
        add_sub(parent, n)
        gh("issue", "edit", str(n), "--milestone", milestone)
        print(f"  #{n} {title} -> #{parent}")

    gh("issue", "comment", "73", "--body",
       "本 issue は #68 の fixture 作成を包含します。#68 は match@3 推奨テスト、本 issue は routing/red_team も含む包括的 fixture 整備です。")

    n71_body = f"""## 追記（2026-06-11 新規 issue）

| # | タイトル | 優先度 |
|---|----------|--------|
| #72 | CI: GitHub Actions | P1 |
| #73 | fixture 整備 | P1 |
| #74 | セキュリティ本番設定 | P1 |
| #75 | Concierge エピック | P2 |
| #76 | /health + 監視 | P2 |

新規 sub-issue: {', '.join(f'#{n}' for n in created.values())}"""
    gh("issue", "comment", "71", "--body", n71_body)
    subprocess.run(["gh", "issue", "edit", "53", "--repo", REPO, "--add-label", "duplicate"], check=False)

    print("=== Summary ===")
    print(json.dumps(created, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
