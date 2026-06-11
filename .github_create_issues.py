#!/usr/bin/env python3
"""Create recommended new issues and sub-issues."""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = "32Lwk/medicine-recommend-system"
FOOTER = "\n\n---\n_2026-06-11 調査に基づき自動作成。ロードマップ: #71_"


def run(cmd: list[str], check: bool = True) -> str:
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    if check and r.returncode != 0:
        print(r.stderr or r.stdout, file=sys.stderr)
        raise SystemExit(r.returncode)
    return (r.stdout or "").strip()


def gh(*args: str, check: bool = True) -> str:
    return run(["gh", *args, "--repo", REPO], check=check)


def write_tmp(text: str) -> Path:
    p = Path(tempfile.gettempdir()) / f"gh_new_{abs(hash(text))}.md"
    p.write_text(text, encoding="utf-8")
    return p


def create_issue(title: str, body: str, labels: list[str]) -> int:
    bf = write_tmp(body + FOOTER)
    cmd = ["gh", "issue", "create", "--repo", REPO, "--title", title, "--body-file", str(bf)]
    for lb in labels:
        cmd.extend(["--label", lb])
    out = run(cmd)
    bf.unlink(missing_ok=True)
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


def edit_labels(number: int, labels: list[str]) -> None:
    gh("issue", "edit", str(number), "--add-label", ",".join(labels))


def edit_milestone(number: int, milestone: str) -> None:
    gh("issue", "edit", str(number), "--milestone", milestone)


# ─── Top-level issues ───

