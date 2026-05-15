# 開発用エラー UI プレビュー（7パターン）

**対象環境:** `APP_ENV=development`（または `is_development_runtime()` が true のとき）のみ。  
**本番:** トリガー語を送っても通常のチャットとして処理され、プレビューは発火しません。

実装: `src/handlers/chat/chat_dev_triggers.py`  
フロント: `static/js/main.js`（`showErrorMessage` / `showWarningMessage` / `chat-status-card`）

## 使い方

1. `.env` で `APP_ENV=development` を設定してアプリを起動する。
2. チャットに、下表の **トリガー文字列だけ** を送信する（前後に文字を付けない・完全一致のみ）。
3. 起動後の初回 POST で、サーバーログにトリガー一覧が 1 回出力される。

トリガー語は `.env` の `DEV_ERROR_TRIGGER_*` で上書き可能（未設定時は下表の既定値）。  
毎回変える UUID は非推奨（症状文と衝突しにくい固定の難読語を推奨）。

## 7パターン一覧（すべて実装済み）

| # | トリガー（完全一致で送信） | 種類 | 表示 |
|---|---------------------------|------|------|
| 01 | `mrcdev00000000000001` | クライアント・エラー | 赤カード（`showErrorMessage`） |
| 02 | `mrcdev00000000000002` | クライアント・警告 | 赤枠・セキュリティ（`showWarningMessage`） |
| 03 | `mrcdev00000000000003` | HTTP 500 | 通信エラー系カード（fetch 失敗扱い） |
| 04 | `mrcdev00000000000004` | HTML・システム | 赤 `chat-status-card`（サーバー生成） |
| 05 | `mrcdev00000000000005` | HTML・注意 | 黄 `chat-status-card` + フィードバック |
| 06 | `mrcdev00000000000006` | HTML・通知 | 青（診断名検出風） |
| 07 | `mrcdev00000000000007` | HTML・重要 | 赤・critical（エスカレーション風） |

## 環境変数（任意）

| キー | 既定トリガー |
|------|----------------|
| `DEV_ERROR_TRIGGER_CLIENT` | `mrcdev00000000000001` |
| `DEV_ERROR_TRIGGER_WARNING` | `mrcdev00000000000002` |
| `DEV_ERROR_TRIGGER_HTTP500` | `mrcdev00000000000003` |
| `DEV_ERROR_TRIGGER_HTML_SYSTEM` | `mrcdev00000000000004` |
| `DEV_ERROR_TRIGGER_HTML_CAUTION` | `mrcdev00000000000005` |
| `DEV_ERROR_TRIGGER_HTML_NOTICE` | `mrcdev00000000000006` |
| `DEV_ERROR_TRIGGER_HTML_CRITICAL` | `mrcdev00000000000007` |

## 応答の違い（01〜03 vs 04〜07）

| 区分 | パターン | サーバー応答 |
|------|----------|----------------|
| クライアント専用 | 01, 02 | JSON（`error` / `warning`）。ユーザー発言のみ履歴保存 |
| HTTP ステータス | 03 | JSON + **HTTP 500** |
| HTML ボット応答 | 04〜07 | `html_formatter` 生成 HTML をボットメッセージとして保存・返却 |

## テスト

`tests/test_chat_dev_triggers.py` — 本番無効・完全一致・各種応答の回帰。
