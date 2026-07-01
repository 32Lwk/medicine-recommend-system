---
name: local-v2-chat-test
description: >-
  Runs Chat Pipeline v2 local integration tests against app.py on :5000 via
  scripts/local_v2_chat_test_runner.py. Executes YAML scenarios and optional GPT
  user simulation, writes reports to log/analysis/, measures pipeline baseline
  and IntentRouter shadow metrics, and performs gcp-log-analysis-style per-session
  intent evaluation from counseling_detail and dialogue_route logs. Use when the
  user asks for v2 local chat test, CHAT_PIPELINE_V2 validation, GPT simulation,
  admin v2テスト review, intent alignment evaluation, or local v2 regression before deploy.
---

# Local v2 Chat Test (medicine-recommend)

ローカル限定。`app.py` + `scripts/local_v2_chat_test_runner.py` を軸に、Chat Pipeline v2 の統合テスト・意図評価・Admin 手動確認までを一連で実行する。

**GCP ログ解析**が必要な場合は別スキル [`gcp-log-analysis`](../gcp-log-analysis/SKILL.md) を使う。本スキルはローカルファースト。

## When to use

- `CHAT_PIPELINE_V2` / Wave 1a–1b のローカル回帰
- YAML 100 シナリオ + GPT ペルソナ長尺シミュレーション
- `log/analysis/*_local_v2_*` レポート生成と意図整合レビュー
- Admin「v2テストのみ」での手動確認前後

## Workflow overview

```
0. Pre-flight（毎回必須・ユーザー確認）
1. Server check  →  app.py :5000, APP_ENV=development, v2 ON
2. Run runner    →  local_v2_chat_test_runner.py
3. Metrics       →  measure_pipeline_baseline, measure_intent_router_shadow
4. Wave B eval   →  セッション別意図評価（evaluation.md）
5. Report        →  log/analysis/YYYY-MM-DD_local_v2_*（report_only、git commit しない）
6. Admin review  →  /admin → v2テストのみ
```

詳細 CLI・出力パス: [reference.md](reference.md)  
意図評価ルーブリック: [evaluation.md](evaluation.md)

---

## Step 0 — Pre-flight（毎回必須）

**実行前に必ずユーザーへ確認する。** 前回の設定を流用しない。

| 項目 | 確認内容 | 既定・下限 |
|------|----------|------------|
| **スケール** | smoke / yaml-only / gpt-scale / **combined full** | 下限は **combined full**（YAML 100 + GPT 12 セッション / 500+ ターン） |
| **コンテンツ重点** | 全カテゴリ or 特定（physical / concierge / session_ops / correction 等） | 全カテゴリ |
| **意図シナリオ** | 固定 YAML のみ / GPT ペルソナ追加 / 両方 | combined full 推奨 |
| **話し方・ペルソナ** | `v2_gpt_personas.yaml` から選択 or 全件 | 12 ペルソナ（gpt-scale 時） |
| **GPT シミュレータ** | ON（`OPENAI_API_KEY`）/ OFF | **ON**（`.env`） |
| **サーバー** | `app.py` 起動済みか、起動してよいか | `:5000` |
| **レポート suffix** | ファイル名識別子 | `full` / `v2` / ユーザー指定 |
| **GCP 併用** | dev ログ解析も必要か | 不要なら本スキルのみ |

ユーザーが「とりあえず」と言っても、**スケールは明示選択**を促す（未指定なら combined full を提案）。

---

## Step 1 — Server pre-flight

### 起動確認

```powershell
# repo root
python app.py
```

| チェック | 期待値 |
|----------|--------|
| URL | `http://127.0.0.1:5000/` が 200 |
| `APP_ENV` | `development`（`.env` 既定） |
| v2 | `CHAT_PIPELINE_V2` 未設定でも development では ON |
| `OPENAI_API_KEY` | GPT モード時は `.env` に設定 |

未起動なら **バックグラウンドで起動**してよい（ユーザー許可後）。ポート競合時は `app.py` が別ポートを選ぶ — runner の `--base-url` を合わせる。

### v2 テストセッションの仕組み（参照のみ）

- `User-Agent: local-v2-chat-test/2.0` → `username = v2-test-{scenario}`
- `X-V2-Test-Scenario` ヘッダでシナリオ ID を記録
- `session_manager.is_v2_local_test_session()` / DB で本番集計から除外
- Admin: サイドバー「**v2テストのみ**」フィルタ（`static/js/admin_chat.js`）

---

## Step 2 — Run test runner

repo root から `.venv` 有効化後:

### モード別コマンド

| モード | コマンド |
|--------|----------|
| **smoke** | `python scripts/local_v2_chat_test_runner.py --limit 10 --report-suffix smoke` |
| **yaml-only** | `python scripts/local_v2_chat_test_runner.py --report-suffix yaml` |
| **gpt-scale** | `python scripts/local_v2_chat_test_runner.py --skip-yaml --use-gpt-user --sessions 12 --min-chats 500 --report-suffix gpt` |
| **combined full**（下限） | `python scripts/local_v2_chat_test_runner.py --use-gpt-user --sessions 12 --min-chats 500 --report-suffix full` |

**combined full** の内訳:
1. YAML 100 シナリオ（`tests/fixtures/v2_local_chat_scenarios.yaml`）— `--skip-yaml` なし
2. GPT 12 ペルソナ × 約 42 ターン（500+ 合計）— `--sessions 12 --min-chats 500`

オプション:
- `--base-url http://127.0.0.1:PORT/` — ポートずれ時
- `--skip-metrics` — ログ突合スキップ（非推奨）
- カテゴリ絞り: runner にフィルタ無し → **smoke + 該当カテゴリ手動確認** or ユーザーと相談して `--limit` / ペルソナ subset