TOP_LEVEL = [
    (72, "CI: GitHub Actions + pytest 自動実行", ["infra", "enhancement", "P1"], "2026-Q2 Core", """## 目的
PR / push 時に `pytest` を自動実行し、退行を防止する。

## 背景
- `.github/workflows/` が存在しない（レビュー報告書 T1）
- `sample_cases.jsonl` 等の欠落が CI で検出されない

## 実装手順
1. `.github/workflows/ci.yml` 作成
2. Python 3.10 + `pip install -r requirements.txt` + pytest
3. 初期対象: `tests/line/`, `tests/api/test_sse_emit.py`, `tests/core/`
4. fixture 欠落時は skip ではなく **#73 完了後に必須化**
5. （任意）カバレッジ artifact

## コスト・効果

| 項目 | 値 |
|------|-----|
| 工数 | **8–16h** |
| 月額 | $0（GitHub Actions 無料枠） |
| 効果 | PR ごとの退行検出、#68 golden の前提 |

## 受け入れ条件
- [ ] PR で pytest が自動実行される
- [ ] main ブランチ push で実行される
- [ ] 失敗時にマージブロック（branch protection 設定は別途）

## 関連
- 前提/並行: #73 fixture 整備
- ロードマップ: #71"""),

    (73, "fixture 整備: golden / routing / red_team", ["infra", "enhancement", "P1"], "2026-Q2 Core", """## 目的
テストが参照する fixture ファイルを整備し、CI・回帰テストの基盤を完成させる。

## 欠落ファイル

| ファイル | 参照テスト | 現状 |
|----------|-----------|------|
| `tests/fixtures/golden/sample_cases.jsonl` | `test_golden_regression.py` | **欠落**（schema のみ） |
| `tests/fixtures/routing/routing_golden.jsonl` | `test_routing_golden.py` | **欠落** |
| `tests/fixtures/safety/red_team.jsonl` | `test_safety_regression.py` | **欠落** |

## 実装手順
1. `sample_cases.jsonl` — 40件（P16/E10/A6/Em4/O4）、#68 と共同
2. `routing_golden.jsonl` — triage ルーティング 10+ 件
3. `red_team.jsonl` — プロンプトインジェクション・緊急誤判定 5+ 件
4. `pytest` 全パス確認
5. #72 CI に組み込み

## コスト・効果

| 項目 | 値 |
|------|-----|
| 工数 | **16–24h** |
| 効果 | Phase0 出口条件、安全回帰の自動化 |

## Sub-issues（#31 配下にもリンク）
- 本 issue が親、#31/#68 が内容重複する場合は #68 をクローズ候補に

## 受け入れ条件
- [ ] 3 fixture ファイルがリポジトリに存在
- [ ] 対応 pytest が skip せず実行可能

## 関連: #68, #72, #31"""),

    (74, "セキュリティ: 本番必須設定（SECRET_KEY / CORS / ADMIN）", ["enhancement", "P1"], "2026-Q2 Core", """## 目的
本番環境でのセキュリティ設定を必須化し、デフォルト値運用を防ぐ。

## 背景（レビュー報告書 S1/S2/S4）
| 項目 | リスク |
|------|--------|
| `ADMIN_PASSWORD` デフォルト | 管理画面不正アクセス |
| `SECRET_KEY` 弱い/未設定 | セッション改ざん |
| CORS 本番 URL 未登録 | または過剰許可 |

## 実装手順
1. 起動時チェック: `APP_ENV=production` で必須 env 未設定なら **fail fast**
2. CORS に Cloud Run / カスタムドメイン URL を追加
3. `.env.example` に本番必須項目を明記
4. `docs/security/` にチェックリスト追記

## コスト・効果

| 項目 | 値 |
|------|-----|
| 工数 | **8–16h** |
| 効果 | 本番リリース（#57 LINE）の前提条件 |

## 受け入れ条件
- [ ] production で SECRET_KEY/ADMIN 未設定時に起動失敗
- [ ] CORS が本番ドメインのみ許可
- [ ] ドキュメント更新

## 関連: #57 本番ロールアウト"""),

    (75, "Concierge エピック（トリアージ統合・意図分類）", ["epic", "enhancement", "P2"], "2026-Q3 Comparison", """## 目的
Concierge（挨拶・メタ質問・店舗案内等）機能の継続改善をエピックとして管理。

## 現状（2026-06-11 CHANGELOG）
| 機能 | 状態 |
|------|------|
| 第二段階トリアージ省略 | ✅ 実装済み |
| `concierge_intent` / emergency 除外 | ✅ |
| Concierge テスト群 | ✅ `tests/concierge/` |
| **専用 issue** | ❌ これまでなし |

## 残タスク候補
- [ ] Concierge 意図の golden 追加（routing_golden 連携）
- [ ] LINE 向け Concierge Flex 最適化
- [ ] 多言語 Concierge 応答
- [ ] `docs/ARCHITECTURE_MULTI_AGENT.md` に Concierge 経路追記

## コスト・効果

| 項目 | 値 |
|------|-----|
| 工数 | 継続的（各 8–16h） |
| 優先度 | P2（LINE/ストリーム後） |

## 関連ファイル
- `src/agents/concierge_agent.py`
- `src/services/concierge_orchestrator.py`
- `src/services/llm_triage.py`"""),

    (76, "運用: /health エンドポイント + 監視アラート", ["infra", "enhancement", "P2"], "2026-Q2 Core", """## 目的
Cloud Run のヘルスチェックと障害検知を整備する。

## 背景（レビュー報告書 O4）
- 明示的 `/health` または `/ready` が不明
- 障害検知が遅れる可能性

## 実装手順
1. `GET /health` — DB 接続確認（軽量）
2. `GET /ready` — アプリ起動完了
3. Cloud Run の liveness/readiness プローブ設定
4. （任意）Cloud Monitoring アラート（5xx 率）

## コスト・効果

| 項目 | 値 |
|------|-----|
| 工数 | **8h** |
| 月額 | $0–10（Monitoring） |
| 効果 | #57 本番運用の信頼性向上 |

## 受け入れ条件
- [ ] `/health` が 200 を返す
- [ ] Cloud Run プローブ設定済み

## 関連: #57, #58"""),
]

