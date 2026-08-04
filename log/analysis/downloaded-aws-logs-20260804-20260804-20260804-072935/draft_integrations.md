# Integrations グループ（ドラフト）

**ソース**: `downloaded-aws-logs-20260804-20260804-20260804-072935.json`  
**環境**: AWS ECS staging — `/ecs/medicine-recommend`（ap-northeast-1）  
**期間**: 2026-08-04T07:28:02Z ～ 2026-08-04T07:29:31Z（**168 エントリ / 約 89 秒**）  
**深刻度内訳**: INFO 144 / DEBUG 22 / WARNING 1 / ERROR 1  
**ECS log stream**: 3（`ecs/Main/*` ×3 — タスク並行稼働）

---

## エグゼクティブサマリー

- **LINE Webhook は本窓口に無し**: webhook リクエスト 0・テキストメッセージ 0・`job_lock_events` 0。唯一のセッションは `channel: web`。
- **Neon (PostgreSQL) は正常観測**: 本窓口に SSL 切断・再接続失敗・Neon タイムアウトは無し。`PIPELINE_PERF` 上の `session_db_read` は **2.33 ms**、`session_db_source: db` でセッション読み取り成功。
- **`medicine_information_qa` 120s タイムアウトが 1 件**: `product_image_fast_path_timeout`（約 524,788 ms）がパイプライン全体の **99.9%** を占め、統合レイヤの主要ボトルネック。Neon / LINE 起因ではない。
- **OpenAI API は到達・応答成功**: 窓口末尾の `chat/completions` は HTTP 200（約 4 秒）。`misc_signals.openai_errors` の大半は DEBUG 成功ログの誤分類。
- **その他外部連携は未発火または観測不足**: Comprehend Medical / Redis / Budget / Moderation / Gunicorn 再起動 / 緊急 dispatch の記録なし。デプロイ revision 変更も無し（短窓口のため）。

---

## LINE Webhook

### HTTP 統計

| 指標 | 値 |
|------|-----|
| リクエスト数 | **0** |
| ステータス分布 | （記録なし） |
| latency 統計 | （記録なし） |
| テキストメッセージ | **0** |
| `job_lock_events` | **0** |

### 所見

- 約 89 秒の差分窓口で **LINE 経由トラフィックは存在しない**。
- Web チャネルの単一セッション（`1785827858215313801801`）のみ。LINE 署名検証・Webhook 去重・非同期 200 返却の評価データは本窓口では得られない。

**深刻度**: 🟢 info（LINE 未利用のため評価対象外）

### 推奨アクション（LINE）

| 優先度 | アクション |
|--------|-----------|
| 🟢 info | staging LINE E2E（Webhook URL・署名・去重）を別窓口で実施。本窓口 webhook 0 件のため判定不可 |

---

## DB / Neon

### サマリー

| 項目 | 結果 |
|------|------|
| `db_neon.json` 件数 | **7**（※ 内容は OpenAI / タイムアウトログ — Neon 本体ログの誤分類） |
| 接続プール作成 / DB 初期化 | 本窓口に明示ログなし |
| SSL 切断 / 再接続失敗 | ❌ なし |
| Neon タイムアウト / 致命接続失敗 | ❌ なし |
| セッション DB 読み取り（PIPELINE_PERF） | ✅ **2.33 ms**（`session_db_source: db`） |

### パターン

1. **DB は統合ボトルネックではない**: `PIPELINE_PERF` breakdown では `session_db_read` が 2.33 ms と極小。`after_get_session_db`（381 ms）以降の LLM・画像 fast path が支配的。
2. **`db_neon.json` のパーサ誤分類**: top_patterns はすべて OpenAI `chat/completions` DEBUG ログおよび `medicine_information_qa timeout`。Neon 接続・プール・SSL 関連の行は本窓口に抽出されていない。
3. **セッション永続化は機能**: `counseling_detail` が正常に出力されており、DB 読み書き経路は少なくともこのセッションで動作。

### エビデンス（タイムスタンプ）

| 時刻 (UTC) | イベント | 証拠 |
|------------|----------|------|
| `2026-08-04T07:29:25Z` | セッション DB 読み取り完了 | `PIPELINE_PERF` — `session_db_read: 2.33`, `session_db_source: db` |
| `2026-08-04T07:29:25Z` | counseling_detail 出力 | `counseling_detail` JSON（`user_sessions.json`） |

**深刻度**: 🟢 info（DB 可用性に問題の兆候なし）

### 推奨アクション（DB）

| 優先度 | アクション |
|--------|-----------|
| 🟢 info | パーサ改善: `db_neon.json` 抽出条件を Neon / psycopg2 / `database.py` キーワードに限定し OpenAI ログ混入を防止 |
| 🟢 info | 長窓口分析で SSL 切断・`channel_binding` 警告の再確認（本窓口は 89 秒のためデータ不足） |

---

## その他シグナル（misc_signals）

### OpenAI API

