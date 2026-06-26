# インフラ・HTTP エラー分析（infra_errors）

## 対象メタデータ

| 項目 | 値 |
|------|-----|
| 環境 | **medicine-recommend-dev** |
| 期間 | 2026-06-25 05:05 UTC 〜 2026-06-26 07:39 UTC（約 26.5 時間） |
| ログ件数 | 41,402 |
| デプロイ commit | `a7455d2`（全リビジョン共通） |
| リビジョン | 00123 → 00129（期間中 7 リビジョン、計 13 回の切替イベント） |
| 重大度カウント | ERROR 27 / WARNING 5 |

---

## エグゼクティブサマリ（最大 5 点）

- **ユーザー向け HTTP 503 は 0 件**。期間中の HTTP 4xx/5xx は合計 13 件のみで、大半は管理画面・ノイズ系。
- **🔴 管理画面の薬剤師手動返信が 8 連続 500**（`POST /api/main_manual_reply_queue`、2026-06-25 15:39 UTC）。原因はデプロイ済み `a7455d2` に `get_line_channel_access_token` の import 欠落（`NameError`）。ローカルには未デプロイの修正あり。
- **🟡 EpisodeSummaryAgent が TypeError**（2026-06-25 15:33 UTC）。`append_consultation_summary()` に未対応の `episode_id` 引数を渡している API 不整合。要約保存は失敗するが、例外は catch されユーザー応答は継続。
- **🟢 デプロイ時 SIGTERM 12 件は正常なロールアウトノイズ**。リビジョン切替直後（±30 秒）に旧リビジョン Worker へ SIGTERM。HTTP 503 とは無関係。
- **🟢 404/405 は無害**。`apple-touch-icon` 404（ブラウザ自動取得）、`GET /line/webhook` 405（POST 専用エンドポイントへの誤 GET）。

---

## デプロイ・リビジョンタイムライン

| 時刻 (UTC) | リビジョン | 備考 |
|------------|-----------|------|
| 05:05:32 | 00123-bpf | ログ期間開始 |
| 05:37:32 | 00124-gjq | SIGTERM @ 05:37:55（旧 00123） |
| 06:22:24 | 00125-jw2 | SIGTERM @ 06:22:51（旧 00124） |
| 06:24:16 | 00126-fln | SIGTERM @ 06:24:41（旧 00125） |
| 07:05:01 | 00127-klm | SIGTERM @ 07:05:21（旧 00126）。以降メイン稼働リビジョン |
| 16:41:53 | 00128-zqr | SIGTERM @ 16:42:18（旧 00127） |
| 16:55:13 | 00129-v9q | SIGTERM @ 16:55:31（旧 00128）。期間後半の支配リビジョン |

ログ件数比率: 00129-v9q (20,978) > 00127-klm (15,651) > 00124-gjq (2,135) > その他。

---

## 所見詳細

### 1. 管理画面手動返信 API の 500 連発 🔴 critical

**深刻度**: 🔴 critical（管理オペレーション不能。エンドユーザー向けチャット本体は別経路）

**時刻・証拠**:
- HTTP 500 × 8: `2026-06-25T15:39:47` 〜 `15:39:54` UTC（JST 00:39）
- リビジョン: `medicine-recommend-dev-00127-klm`
- セッション ID: `1782074044488131856187`
- エラーログ: `[ERROR] エラー詳細ログ [session_id: 1782074044488131856187] [type: NameError]`
- スタックトレース:
  ```
  File "/app/src/handlers/line/line_admin_manual_reply.py", line 66, in apply_admin_manual_reply
    elif not get_line_channel_access_token():
  NameError: name 'get_line_channel_access_token' is not defined
  ```
- ユーザー向け表示メッセージ: 「申し訳ございません。システムエラーが発生しました。管理者に連絡してください。」

**コード根拠**:
- デプロイ commit `a7455d2` の `line_admin_manual_reply.py` には **import が無い**（67 行目で関数を参照するのみ）。
- 現行ワーキングツリーには `from config.line_config import get_line_channel_access_token` が追加済み（**未デプロイ**）。
- 呼び出し元: `main.py` `api_main_manual_reply_queue_post` → `action == "reply"` → `apply_admin_manual_reply()`

**影響**: 管理画面からの薬剤師手動返信が約 7 秒間に 8 回リトライされすべて失敗。キューからの返信送信・LINE Push が完了しない。

**推奨アクション**:
1. `src/handlers/line/line_admin_manual_reply.py` の import 修正を **GitLab へ push → dev デプロイ**（ローカル修正済みならデプロイのみ）。
2. `tests/line/` に `apply_admin_manual_reply` の smoke テストを追加し、import 欠落を CI で検出。
3. 管理画面 `static/js/admin_chat.js` の連続 POST（8 回/秒）が意図的か確認。エラー時のリトライ抑制を検討。

---

### 2. EpisodeSummaryAgent の TypeError 🟡 warning

**深刻度**: 🟡 warning（バックグラウンド要約保存のみ。チャット応答は継続）

**時刻・証拠**:
- `2026-06-25T15:33:08` UTC
- リビジョン: `medicine-recommend-dev-00127-klm`
- メッセージ:
  ```
  TypeError: append_consultation_summary() got an unexpected keyword argument 'episode_id'
  File "/app/src/agents/episode_summary_agent.py", line 106
  ```

