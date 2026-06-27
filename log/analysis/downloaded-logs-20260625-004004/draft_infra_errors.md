# Wave A — infra_errors グループ分析（ドラフト）

## 対象・環境

| 項目 | 値 |
|------|-----|
| ソース | `downloaded-logs-20260625-004004.json` |
| **環境** | **開発（`medicine-recommend-dev`）** — 本ログに prod（`medicine-recommend`）は含まれない |
| 期間 | 2026-06-23T15:40:11Z ～ 2026-06-24T15:15:56Z（約24時間） |
| エントリ数 | 7,722 |
| 主 commit | `a7455d2bb00b2538316be114a876bf78f10f4544` |
| revision 推移 | `00114-745` → `00121-lwb`（15回の切替記録） |
| severity 集計 | INFO 1,489 / DEFAULT 6,214 / NOTICE 7 / **ERROR 12** |

---

## エグゼクティブサマリー（最大5項目）

- 🔴 **開発環境**で `counseling_processor.py:318` の **`NameError: generate_counseling_response` が2回**（revision `00121-lwb`）。カウンセリング応答生成パスが実害ありで破損。
- 🔴 管理画面 API が **HTTP 500×2**（`POST /admin/medicine_chat`、`GET /api/admin/sessions`）。直後のテキストログも同一 `NameError` 系で、**ユーザー／運用者向けの実障害**。
- 🟡 **HTTP 503×6** はすべて **`POST /line/webhook`・2026-06-23T23:43～23:48 UTC** に限定。revision `00115-jdn`→`00116-krg` の **Cloud Run ロールアウト直後**と同期。**恒常的なユーザー向け 503 ではなく、デプロイ起因の benign noise**。
- 🟢 24時間の HTTP 4xx/5xx は **計8件のみ**（7,722 エントリ中）。DB/Neon 接続失敗や大量 5xx スパイクは検出されず。
- 🟡 約9時間で **revision 7回連続切替**（23:39～02:44 UTC）。503 の発生窓はこの密集デプロイに依存。**ロールアウト外で 503 が出たら要アラート**。

---

## 所見（タイムスタンプ・証拠付き）

### 1. HTTP 異常サマリー

`errors_http.json` より:

| status | 件数 | パス |
|--------|------|------|
| 503 | 6 | `POST /line/webhook` |
| 500 | 2 | `POST /admin/medicine_chat`×1、`GET /api/admin/sessions`×1 |

---

### 2. 🟡 デプロイ起因 503（benign）vs ユーザー向け 503 の区別

#### 証拠: 503×6（すべて LINE webhook）

| 時刻 (UTC) | status | latency | revision |
|------------|--------|---------|----------|
| 2026-06-23T23:43:30 | 503 | 0.219s | `00115-jdn` |
| 2026-06-23T23:44:30 | 503 | 0.034s | `00115-jdn` |
| 2026-06-23T23:45:30 | 503 | 0.002s | `00115-jdn` |
| 2026-06-23T23:46:30 | 503 | 0.002s | `00115-jdn` |
| 2026-06-23T23:47:30 | 503 | 0.002s | `00115-jdn` |
| 2026-06-23T23:48:30 | 503 | 0.133s | `00116-krg` |

**デプロイ境界との対応**（`deploy_revision.json`）:

- `2026-06-23T23:39:59` — revision `00115-jdn` へ切替開始
- `2026-06-23T23:48:01` — `00116-krg` へ切替
- 以降 23:49～02:44 に `00117`～`00121` へ連続ロールアウト

**判定: 🟡 benign deploy noise**

- 503 は **ロールアウト直後の約5分間のみ**。以降24時間で追加の 503 なし。
- latency が **2～220ms** と極端に短く、Cloud Run が新インスタンス未就绪時に返す **プラットフォーム 503** の典型。
- **約60秒間隔**（23:43, 23:44, …）は LINE 側の webhook 再送・疎通確認と整合。
- アプリ内 503（`src/handlers/line/line_webhook.py` L145–156）は `LINE_WEBHOOK_ENABLED=false` または `LINE_CHANNEL_SECRET` 未設定時に JSON エラーボディを返す設計。**本件はデプロイ窓・低レイテンシ・revision 遷移と一致**し、設定ミス型の恒常 503 とは性質が異なる。

**ユーザー向け 503 ではない根拠**: 窓が閉じた後は webhook が正常応答。本 export 期間中、ロールアウト外の LINE 503 は **0件**。

---

### 3. 🔴 アプリケーション 500（実障害）

| 時刻 (UTC) | status | path | latency | revision |
|------------|--------|------|---------|----------|
| 2026-06-24T01:33:09 | 500 | `POST /admin/medicine_chat` | 4.90s | `00120-tgk` |
| 2026-06-24T01:33:56 | 500 | `GET /api/admin/sessions` | 1.30s | `00120-tgk` |

**判定: 🔴 critical — 運用者向け実障害**