実行時間目安: combined full は **2–3 時間**（GPT API 依存）。バックグラウンド実行可。

### 終了コード

| code | 意味 |
|------|------|
| 0 | 自動合格 ≥ 50% |
| 1 | 合格率低 |
| 2 | サーバー未起動 / API キー無し / シナリオ 0 件 |

---

## Step 3 — Post-run metrics

テスト完了後、runner が生成したレポートの **直後** に実行:

```powershell
python scripts/measure_pipeline_baseline.py --counseling-detail log/counseling_detail_log.jsonl
python scripts/measure_intent_router_shadow.py --json
```

出力をエージェントが読み、最終サマリに要約を追記する（runner 内 `_run_auto_metrics` と重複可 — 手動再計測で鮮度確保）。

---

## Step 4 — Wave B 意図評価（ローカル）

`gcp-log-analysis` の Wave B と同型。**セッションごと**に深掘りする。

1. `log/analysis/YYYY-MM-DD_local_v2_session_ids_{suffix}.json` から `session_id` 一覧を取得
2. 各セッションについて [evaluation.md](evaluation.md) のルーブリックで評価
3. ソース:
   - `log/analysis/YYYY-MM-DD_local_v2_chat_test_{suffix}.md` — 完全トランスクリプト
   - `log/counseling_detail_log.jsonl` — 応答全文
   - `log/dialogue_route_shadow_log.jsonl` / `dialogue_route_dispatch_log.jsonl` — ルート
4. **Multitask**: セッション数が多い場合（>20）は `auto_pass=false` / REVIEW 優先で最大 20 セッションに Task サブエージェント（`run_in_background: true`）。残りは親がテーブル要約

評価の最終判定は **LLM（エージェント）** — runner の `auto_pass` は参考。

---

## Step 5 — 出力（report_only）

runner が自動生成:

| ファイル | 内容 |
|----------|------|
| `log/analysis/YYYY-MM-DD_local_v2_chat_test_{suffix}.md` | 完全トランスクリプト + メトリクス |
| `log/analysis/YYYY-MM-DD_local_v2_chat_test_{suffix}.json` | 機械可読結果 |
| `log/analysis/YYYY-MM-DD_local_v2_simulation_eval_{suffix}.md` | 意図評価サマリ |
| `log/analysis/YYYY-MM-DD_local_v2_session_ids_{suffix}.json` | Admin 用 ID 一覧 |

エージェント追加作業:
- Wave B 評価を `simulation_eval` に追記、または `log/analysis/YYYY-MM-DD_local_v2_intent_review_{suffix}.md` を新規作成
- エグゼクティブサマリ（5–10 行）をユーザーに報告

**Git**: `log/` は追跡対象だが **自動 commit / push しない**。ユーザー依頼時のみ。

---

## Step 6 — Admin 手動確認

1. [http://127.0.0.1:5000/admin](http://127.0.0.1:5000/admin) を開く
2. サイドバー「**v2テストのみ**」を ON
3. `session_ids_{suffix}.json` の ID で検索、または `v2-test` でフィルタ
4. シナリオ ID（`v2_test_scenario`）と会話内容を照合

---

## 厳守ルール

1. **テスト後に localhost を停止しない** — runner も「Server left running」と表示
2. **毎回 Step 0 でユーザーにスケール等を確認**
3. **下限スケールは combined full** — ユーザーが明示的に smoke/yaml-only を選んだ場合のみ縮小
4. **GPT シミュレータは既定 ON** — OFF はユーザー明示時のみ
5. **report_only** — 成果物は `log/analysis/` のみ、自動 git 操作なし
6. **本番 DB / GCP には触れない** — ローカル `APP_ENV=development` のみ

---

## フィクスチャ参照

| パス | 用途 |
|------|------|
| `tests/fixtures/v2_local_chat_scenarios.yaml` | 100 YAML シナリオ |
| `tests/fixtures/v2_gpt_personas.yaml` | GPT ペルソナ（実ログパターン） |
| `docs/dev/CHAT_PIPELINE_V2.md` | v2 仕様・フラグ |

カテゴリ例: `session_ops`, `physical`, `physical_fever`, `concierge`, `concierge_followup`, `correction`, `counseling_context`, `emergency`, `security`, `store`

---

## gcp-log-analysis との関係

| 本スキル | gcp-log-analysis |
|----------|------------------|
| ローカル HTTP テスト | GCP エクスポート JSON |
| runner がトランスクリプト生成 | CLI が session transcript 生成 |
| `counseling_detail` ローカル jsonl | 同上（Cloud Run ログ経由） |
| Wave B 意図評価（ローカル session_ids） | Wave B（GCP session_id） |

両方必要なとき: 本スキルでローカル回帰 → 別途 `gcp-log-analysis` で dev ログ比較。

---

## 関連スキル・ドキュメント

- [reference.md](reference.md) — CLI 全フラグ、環境変数、トラブルシュート
- [evaluation.md](evaluation.md) — 意図整合ルーブリック、Wave B 手順
- [gcp-log-analysis/SKILL.md](../gcp-log-analysis/SKILL.md)
- [medicine-recommendation-advisor/SKILL.md](../medicine-recommendation-advisor/SKILL.md) — OTC 推奨品質（physical セッション）

## レポート例

- `log/analysis/2026-06-29_local_v2_chat_test_full.md`
- `log/analysis/2026-06-29_local_v2_simulation_eval_full.md`
- `log/analysis/2026-06-29_local_v2_session_ids_full.json`
