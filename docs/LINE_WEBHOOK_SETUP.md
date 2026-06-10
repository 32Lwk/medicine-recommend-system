# LINE Webhook 環境構築（ローカル Mac / Windows・GCP）

Webhook 受信・署名検証・Reply/Push・Flex Message・推奨パイプライン連携を実装済みです。  
本番 `medicine-recommend` は `LINE_WEBHOOK_ENABLED=false` のまま、検証は **dev Cloud Run** で行います。

関連: [ROUTE_SPEC.md](ROUTE_SPEC.md) · [CLOUD_RUN_LLM_ENV.md](CLOUD_RUN_LLM_ENV.md)

---

## 1. 前提

| 項目 | 内容 |
|------|------|
| エンドポイント | `POST /line/webhook` |
| 状態確認 | `GET /line/webhook/status` |
| 既定 | `LINE_WEBHOOK_ENABLED=false`（未設定時は Webhook 無効） |
| インフラ | ローカル: `python app.py` または `./start.sh` / GCP: Cloud Run |

---

## 2. LINE Developers の準備（共通）

1. [LINE Developers Console](https://developers.line.biz/console/) でプロバイダーを作成
2. **Messaging API** チャネルを作成
3. **チャネル基本設定** で **Channel secret** を控える
4. **Messaging API 設定** で **Channel access token**（長期）を発行（Reply 実装まで未使用でも可）
5. **応答メッセージ**・**あいさつメッセージ**はオフ推奨（アプリ側で制御するため）
6. Webhook URL は後述（ローカルは ngrok、GCP は Cloud Run URL）

---

## 3. 環境変数

`.env`（ローカル）または Cloud Run の環境変数に設定します。

```bash
LINE_CHANNEL_SECRET=（チャネル基本設定の Channel secret）
LINE_CHANNEL_ACCESS_TOKEN=（Messaging API の長期トークン・任意）
LINE_WEBHOOK_ENABLED=true
```

| 変数 | 説明 |
|------|------|
| `LINE_CHANNEL_SECRET` | `X-Line-Signature` 検証に必須 |
| `LINE_CHANNEL_ACCESS_TOKEN` | 将来の Reply API 用。現フェーズでは未使用 |
| `LINE_WEBHOOK_ENABLED` | `true` のときのみ `/line/webhook` が有効 |

秘密値を Git にコミットしないこと。`.env` は `.gitignore` 対象です。

---

## 4. ローカル（macOS）

### 4.1 アプリ起動

```bash
cd /path/to/medicine-recommend-system
cp .env.example .env
# .env に LINE_* を記入

pip install -r requirements.txt
python app.py
# または: ./start.sh
```

既定ポートは **5000**（`PORT` 未設定時）。`http://localhost:5000/line/webhook/status` で設定確認:

```json
{"enabled": true, "channel_secret_configured": true, "channel_access_token_configured": true}
```

### 4.2 HTTPS トンネル（ngrok）

LINE は **HTTPS** の Webhook のみ受け付けます。ローカルでは ngrok 等で公開します。

```bash
# ngrok をインストール後（Homebrew: brew install ngrok）
ngrok http 5000
```

表示された `https://xxxx.ngrok-free.app` を使い、LINE の Webhook URL に登録:

```
https://xxxx.ngrok-free.app/line/webhook
```

### 4.3 LINE 側の検証

1. Messaging API 設定で **Webhook URL** を上記に設定
2. **Webhookの利用** を ON
3. **検証** ボタン → 成功すれば Cloud Run / ローカルに POST が届く
4. ターミナルログに `LINE webhook received events=...` が出ることを確認
5. 友だち追加後、テキスト送信 → 同様にログのみ（**返信はまだ来ない**）

### 4.4 署名の手動確認（任意）

```bash
SECRET="your-channel-secret"
BODY='{"events":[]}'
SIG=$(printf '%s' "$BODY" | openssl dgst -sha256 -hmac "$SECRET" -binary | base64)
curl -s -X POST "http://localhost:5000/line/webhook" \
  -H "Content-Type: application/json" \
  -H "X-Line-Signature: $SIG" \
  -d "$BODY"
# → {"status":"ok","events_received":0}
```

---

## 5. ローカル（Windows）

### 5.1 アプリ起動

**PowerShell** または **コマンドプロンプト**:

```powershell
cd C:\path\to\medicine-recommend-system
copy .env.example .env
# .env を編集して LINE_* を設定

pip install -r requirements.txt
python app.py
```

ブラウザで `http://localhost:5000/line/webhook/status` を開き、設定を確認します。

### 5.2 HTTPS トンネル

**ngrok（推奨）**

1. [ngrok](https://ngrok.com/) をインストールし `ngrok config add-authtoken ...` を実行
2. PowerShell:

```powershell
ngrok http 5000
```

3. `Forwarding` 行の `https://....ngrok-free.app` を Webhook URL に登録:

```
https://xxxx.ngrok-free.app/line/webhook
```

**Cloudflare Tunnel（代替）**

```powershell
cloudflared tunnel --url http://localhost:5000
```

表示された HTTPS URL + `/line/webhook` を LINE に登録します。

### 5.3 Windows 固有の注意

- ファイアウォールで Python の受信を許可するダイアログが出たら許可
- 改行コードは `.env` が CRLF でも通常は問題なし（値の前後空白は trim 済み）
- `openssl` が無い場合は Git Bash または WSL で署名テストコマンドを実行

---

## 6. GCP Cloud Run（dev）

本番 `medicine-recommend` より先に **dev**（`medicine-recommend-dev`）で構築することを推奨します。

### 6.1 環境変数の設定

**Google Cloud Console**

1. Cloud Run → `medicine-recommend-dev` → **編集して新しいリビジョンをデプロイ**
2. **変数とシークレット** に追加:
   - `LINE_WEBHOOK_ENABLED` = `true`
   - `LINE_CHANNEL_SECRET` = （Channel secret）
   - `LINE_CHANNEL_ACCESS_TOKEN` = （任意）
3. デプロイ

**gcloud CLI**

```bash
gcloud run services update medicine-recommend-dev \
  --region=asia-northeast1 \
  --update-env-vars="LINE_WEBHOOK_ENABLED=true,LINE_CHANNEL_SECRET=YOUR_SECRET"
```

（トークンは Secret Manager 連携に移行する場合は Console の「シークレットを参照」を使用）

### 6.2 Webhook URL

サービス URL を確認:

```bash
gcloud run services describe medicine-recommend-dev \
  --region=asia-northeast1 \
  --format='value(status.url)'
```

LINE Developers に登録:

```
https://medicine-recommend-dev-XXXXXXXX.asia-northeast1.run.app/line/webhook
```

### 6.3 動作確認

```bash
curl -s "https://YOUR-DEV-URL/line/webhook/status"
```

LINE コンソールで **検証** → Cloud Run のログ（Logging）に `LINE webhook received` が出ることを確認します。

```bash
gcloud logging read \
  'resource.type="cloud_run_revision" AND textPayload:"LINE webhook"' \
  --limit=5 --format='value(textPayload)'
```

### 6.4 本番（medicine-recommend）

- 検証完了まで `LINE_WEBHOOK_ENABLED=false` のまま推奨
- 本番有効化時も手順は dev と同じ（サービス名と URL のみ変更）

---

## 7. 環境ごとの Webhook URL 一覧（例）

| 環境 | Webhook URL の例 | 備考 |
|------|------------------|------|
| ローカル Mac/Win | `https://xxxx.ngrok-free.app/line/webhook` | ngrok 再起動で URL が変わる |
| GCP dev | `https://medicine-recommend-dev-....run.app/line/webhook` | 固定 URL |
| GCP 本番 | `https://medicine.yutok.dev/line/webhook` 等 | カスタムドメイン利用時 |

**1 チャネルに登録できる Webhook URL は 1 つ**です。ローカルと GCP を同時に試す場合は、都度 LINE コンソールで URL を切り替えるか、チャネルを分けてください。

---

## 8. トラブルシューティング

| 症状 | 確認事項 |
|------|----------|
| LINE 検証が失敗 | URL が `https`・末尾 `/line/webhook`・`LINE_WEBHOOK_ENABLED=true`・Secret 一致 |
| 401 Invalid signature | Channel secret の誤り、body の再エンコード（署名は raw body で計算） |
| 503 disabled | `LINE_WEBHOOK_ENABLED` が `false` または未設定 |
| 503 secret not configured | `LINE_CHANNEL_SECRET` 未設定 |
| ローカルに届かない | ngrok が起動中か、LINE の Webhook URL が最新か |
| GCP に届かない | 最新リビジョンに env が入っているか、IAM で未認証呼び出し可か |
| 検証がタイムアウト | コールドスタート。先に `GET /line/webhook/status` でウォームアップしてから「検証」 |
| 「少々お待ちください」だけ届く | ログに `WORKER TIMEOUT` がないか。`GUNICORN_TIMEOUT=300`（`start.sh` 既定）を確認 |
| Push が届かない | ログの `LINE push failed`。Flex 拒否時は altText のテキストフォールバックあり |

Cloud Run は **未認証の POST** を受け付ける必要があります（LINE Platform からの呼び出しのため）。ingress 設定でブロックしていないか確認してください。

**Cloud Run 推奨（dev）**

- リクエスト timeout: **300s** 以上
- 環境変数: `GUNICORN_TIMEOUT=300`（未設定時も `start.sh` 既定 300）
- バックグラウンドの推奨処理が遅い場合: 「CPU を常に割り当てる」を検討

---

## 9. Flex Message・Reply/Push（実装済み）

### 9.1 動作概要

1. ユーザーが 1:1 でテキスト送信
2. Webhook が即 **200** を返す（処理は **専用スレッド** のバックグラウンド）
3. **Reply** で「症状を確認しています。少々お待ちください。」
4. 既存 `handle_chat_post` で推奨（sid は `line:{userId}`）
5. **Push** で Flex 2通（アドバイス bubble + 医薬品 carousel 最大3件）

危機検出・緊急時は Flex ではなくテキスト Push。管理画面の手動キューは既存通り。

### 9.2 必須環境変数（返信する場合）

| 変数 | 用途 |
|------|------|
| `LINE_CHANNEL_SECRET` | Webhook 署名 |
| `LINE_CHANNEL_ACCESS_TOKEN` | Reply / Push |
| `LINE_WEBHOOK_ENABLED=true` | Webhook 有効化 |
| `DATABASE_URL` | セッション永続化 |

`LINE_CHANNEL_ACCESS_TOKEN` 未設定時は Webhook は **200** のまま、Reply/Push はスキップされます。

### 9.3 開発用 Flex プレビュー（エラー UI プレビューと同様）

dev 環境（`APP_ENV=development`）で、LINE に **トリガー文字列だけ** を送ると LLM なしでサンプル Push されます。  
詳細: [DEV_LINE_FLEX_PREVIEW.md](DEV_LINE_FLEX_PREVIEW.md)

| トリガー | 内容 |
|----------|------|
| `mrcdevline00000001` | Flex 成功（アドバイス + カルーセル3件） |
| `mrcdevline00000002`〜`05` | エスカレーション / 危機 / 質問 / フォールバック（status Flex） |

Flex Simulator 用 JSON: `python scripts/export_line_flex_simulator_samples.py --all` → [Flex Message Simulator](https://developers.line.biz/flex-simulator/)

### 9.4 ローカル確認

```bash
# Flex JSON（Simulator 用）
python scripts/line_push_preview.py --trigger flex_success --dry-run

# pytest
pytest tests/test_line_flex_messages.py tests/test_line_webhook.py -q

# 実機 Push（Webhook 不要）
# .env: LINE_CHANNEL_ACCESS_TOKEN, LINE_PUSH_TO_USER_ID
python scripts/line_push_preview.py --user-id Uxxxxxxxx
```

Flex Simulator: https://developers.line.biz/flex-simulator/

### 9.4 管理画面

LINE セッションの sid は `line:Uxxxxxxxx` 形式です。既存の管理チャットでそのまま参照できます。

### 9.5 Cloud Run 運用注意

バックグラウンド処理中にインスタンスがスケールダウンすると Push が届かない場合があります。長時間化する場合は将来 Cloud Tasks 等を検討してください。

### 9.6 将来: hero 画像

v1 は hero なし（Noimage）。商品画像 URL が整備されたら `flex_messages.build_medicine_bubble(..., hero_url=...)` で拡張予定。
