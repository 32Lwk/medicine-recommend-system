# Safari SSE「処理中…」固定 — 修正・デプロイ・E2E 検証

**日時**: 2026-08-08  
**コミット**: `4c116b3` — fix: flush trailing SSE buffer on Safari and forward Worker POST bodies

---

## 原因（推定）

Safari（WebKit）では `fetch` + `ReadableStream` で SSE を読む際、**接続終了直前の最終チャンクに `\n\n` が含まれない**ことがある。  
`chat_sse.js` の `parseSseChunk` は `\n\n` 区切りのみイベント化するため、バッファに残った **`event: done` が未パース**のまま `onDone` が呼ばれ、UI が「処理中…」のままになる。

AWS 側は別件で Cloudflare Worker が POST ボディ未転送 → `/api/chat/stream` 422（前回解析）。同一コミットで Worker 修正も含む。

---

## 修正内容

| ファイル | 変更 |
|---------|------|
| `static/js/chat_sse.js` | ストリーム終了時に `forceFlush` で残バッファをパース |
| `workers/src/index.js` | 非 GET/HEAD リクエストの `body` を Origin に転送 |
| `scripts/test_chat_sse_parser.js` | パーサ単体テスト（新規） |

---

## デプロイ監視

| 環境 | 手段 | コミット | 結果 |
|------|------|----------|------|
| **GCP dev** | Cloud Build `040fb692-…` | `4c116b3` | **SUCCESS**（約 6 分） |
| **AWS staging** | CodePipeline `1b1d4815-…` | `4c116b3` | **Succeeded**（約 5 分） |
| **Cloudflare Worker** | `wrangler deploy` | — | **未実行**（`CLOUDFLARE_API_TOKEN` 未設定）。ただし curl/E2E で Worker 経由 POST 200 を確認 |

### デプロイ後確認

- GCP dev: `chat_sse.js?v=1786170701` に `forceFlush` / Safari コメントあり
- AWS `/health`: `git_commit: 4c116b3`
- GCP dev `/health` の `git_commit` 表示は既知問題で `0fd8593` のまま（インライン Cloud Build トリガーの `GIT_COMMIT` env 未更新）

---

## E2E 評価

```text
scripts/test_chat_sse_parser.js     PASS
scripts/test_sse_chat_e2e.py (GCP dev)  PASS  HTTP 200, done=True, 4.7s
scripts/test_sse_chat_e2e.py (AWS)      PASS  HTTP 200, done=True, 11.8s
```

---

## Safari 実機確認（ユーザー側）

Network タブ未確認のため、以下を Safari で再確認してください。

1. ハードリロード（キャッシュクリア）
2. メッセージ送信 → 「処理中…」が消え bot 応答が表示されること
3. まだ失敗する場合: Safari バージョン、コンソールエラー、Network の `/api/chat/stream` ステータスと Response 末尾

---

## 未対応

- GCP **本番** (`medicine.yutok.dev`): Cloud Build 本番トリガー無効のため今回未デプロイ
- Worker の `wrangler deploy`: トークン設定後に `cd workers && npx wrangler deploy`
