# Local v2 Chat Test — Reference

## CLI: `scripts/local_v2_chat_test_runner.py`

### フラグ一覧

| フラグ | 型 | 既定 | 説明 |
|--------|-----|------|------|
| `--base-url` | str | `http://127.0.0.1:5000/` | テスト対象 URL（`V2_TEST_BASE_URL` で上書き可） |
| `--limit` | int | 0 | YAML シナリオ上限（0=全件 100）。smoke は 10 |
| `--use-gpt-user` | flag | off | GPT がユーザー発話を生成（`OPENAI_API_KEY` 必須） |
| `--skip-yaml` | flag | off | 静的 YAML をスキップ（gpt-scale のみ） |
| `--sessions` | int | 0 | GPT ペルソナセッション数（>0 で gpt-scale 有効） |
| `--min-chats` | int | 0 | GPT 合計ターン下限（0 なら gpt-scale 時 500） |
| `--report-suffix` | str | `v2` | 出力ファイル名の `{suffix}` 部分 |
| `--skip-metrics` | flag | off | ログ突合・IntentRouter メトリクスをスキップ |

### モードとコマンド

```powershell
# smoke（10 シナリオ）
python scripts/local_v2_chat_test_runner.py --limit 10 --report-suffix smoke

# yaml-only（100 シナリオ、GPT なし）
python scripts/local_v2_chat_test_runner.py --report-suffix yaml

# gpt-scale のみ（YAML スキップ）
python scripts/local_v2_chat_test_runner.py --skip-yaml --use-gpt-user --sessions 12 --min-chats 500 --report-suffix gpt

# combined full（下限・推奨）
python scripts/local_v2_chat_test_runner.py --use-gpt-user --sessions 12 --min-chats 500 --report-suffix full
```

`--sessions` または `--min-chats` > 0 のとき gpt-scale が有効。`--use-gpt-user` 無しでも自動有効化（WARN 出力）。

### 環境変数

| 変数 | 用途 |
|------|------|
| `OPENAI_API_KEY` | GPT ユーザーシミュレータ（`.env` から読込） |
| `V2_TEST_BASE_URL` | 既定 base URL |
| `V2_TEST_CHAT_TIMEOUT` | 1 ターンタイムアウト秒（既定 120） |
| `APP_ENV` | `development` で v2 自動 ON |
| `CHAT_PIPELINE_V2` | 明示 ON/OFF |

### 終了コード

| code | 条件 |
|------|------|
| 0 | `auto_pass >= 50%` |
| 1 | 合格率不足 |
| 2 | ヘルスチェック失敗 / API キー無し / ペルソナ空 / 結果 0 件 |

---

## 出力パス（`log/analysis/`）

日付 `YYYY-MM-DD` は実行日。

| パターン | 内容 |
|----------|------|
| `{date}_local_v2_chat_test_{suffix}.md` | メインレポート（**全トランスクリプト**） |
| `{date}_local_v2_chat_test_{suffix}.json` | `meta` + `metrics` + `results[]` |
| `{date}_local_v2_simulation_eval_{suffix}.md` | 意図評価・ログ突合サマリ |
| `{date}_local_v2_session_ids_{suffix}.json` | Admin 用 `sessions[]` インデックス |

エージェント任意追加:

| パターン | 内容 |
|----------|------|
| `{date}_local_v2_intent_review_{suffix}.md` | Wave B 深掘り（evaluation.md 準拠） |

### JSON スキーマ（session_ids）

```json
{
  "meta": { "date", "base_url", "started_at", "elapsed_sec", "scenario_count", "total_turns", "auto_pass", "use_gpt_user", "gpt_scale", "v2_enabled" },
  "sessions": [
    { "scenario_id", "session_id", "category", "persona_id", "turns", "auto_pass", "admin_url" }
  ]
}
```

---

## Post-run スクリプト

### `scripts/measure_pipeline_baseline.py`

```powershell
python scripts/measure_pipeline_baseline.py
python scripts/measure_pipeline_baseline.py --counseling-detail log/counseling_detail_log.jsonl
python scripts/measure_pipeline_baseline.py --log-dir log/analysis/downloaded-logs-*
```

主な KPI: `response_missing_rate_pct`, counseling_detail 件数。

### `scripts/measure_intent_router_shadow.py`

```powershell
python scripts/measure_intent_router_shadow.py
python scripts/measure_intent_router_shadow.py --json
```

主な KPI: `shadow_mismatch_rate_pct`, `dispatch_handled`, `shadow_by_primary_route`。

---

## サーバー起動

```powershell
# repo root、.venv 有効化後
python app.py
```

| 項目 | 値 |
|------|-----|
| 既定ポート | 5000（`PORT` env） |
| ヘルス | `GET /` → 200 |
| v2 有効化 | `APP_ENV=development` |

**禁止**: テスト完了後の `taskkill` / uvicorn 停止。

---

## v2 テストセッション（Admin 連携）

### サーバー側（`main.py`）

- `User-Agent` に `local-v2-chat-test` → `v2_local_test=True`
- `username = v2-test-{scenario_slug}`
- `X-V2-Test-Scenario` → `v2_test_scenario` フィールド

### 除外（本番集計）

- `session_manager.is_v2_local_test_session()` — クリーンアップ除外
- `database.py` — 一部クエリで `username NOT LIKE 'v2-test-%'`

### Admin UI

1. `/admin` を開く
2. セッション一覧サイドバー → 「**v2テストのみ**」チェック ON
3. セッション行に `v2テスト: {scenario_id}` バッジ
4. `session_ids_{suffix}.json` の ID を検索ボックスに貼り付け

---

## フィクスチャ

### `tests/fixtures/v2_local_chat_scenarios.yaml`

- 100 シナリオ、`category` + `wave` + `input` + `expect.primary_route`
- カテゴリ: session_ops, physical, physical_fever, concierge, concierge_followup, correction, counseling_context, emergency, security, store

### `tests/fixtures/v2_gpt_personas.yaml`

- 実 GCP ログパターン由来のペルソナ
- フィールド: `id`, `label`, `category`, `opening`, `goal`, `system`, `example_patterns`

---

## トラブルシュート

| 症状 | 対処 |
|------|------|
| `ERROR: ... に接続できません` | `python app.py` 起動、`--base-url` 確認 |
| `OPENAI_API_KEY not set` | `.env` にキー追加 or GPT OFF で yaml-only |
| `CHAT_PIPELINE_V2 が OFF` | `APP_ENV=development` を設定して再起動 |
| ポートずれ | `app.py` のログで実ポート確認 → `--base-url` |
| combined full が長い | バックグラウンド実行、進捗はターミナル `[yaml N/100]` / `[gpt N/12]` |
| counseling_detail 0 件 | v2 ルートで `counseling_detail` 出力設定を確認（CHAT_PIPELINE_V2.md） |

---

## 仕様ドキュメント

- `docs/dev/CHAT_PIPELINE_V2.md` — フラグ・Wave・ベースライン
- `docs/dev/CHAT_ROUTE_EXPECTATIONS.md` — 期待 route
- `tests/fixtures/expected_v2_diff.yaml` — 旧 pipeline 差分
