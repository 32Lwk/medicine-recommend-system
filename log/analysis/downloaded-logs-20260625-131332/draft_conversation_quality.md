# Wave A — conversation_quality（横断サマリ）

**環境**: `medicine-recommend-dev`（dev）  
**ソース**: `downloaded-logs-20260625-131332.json`  
**期間**: 2026-06-24T18:08:04Z 〜 2026-06-25T04:13:20Z（エントリ 10,000 件）  
**リビジョン**: `00122-44q`（6,862） / `00123-bpf`（3,135） / commit `a7455d2`  
**解析日**: 2026-06-25

---

## Executive Summary（最大 5 項目）

- **セッション会話は CLI 上 0 件**（`quality_metrics.session_count=0`）だが、`chat_flow` には **10 trace / 2 セッション**（Web 1 + LINE 1）が存在。会話品質の自動評価（grade / intent mismatch）は **未実行**。
- **生ログには `counseling_detail` が 7 ブロック存在**するが、CLI が 0 件と報告。**パーサが `conversation_history` 内のネスト `{` を誤検出**し、JSON 再構成に失敗している（後述）。エクスポート欠落ではなく **解析パイプラインのギャップ**。
- 観測された会話は **Concierge メタ質問（Web）** と **LINE 絵文字・挨拶テスト** が中心。**Physical / 医薬品推奨フローは 0 件**。
- **意図ルーティングは trace 上問題なし**（capabilities / architecture / app_about / greeting / offensive emoji 等）。ただし **短い挨拶・複合絵文字文でフル LLM トリアージが走り、6〜9 秒**（🟡）。
- **セキュリティ検証は全 trace で safe=True**（score=0, warnings=0）。HTTP 4xx/5xx も 0。

---

## データ可用性と解析限界

| 指標 | 値 | 備考 |
|------|-----|------|
| `chat_flow.trace_count` | 10 | パイプライン trace は抽出済 |
| `session_conversations.session_count` | 0 | `counseling_detail` 依存 |
| `counseling_detail_count` (CLI) | 0 | **生ログでは 7 ブロック確認** |
| `physical_recommendation_log_events` | 0 | 推奨品質レビュー対象なし |
| `heuristic_mismatch_count` | 0 | セッション未構築のため参考にならない |

### counseling_detail 空 vs chat_flow あり — 原因

生ログ（`downloaded-logs-20260625-131332.json`）を直接確認すると、`カウンセリング詳細ログ [session_id: ...]` の直後に行分割 JSON（`log_type: counseling_detail`）が **7 回**出力されている。例:

- `2026-06-25T03:00:12Z` — session `1782074044488131856187`, user_input `このツールで何ができる？`
- `2026-06-25T03:10:28Z` — session `line:U20a3beee...`, greeting 応答

一方、`src/analysis/gcp_cloud_run_log_parser.py` の `_extract_multiline_json_objects` は **行が `{` のみのとき新ブロック開始**とし、**終了も単行 `}` 判定**のため、`conversation_history` 配列内の `{` / `}`（例: entry index 7323–7328）でブロックが **途中分割・上書き**される。結果として `counseling_detail` は 0 件、`build_session_conversations` も空になる。

**結論**: ログレベルや GCP エクスポートフィルタの欠落ではなく、**structured_logger の行分割 JSON + 浅い brace パーサ**の組み合わせ問題。Wave B セッション深掘りもこの修正なしでは `conversation_history` を復元できない。

---

## 横断 Findings

### 1. セッション会話・品質メトリクスが構築不能

**Severity**: 🔴 critical（分析ワークフロー）

**Evidence**:
- `quality_metrics.json`: `"session_count": 0`, `"counseling_detail_count": 0`
- `user_sessions.json`: `"sessions": []`, `"intent_mismatches": []`
- 生ログ grep: `counseling_detail` 7 ブロック、`standalone {` 行 33 件、パーサ成功 JSON 7 件（いずれも message 型、`counseling_detail` 0）

**影響**: ヒューリスティック grade、mismatch 検出、推奨 advisor フックがすべてスキップ。親エージェントの Wave B も session オブジェクトなし。