- ルート定義: `main.py` の `@app.post("/admin/medicine_chat")`（L2340付近）、`@app.get("/api/admin/sessions")`（L2509付近）。
- 直後 **2026-06-24T01:33:57Z** にテキスト ERROR が連鎖:
  - `[ERROR] エラー詳細ログ [session_id: 1782074044488131856187] [type: NameError]`
  - `[ERROR] Exception in ASGI application`（gunicorn/uvicorn）
  - Starlette middleware 経由の Traceback

medicine_chat 送信が先に失敗し、約47秒後にセッション一覧取得も 500。**同一セッション処理中の未処理例外が管理 API 全体に波及**したパターン。

---

### 4. 🔴 テキスト ERROR — `NameError`（カウンセリング）

`errors_http.json` → `text_errors`（count: 6）の主要パターン:

| 時刻 (UTC) | メッセージ要約 | revision |
|------------|----------------|----------|
| 2026-06-24T01:33:57 | `[type: NameError]`（session `1782074044488131856187`） | `00120-tgk` |
| 2026-06-24T02:46:21 | `counseling_processor.py:318` — `NameError: name 'generate_counseling_response' is not defined` | `00121-lwb` |
| 2026-06-24T07:34:45 | 同上 | `00121-lwb` |

**コード根拠**:

```318:325:src/services/counseling/counseling_processor.py
            counseling_response_text = generate_counseling_response(
                symptom_type,
                user_text,
                client,
                conversation_history=conversation_history,
                session_id=session_id
            )
```

ログ期間のデプロイ revision（`a7455d2`）では **import 欠落**により L318 で `NameError` が発生。関数本体は `src/services/counseling/counseling_generator.py` に定義。

**現行ワークスペース**: L17 に `from src.services.counseling.counseling_generator import generate_counseling_response` が存在（CHANGELOG・`tests/services/counseling/test_counseling_processor_import.py` で回帰防止済み）。**修正はコミット済みだが、ログ上の revision `00120`/`00121` には未反映または再デプロイ前**と推定。

**判定: 🔴 critical** — 不眠以外の症状タイプでカウンセリング継続時に必ず失敗するコードパス。

---

### 5. 🟢 参考: 遅延エンドポイント（エラーではない）

`errors_http.json` → `slow_endpoints_ge_5s`:

- `GET /api/sessions`: 953件、**p95 0.31s**、max 15.1s（外れ値少数）
- `PATCH /api/sessions/activity`: 202件、**p95 0.31s**、max 14.7s

中央値・p95 は正常。**max のみスパイク**で、本 infra_errors グループの主因ではない。

---

### 6. 🟡 デプロイ頻度（間接的要因）

`deploy_revision.json` — 主要切替（同一 commit `a7455d2`）:

| 時刻 (UTC) | revision |
|------------|----------|
| 2026-06-23T23:39:59 | `00115-jdn` |
| 2026-06-23T23:48:01 | `00116-krg` |
| 2026-06-23T23:49:00 | `00117-6pf` |
| 2026-06-23T23:49:24 | `00118-rll` |
| 2026-06-23T23:53:58 | `00119-9x5` |
| 2026-06-24T00:58:44 | `00120-tgk` |
| 2026-06-24T02:44:30 | `00121-lwb` |

約9時間で7 revision。**503 の唯一の発生窓は最初のロールアウト直後**だが、頻繁な切替は今後も短時間 unavailable を誘発しうる。

---

## 推奨アクション

### 🔴 即時（コード）

1. **`src/services/counseling/counseling_processor.py`** — `generate_counseling_response` の import がデプロイ revision に載っているか確認。未反映なら `counseling_generator` からの import を含むビルドを dev へ再デプロイ。
2. **回帰テスト** — `tests/services/counseling/test_counseling_processor_import.py` を CI で必須化（既存テストの維持）。
3. **管理 API** — `main.py` の `/admin/medicine_chat`・`/api/admin/sessions` でカウンセリング経路を踏むリクエストの統合テスト追加（`tests/api/test_fastapi_contract.py` を拡張）。

### 🟡 インフラ・運用

4. **デプロイ中 LINE 503 緩和** — Cloud Run dev: `min-instances ≥ 1`、startup/readiness プローブの見直し。ロールアウト中も旧 revision が traffic を捌けるよう **traffic 分割**またはデプロイ間隔の確保。
5. **監視** — `POST /line/webhook` の 503 をアラート対象にするが、**revision 切替 ±5分以内は抑制**（benign deploy）。ロールアウト外の 503 は即時通知。
6. **アプリ内 503 の切り分け** — `line_webhook.py` L145–156 の 503 はレスポンスボディに `LINE webhook is disabled` / `LINE_CHANNEL_SECRET is not configured` が含まれる。ログに JSON body があれば設定ミス、なければプラットフォーム 503 と判別可能。

### 🟢 情報

7. 本 export は **dev のみ**。prod への同障害波及は本データでは評価不可。prod デプロイ前に上記 import 修正の含有を必須確認。

---

## セッション深掘りについて

本ドラフトは **infra_errors グループ**の範囲に限定。個別セッション（例: `1782074044488131856187`）の会話品質・LLM 応答は **分析対象外**（Wave 別グループに委譲）。

---

*生成: Wave A infra_errors / 入力: `sections/errors_http.json`, `sections/deploy_revision.json`, `metadata.json`*
