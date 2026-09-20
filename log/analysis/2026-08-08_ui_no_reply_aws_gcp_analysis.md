# UI 送信後に返信が来ない — AWS/GCP ログ解析レポート

**解析日**: 2026-08-08  
**対象**: AWS ステージング `aws-medicine.yutok.dev` / GCP 本番 `medicine.yutok.dev` / GCP dev  
**ログソース**:
- AWS: `log/raw/downloaded-aws-logs-20260806-20260808-20260808-061659.json`（9130 entries）
- GCP dev: `log/raw/downloaded-logs-20260806-20260808-20260808-061700.json`（3162 entries）
- GCP prod: `log/raw/downloaded-logs-20260729-20260808-20260808-061701.json`（31512 entries）

---

## エグゼクティブサマリ

| 環境 | 根本原因 | 深刻度 | 修正 |
|------|----------|--------|------|
| **AWS** (`aws-medicine.yutok.dev`) | Cloudflare Worker が **POST ボディを転送していない** → `/api/chat/stream` が **422**（`message` 欠落） | 🔴 critical | `workers/src/index.js` 修正済（**Worker デプロイ要**） |
| **GCP 本番** | バックエンドは正常（curl で `done` イベントまで確認）。遅延 60–70s や SSE 切断時の回復ポーリングの可能性 | 🟡 warning | 本番デプロイ遅延（`cec79d9`）の確認・必要なら prod 再デプロイ |
| **GCP dev** | バックエンド正常（挨拶 1 件、33s で返信ログあり） | 🟢 info | UI 表示問題があれば別途 URL/ブラウザ確認 |

---

## AWS — 詳細

### 証拠

1. **ログ**: `POST /api/chat/stream` → **422**（Cloudflare IP `2a06:98c0:3600::103`）
2. **再現**:
   ```bash
   curl -X POST https://aws-medicine.yutok.dev/api/chat/stream -F "message=テスト"
   # → 422 {"detail":[{"type":"missing","loc":["body","message"],...}]}
   ```
3. **Origin 直叩き**（Tunnel 経由）:
   ```bash
   curl -X POST https://origin-aws-medicine.yutok.dev/api/chat/stream -F "message=テスト"
   # → 200 text/event-stream（正常）
   ```

### 原因

`workers/src/index.js` のプロキシ `fetch()` が **`body` 未指定**。GET/HEAD 以外（チャット POST 含む）でリクエストボディが Origin に届かず、FastAPI の `Form(...)` バリデーションが 422 を返す。

### 副次現象

- フロントは `SSE HTTP 422` → `stream-result` ポーリングへフォールバック
- `stream-result` は `ready: false` のまま（処理が開始されないため）→ **UI に返信なし**

### デプロイ中の一時エラー（benign 以外）

- 2026-08-08 04:11 UTC: cloudflared `connection refused`（ECS ローリング更新中）
- 2026-08-08 04:12 UTC: `Database connection failed: localhost:5432`（起動直後・一時的）

---

## GCP — 詳細

### 本番 (`medicine.yutok.dev`, commit `cec79d9`)

- **curl 再現（2026-08-08）**: `POST /api/chat/stream` → 200、約 71s で `event: done`（頭痛推奨 sage_reco まで完走）
- **過去ログ**: `POST` 200（46s）、続く `stream-result` ポーリング多数 → SSE 切断後の回復試行パターン
- **本番 Cloud Build トリガー**: `disabled: true`（自動デプロイ停止中）

### dev (`medicine-recommend-dev`)

- セッション `1786162983082137830339`: 「やあこんばんは」→ 33s で bot 返信（counseling_detail 記録あり）
- `POST /api/chat/stream` 200（38.4s）

### GCP で「返信なし」に見える可能性

1. **処理時間 30–70s** — ステータスバーのみでユーザーが待ちきれない
2. **SSE 切断**（モバイル/LINE ブラウザ）— `stream-result` 回復が間に合わないケース
3. **本番が旧 commit** — 既知バグが残っている可能性（要 prod デプロイ）

---

## 実施した修正

**ファイル**: `workers/src/index.js`

```javascript
if (request.method !== "GET" && request.method !== "HEAD") {
  proxyInit.body = request.body;
}
```

---

## ローカル E2E 検証（修正後）

| テスト | 結果 |
|--------|------|
| `scripts/test_sse_chat_e2e.py`（local :5000） | PASS（done 受信） |
| `v2_tier1_short_symptom.yaml` 3 シナリオ | **3/3 auto-pass** |
| レポート | `log/analysis/2026-08-08_local_v2_chat_test_post-worker-fix-verify.md` |

---

## 優先アクション

1. 🔴 **Cloudflare Worker デプロイ**（要 `CLOUDFLARE_API_TOKEN`）:
   ```bash
   cd workers && npx wrangler deploy
   ```
2. デプロイ後確認:
   ```bash
   curl -X POST https://aws-medicine.yutok.dev/api/chat/stream -F "message=テスト" -H "Accept: text/event-stream"
   # 期待: HTTP 200 + SSE status/done
   ```
3. 🟡 GCP 本番を最新 main にデプロイ（トリガー再有効化 or 手動 Cloud Build）
4. ユーザー確認事項（下記）

---

## ユーザーへの確認事項

1. 問題が出た **URL** はどれですか？（`medicine.yutok.dev` / dev run.app / `aws-medicine.yutok.dev`）
2. **ブラウザ**（Chrome / Safari / LINE 内ブラウザ等）
3. 送信後 **何秒待ち**ましたか？（処理中表示は出ますか？）
4. 開発者ツール Network で `/api/chat/stream` の **HTTP ステータス**（422 / 200 / 503）