**推奨アクション**:
- `gcp_cloud_run_log_parser._extract_multiline_json_objects` を **brace depth 追跡**または **`log_type` ヘッダ行（`"log_type": "counseling_detail"`）起点**の再構成に改修
- 代替: `structured_logger._write_to_app_log` を **1 行 JSON（`json.dumps` compact）** 出力に変更し Cloud Logging 分割を回避

---

### 2. Concierge メタ質問ルーティング — Web セッション（正常）

**Severity**: 🟢 info

**Session**: `1782074044488131856187`（channel: web, `session_db_source: db`）

| 時刻 (UTC) | ユーザー入力 | Triage | Concierge intent | total_ms |
|------------|-------------|--------|------------------|----------|
| 03:00:03 | このツールで何ができる？ | Other / general_other (1.0) | capabilities | 8996 |
| 03:00:32 | 誰が答えた？ | Other / general_other (1.0) | architecture | 6601 |
| 03:02:55 | マルチエージェントってなに？ | Other / general_other (1.0) | architecture | 5586 |
| 03:03:30 | あんたについておしえて | Other / general_other (1.0) | app_about | 6117 |

**Evidence**:
- 全 trace で `ChatOrchestrator → handoff → OtherHandler`
- `concierge_agent.meta_*` LLM 1 回/trace（capabilities / architecture / app_about）
- 生ログ response 例（capabilities）: 市販薬案内・安全確認・店舗質問対応を説明 — メタ質問に適合

**所見**: 意図解決は一貫。性能は `concierge_build_payload` が 2.4〜3.5s 占める（性能グループへエスカレーション推奨）。

---

### 3. LINE 絵文字・挨拶 — ルートは妥当だがコスト・遅延が高い

**Severity**: 🟡 warning

**Session**: `line:U20a3beee49563dcd07bb3dd0fc1ca32c`（channel: line, 大半 `session_db_source: memory`）

| 時刻 (UTC) | 入力 | ルート | Triage | Intent | total_ms | 備考 |
|------------|------|--------|--------|--------|----------|------|
| 03:08:36 | `( > ·̫ <)👍🏻🌟` | emoji skip → フルトリアージ | Other (0.99) | null | 6141 | `emoji_route_skip_not_emoji_only`, LLM triage ×2 |
| 03:08:45 | 😄 | emoji route | — | — | 2977 | `emoji_intent.classify` のみ |
| 03:08:56 | 😭 | emoji → counseling | — | — | 9222 | `counseling_generator` + `counseling_followup.alt` |
| 03:09:09 | 😇 | emoji route | — | — | 2879 | classify のみ |
| 03:09:23 | 🖕 | offensive fast path | — | — | 1989 | `emoji_route_offensive`, LLM 0 |
| 03:10:21 | ああ | フルトリアージ → greeting | Other (0.99) | greeting | 8881 | `structural_intent=greeting`, LLM ×3 |

**Evidence**:
- `9f38282c`: breakdown `emoji_route_skip_not_emoji_only` → `after_triage` 3821ms ジャンプ（stage1+2）
- `007eb56d`: `reply_token_elapsed_ms: 9317` — LINE reply トークン上限（約 30s だが UX 上問題）
- `90847f91`（😭）: `emoji_route_done` 8234ms — counseling followup がボトルネック
- `eec5ea89`（🖕）: `emoji_route_offensive` で 81ms 以内に分岐 — **モデレーション設計どおり**

**所見**:
- 絵文字単体は emoji route で妥当。 **絵文字+テキスト複合**と **2 文字挨拶「ああ」** はフル triage + concierge が走り過剰。
- `chat_emoji_route.py` の `emoji_route_skip_not_emoji_only` は仕様どおりだが、LINE 実運用では **短い非症状発話の structural/greeting ショートカット**（`chat_concierge_route` の greeting 判定前倒し）を検討余地あり。

---

### 4. 医薬品推奨・カウンセリング本番フロー未観測

**Severity**: 🟢 info