| 指標 | 値 |
|------|-----|
| `misc_signals.openai_errors` 件数 | **8** |
| 実 API エラー（rate limit / 5xx） | ❌ なし |
| 成功呼び出し（DEBUG 200 OK） | ✅ `2026-08-04T07:29:18–22Z` — `POST https://api.openai.com/v1/chat/completions` |
| LLM コスト（参考） | **0.13 円 / 3 呼び出し**（`llm_cost.json`） |

**所見**: 窓口末尾の OpenAI 呼び出しは NRT 経由 Cloudflare で **200 OK**（約 4 秒）。同時刻帯に `medicine_information_qa timeout after 120s`（ERROR）が 1 件 — API 到達失敗ではなく、**アプリ内 120s タイムアウト**（画像 fast path 待ちと整合）。

**深刻度**: 🟡 warning（タイムアウト 1 件）/ 🟢 info（API 到達性）

### `medicine_information_qa` タイムアウト

| 指標 | 値 |
|------|-----|
| ERROR 件数 | **1** |
| メッセージ | `medicine_information_qa timeout after 120s sid=1785827858215313801801` |
| 時刻 (UTC) | `2026-08-04T07:29:25.053Z` |
| 関連 PIPELINE_PERF | `total_ms: 525,189` — `product_image_fast_path_timeout: 524,787.79` |

**所見**: パイプライン全体の約 **8.75 分**のうち、画像 fast path タイムアウトが **524.8 秒（99.9%）** を占有。DB（2 ms）・OpenAI（~4 s）・security（~5.9 s）ではなく、**製品画像 fast path 統合**がボトルネック。`counseling_detail` は同一時刻帯に出力済み — ユーザー応答は到達している可能性が高い（詳細は Wave B 委譲）。

**深刻度**: 🟡 warning

### Emergency（緊急事案検出）

| 指標 | 値 |
|------|-----|
| `misc_signals.emergency` 件数 | **1** |
| 内容 | `counseling_detail` JSON（比較質問「ロキソニンとバファリンとカロナールでおすすめは？」） |
| `Emergency dispatch` / `sage_emergency` ルーティング | ❌ なし |

**所見**: 緊急検出フローの発火ログではなく、**counseling 完了ログ**が `emergency` バケットに誤分類。緊急事案は本窓口で未観測。

**深刻度**: 🟢 info

### `duplicate_triage`

| 指標 | 値 |
|------|-----|
| 件数 | **1** |
| 内容 | `PIPELINE_PERF` WARNING（`total_ms: 525,189`） |

**所見**: 重複 triage スキップではなく **パイプライン性能ログ**のキーワード `triage` マッチによる誤分類。

**深刻度**: 🟢 info（パーサノイズ）

### 本窓口で未観測の統合

| カテゴリ | 件数 | 備考 |
|----------|------|------|
| Gunicorn / ECS 再起動 | 0 | デプロイ revision 変更も 0 |
| AWS Comprehend Medical | 0 | |
| Redis キャッシュ | 0 | |
| Budget / Moderation | 0 | |
| HTTP 4xx/5xx（`errors_http.json`） | 0 | |

**深刻度**: 🟢 info（短窓口のため「未発火」と「観測不足」の区別に注意）

### HTTP 外部連携エラー（参考）

`errors_http.json`: 4xx/5xx **0 件**。text_errors **1 件**（上記 `medicine_information_qa timeout`）。

---

## 優先アクション（統合）

| 優先度 | カテゴリ | アクション | 根拠 |
|--------|----------|-----------|------|
| 🟡 warning | アプリ | **`product_image_fast_path` 120s タイムアウトを調査** — 524.8 s 待ちがパイプライン全体を支配 | `PIPELINE_PERF` + ERROR 1 件 |
| 🟡 warning | アプリ | `medicine_information_qa` の 120s タイムアウトと fast path の関係をコード確認（並行処理・キャンセル未実装の可能性） | `errors_http.json` + `pipeline_perf.json` |
| 🟢 info | パーサ | `db_neon.json` / `openai_errors` / `emergency` / `duplicate_triage` の抽出条件見直し | OpenAI DEBUG・counseling_detail・PIPELINE_PERF の誤分類 |
| 🟢 info | LINE | staging LINE E2E を別窓口で実施 | webhook 0 件 |
| 🟢 info | Neon | 長窓口で SSL 切断・`channel_binding` 警告の定期確認 | 本窓口 89 秒では DB ログ不足 |

---

## 参照

| 領域 | パス |
|------|------|
| セクション JSON | `log/analysis/downloaded-aws-logs-20260804-20260804-20260804-072935/sections/` |
| パイプライン性能 | `sections/pipeline_perf.json` |
| LLM コスト | `sections/llm_cost.json` |
| HTTP / text エラー | `sections/errors_http.json` |
| DB プール・初期化 | `src/services/database.py` |
| ログ抽出 | `src/analysis/aws_cloudwatch_log_parser.py` |

---

*Integrations ドラフト — infra_errors / performance_cost / conversation_quality とのマージ時に `product_image_fast_path_timeout`・PIPELINE_PERF 等の重複を整理すること。個別セッション詳細は Wave B（`draft_session_1785827858215313801801.md`）に委譲。*