SUB_ISSUES = [
    # (parent, title, body, labels)
    (31, "安全回帰: red_team.jsonl 作成", """## 目的
`tests/fixtures/safety/red_team.jsonl` を作成し、安全回帰テストを有効化。

## 対象テスト
`tests/integration/test_safety_regression.py`

## ケース例（5件以上）
- プロンプトインジェクション → Physical に流れない
- 緊急ワード誤判定 → 挨拶が Emergency にならない
- 禁忌薬要求 → 推奨されない

## 工数: **8–16h** | 親: #31 | 関連: #73""", ["scoring", "enhancement", "P1"]),

    (31, "ルーティング golden: routing_golden.jsonl 作成", """## 目的
`tests/fixtures/routing/routing_golden.jsonl` を作成。

## 対象テスト
`tests/routing/test_routing_golden.py`

## ケース例（10件以上）
- Physical / Ask / Emotional / Emergency / Other
- Concierge 挨拶 → Other + concierge_intent
- 比較質問 → （将来）medicine_comparison

## 工数: **8–16h** | 親: #31 | 関連: #73, #75""", ["scoring", "enhancement", "P1"]),

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

## 工数: **4h** | 優先度: **P1** | 親: #48 | ブロッカー: #64""", ["comparison", "bug", "P1"]),

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
※ #47 は管理画面のみ""", ["ui", "enhancement", "P2"]),

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

## 工数: **4–8h** | 親: #46 | 依存: #61""", ["stream", "enhancement", "P1"]),

    (55, "LINE: Rich Menu 実装", """## 目的
LINE 友だち追加時・トーク画面下部に Rich Menu を表示。

## メニュー案
- 症状相談を始める
- このツールについて
- 終了

## 工数: **16–24h** | 月額: $0 | 親: #55
## 優先度: P2（#57 本番後でも可）""", ["line", "enhancement", "P2"]),

    (55, "LINE: Messaging API sandbox 自動 smoke テスト", """## 目的
#56 手動 E2E を補完する自動 smoke テスト（可能な範囲）。

## スコープ
- Flex 生成の snapshot テスト（既存 `test_line_flex_*`）
- （任意）LINE sandbox への統合テスト — API トークン要

## 工数: **8–16h** | 親: #55 | 関連: #56, #63""", ["line", "enhancement", "P2"]),

    (27, "医薬品画像: Web カルーセル UI", """## 目的
Web チャットに推奨医薬品のパッケージ画像カルーセルを表示。

## 現状
- LINE: `flex_messages.py` は hero URL 対応（#70 ingest 待ち）
- Web: `main.js` はテキストリストのみ

## 参照
- `docs/未踏/docs/carousel_mockup.html`

## 工数: **16–24h** | 親: #27 | 依存: #70 データ

## 受け入れ条件
- [ ] 推奨 Top3 に画像表示（またはプレースホルダー）""", ["data", "ui", "enhancement", "P2"]),
]


def ensure_milestone(title: str, description: str, due_on: str) -> None:
    ms = json.loads(gh("api", "repos/32Lwk/medicine-recommend-system/milestones", check=False) or "[]")
    if any(m.get("title") == title for m in ms):
        return
    run(["gh", "api", "repos/32Lwk/medicine-recommend-system/milestones",
         "-f", f"title={title}", "-f", f"description={description}", "-f", f"due_on={due_on}"])


def main() -> None:
    created: dict[str, int] = {"top_72": 72, "top_73": 73, "top_74": 74, "top_75": 75}

    ensure_milestone("2026-Q3 Comparison", "Comparison, RAG, ingredient DB, Concierge", "2026-09-30T23:59:59Z")
    edit_milestone(75, "2026-Q3 Comparison")
    print("  #75 milestone -> 2026-Q3 Comparison")

    print("=== Create remaining top-level issues ===")
    for num_expected, title, labels, milestone, body in TOP_LEVEL:
        if num_expected in (72, 73, 74, 75):
            continue
        n = create_issue(title, body, labels)
        created[f"top_{num_expected}"] = n
        edit_milestone(n, milestone)
        print(f"  #{n} {title}")

    print("=== Create sub-issues ===")
    for parent, title, body, labels in SUB_ISSUES:
        n = create_issue(title, body, labels)
        created[title] = n
        add_sub(parent, n)
        if parent in (31, 48, 45, 46, 55, 27):
            if parent == 31:
                edit_milestone(n, "2026-Q2 Core")
            elif parent in (48, 27):
                edit_milestone(n, "2026-Q3 Comparison")
            elif parent in (45, 46, 55):
                edit_milestone(n, "2026-Q2 Core")
        print(f"  #{n} {title} -> #{parent}")

    # Link #73 as related to #68 - add comment
    if "top_73" in created:
        n73 = created["top_73"]
        gh("issue", "comment", str(n73), "--body",
           f"本 issue は #68 の fixture 作成を包含します。#68 は match@3 推奨テスト、本 issue は routing/red_team も含む包括的 fixture 整備です。")

    # Update #71 roadmap
    n71_body_add = f"""

## 追記（2026-06-11 新規 issue）

| # | タイトル | 優先度 |
|---|----------|--------|
| #{created.get('top_72', '?')} | CI: GitHub Actions | P1 |
| #{created.get('top_73', '?')} | fixture 整備 | P1 |
| #{created.get('top_74', '?')} | セキュリティ本番設定 | P1 |
| #{created.get('top_75', '?')} | Concierge エピック | P2 |
| #{created.get('top_76', '?')} | /health + 監視 | P2 |

新規 sub-issue: ask_agent 修正、red_team、routing_golden、タッチターゲット、dead code、Rich Menu 等。
"""
    # Append to #71 via comment instead of editing full body
    gh("issue", "comment", "71", "--body", n71_body_add.strip())

    # #53 duplicate label
    gh("issue", "edit", "53", "--add-label", "duplicate", check=False)

    print("=== Summary ===")
    print(json.dumps(created, ensure_ascii=False, indent=2))
    print("Done.")


if __name__ == "__main__":
    main()