**Evidence**:
- `quality_metrics.physical_recommendation_log_events: 0`
- `chat_flow` 全 10 trace の triage category が `Other` のみ（Physical / Emotional カテゴリの本番 triage なし）
- 😭 trace のみ `counseling_generator.main` — 絵文字感情ルート経由の軽量 counseling

**所見**: 本ログウィンドウは **dev 手動テスト**（Concierge FAQ + LINE emoji）が主。推奨アルゴリズム品質はこのエクスポートからは評価不可。

---

### 5. セキュリティ — 問題なし

**Severity**: 🟢 info

**Evidence** (`user_sessions.security_flags`):
- 10 件すべて `Security validation: score=0, safe=True, warnings=0`
- 時刻範囲 03:00:05 〜 03:10:21（chat trace と一致）
- offensive emoji（🖕）も safety gate を通過後、emoji 専用 offensive 分岐で処理（block ではなく soft intro）

---

## 意図ずれ（Intent Mismatch）横断レビュー

CLI の `intent_mismatches` は空。`chat_flow` trace ベースの **参考判定**（LLM 最終判定は Wave B / 生 counseling_detail 復元後に実施）:

| trace | ユーザー意図（推定） | システム intent | 判定 |
|-------|---------------------|-----------------|------|
| d5e8b30a | 機能説明 | capabilities | ✅ 一致 |
| b660c5b1 / 96c84af6 | 仕組み説明 | architecture | ✅ 一致 |
| 2420230e | ボット自己紹介 | app_about | ✅ 一致 |
| 9f38282c | リアクション（絵文字中心） | Other（triage） | 🟡 過剰だが有害ではない |
| 007eb56d | 挨拶 | greeting | ✅ 一致 |
| eec5ea89 | 攻撃的絵文字 | offensive path | ✅ 一致 |

**有意な意図ずれは trace 上検出されず。** ただし応答本文は `counseling_detail` 未復元のため **内容適合性は未検証**。

---

## チャネル別サマリ

| チャネル | trace 数 | 主なパターン | 平均 total_ms |
|----------|----------|-------------|---------------|
| web | 4 | Concierge meta Q&A | ~6,825 |
| line | 6 | emoji route / triage / greeting | ~5,365（offensive 除く） |

Web は DB セッション、LINE は memory セッションが多く、**同一ユーザーでも永続化経路が異なる**（設計どおりだが、長会話時のコンテキスト差に注意）。

---

## 推奨アクション（優先順）

1. 🔴 **`_extract_multiline_json_objects` 修正** — `counseling_detail` / `recommendation_detail` の復元を最優先。修正後 CLI 再実行で `session_count` と Wave B が有効化される。
2. 🟡 **短い挨拶・リアクションのトリアージ省略** — `ああ` 等で stage1+2（~4s）を避ける。`chat_post_pipeline` / `chat_concierge_route` で structural greeting 前倒し、または triage スキップ条件を追加。
3. 🟡 **複合絵文字メッセージ** — `( > ·̫ <)👍🏻🌟` 類は emoji+text ヒューリスティックで social/concierge 直行を検討（`chat_emoji_route.py`）。
4. 🟡 **LINE reply 遅延監視** — `slow_concierge_path: true` が 4/6 trace。`reply_token_elapsed_ms` > 8s をアラート化（性能グループと連携）。
5. 🟢 **次回エクスポート** — 医薬品推奨シナリオを含むログ取得で `physical_recommendation` 品質評価を実施。現エクスポートは dev スモークテストに偏る。

---

## 参照コード

- セッション構築: `src/analysis/session_conversation_analysis.py` → `build_session_conversations(counseling_details, chat_flow)`
- counseling ログ出力: `src/services/counseling/counseling_logger.py` → `log_counseling_detail`
- Concierge ログ: `src/handlers/chat/chat_concierge_route.py` → `_log_concierge_response`
- Emoji ルート: `src/handlers/chat/chat_emoji_route.py`

---

*Wave A conversation_quality — セッション別深掘りは Wave B に委譲。本ドラフトは横断サマリのみ。*