**コード根拠**:
- `episode_summary_agent.py:106` が `append_consultation_summary(line_sid, parsed, episode_id=episode_id)` を呼ぶ。
- `line_user_memory.py` の `append_consultation_summary()` は `(line_sid, summary)` のみ受け付け。
- `episode_id` 対応は `upsert_consultation_summary()` 側（`episode_id` kwarg あり）に実装済み。

**推奨アクション**:
1. `episode_summary_agent.py` で `upsert_consultation_summary` を直接呼ぶ、または `append_consultation_summary` に `episode_id` を透過する。
2. 既存テスト `tests/line/test_line_user_memory.py::test_upsert_consultation_summary_same_episode` を agent 経由でもカバー。

---

### 3. OpenAI API タイムアウト（httpx） 🟡 warning

**深刻度**: 🟡 warning（単発。HTTP 5xx には未変換）

**時刻・証拠**:
- `2026-06-25T07:30:46` UTC
- `Encountered httpx.TimeoutException` → OpenAI `_base_client.py` 経由の traceback（ERROR 2 件）
- 関連セッション入力: 「マルチエージェントってなに？」
- 同時刻の HTTP: `POST /line/webhook` は **200**（ユーザー向け障害なし）

**推奨アクション**:
- 再発頻度が低いため当面は監視継続。`performance_cost` グループと合わせて LLM タイムアウト設定・リトライ方針を確認。
- 頻発する場合は `src/services/chat_response_service.py` 周辺の timeout / fallback を調整。

---

### 4. デプロイ SIGTERM vs ユーザー向け 503 🟢 info

**深刻度**: 🟢 info（正常な Cloud Run ロールアウト）

**SIGTERM 証拠**（計 12 件）:

| 時刻 (UTC) | 旧リビジョン | メッセージ |
|------------|-------------|-----------|
| 05:37:55 | 00123-bpf | Worker (pid:3,66) was sent SIGTERM! |
| 06:22:51 | 00124-gjq | Worker (pid:2,3) was sent SIGTERM! |
| 06:24:41 | 00125-jw2 | Worker (pid:2,3) was sent SIGTERM! |
| 07:05:21 | 00126-fln | Worker (pid:2,3) was sent SIGTERM! |
| 16:42:18 | 00127-klm | Worker (pid:47,80) was sent SIGTERM! |
| 16:55:31 | 00128-zqr | Worker (pid:2,3) was sent SIGTERM! |

いずれも **新リビジョン切替の 10〜30 秒後** に旧リビジョン上で発生。Gunicorn の `[ERROR] Worker ... was sent SIGTERM!` は Cloud Run のインスタンス停止シグナルであり、単体では障害ではない。

**Worker exiting**（INFO、6 件）: 00127-klm / 00129-v9q 上でデプロイと無関係な時刻（09:51, 12:36, 12:55, 15:24, 06-26 05:25, 06:24）にも発生。インスタンススケールダウンまたはアイドル終了と推定。**HTTP 503 は 0 件**のため、これらはユーザー向け可用性低下に結びついていない。

**区別の目安**:
| シグナル | 典型パターン | ユーザー影響 |
|---------|-------------|-------------|
| SIGTERM @ リビジョン切替直後 | 旧 revision_name、複数 Worker 同時 | 通常なし（新リビジョンがトラフィック受信） |
| HTTP 503 | `httpRequest.status == 503` | **あり**（コールドスタート/容量不足） |
| 本ログ | SIGTERM 12、503 **0** | デプロイノイズのみ |

---

### 5. 無害な HTTP 4xx 🟢 info

| 時刻 (UTC) | Status | Path | 説明 |
|------------|--------|------|------|
| 05:40:51 | 404 | `/apple-touch-icon.png` 等 | Safari/Chrome のファビコン自動取得 |
| 06-26 02:49:33 | 404 | 同上 | 同上 |
| 10:28:55 | 405 | `GET /line/webhook` | POST 専用。ブラウザ直アクセスまたはヘルスチェック誤設定 |

対応不要。必要なら静的ファイル配置または WAF ルールでログノイズ削減。

---

### 6. 遅延エンドポイント（参考） 🟢 info

`POST /api/chat/stream`: 5 秒以上 15 件（平均 11.1s、最大 14.7s）。HTTP エラーではないが、タイムアウト境界に近い。詳細は `performance_cost` グループへ委譲。

---

## 優先度付き推奨アクション

| 優先度 | アクション | 対象 |
|--------|-----------|------|
| P0 | `get_line_channel_access_token` import 修正を dev へデプロイ | `src/handlers/line/line_admin_manual_reply.py` |
| P1 | `append_consultation_summary` / `upsert_consultation_summary` の API 整合 | `src/agents/episode_summary_agent.py`, `src/services/line_user_memory.py` |
| P2 | 手動返信 API の回帰テスト追加 | `tests/line/` |
| P3 | デプロイ時 SIGTERM アラートの閾値調整（リビジョン切替と相関する場合は抑制） | Cloud Monitoring / アラートポリシー |
| — | apple-touch-icon 404、GET /line/webhook 405 | 対応不要（info） |

---

## 結論

期間中のインフラ可用性は **概ね良好**（503 ゼロ、SIGTERM はデプロイノイズ）。ただし **管理画面の薬剤師手動返信がコードバグにより完全に失敗**しており、これが唯一のユーザー（管理者）影響のある 🔴 事象。ローカルに修正済みの import 欠落を速やかにデプロイすること。EpisodeSummaryAgent の TypeError は LINE メモリ要約の欠損リスクがあり、API 整合修正を推奨する。
