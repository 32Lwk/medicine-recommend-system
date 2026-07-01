# 開発用 UI プレビュー（17パターン）

**対象環境:** `APP_ENV=development`（または `is_development_runtime()` が true のとき）のみ。  
**本番:** トリガー語を送っても通常のチャットとして処理され、プレビューは発火しません。

実装: `src/handlers/chat/chat_dev_triggers.py`  
Sage 描画: `status_renderer.js` / `recommendation_renderer.js`（`body[data-ui-variant="sage"]`）

## 使い方

1. `.env` で `APP_ENV=development` を設定してアプリを起動する。
2. チャットに、下表の **トリガー文字列だけ** を送信する（前後に文字を付けない・完全一致のみ）。
3. 起動後の初回 POST で、サーバーログにトリガー一覧が 1 回出力される。

## 一覧

| # | トリガー | 種類 | Sage 表示 |
|---|----------|------|-----------|
| 01 | `mrcdev00000000000001` | クライアント・エラー | 赤カード（`showErrorMessage`） |
| 02 | `mrcdev00000000000002` | クライアント・警告 | セキュリティ警告 |
| 03 | `mrcdev00000000000003` | HTTP 500 | 通信エラー系 |
| 04 | `mrcdev00000000000004` | システムエラー | `sage_status` error |
| 05 | `mrcdev00000000000005` | 候補なし | `sage_status` caution |
| 06 | `mrcdev00000000000006` | 診断名通知 | `sage_status` notice |
| 07 | `mrcdev00000000000007` | エスカレーション | `sage_status` critical |
| 08 | `mrcdev00000000000008` | 挨拶 | `sage_status` notice（フィードバックなし） |
| 09 | `mrcdev00000000000009` | 店舗案内 | `sage_status` notice + フィードバック |
| 10 | `mrcdev00000000000010` | 医薬品 Q&A | `sage_qa` |
| 11 | `mrcdev00000000000011` | 推奨成功 | `sage_reco` + カルーセル |
| 12 | `mrcdev00000000000012` | 推奨 0 件 | `sage_reco` + error |
| 13 | `mrcdev00000000000013` | 緊急 | `sage_status` critical |
| 14 | `mrcdev00000000000014` | 危機支援 | `sage_status` security |
| 15 | `mrcdev00000000000015` | カウンセリング | `sage_status` notice |
| 16 | `mrcdev00000000000016` | LLM 障害（quota 等） | `sage_status` error |
| 17 | `mrcdev00000000000017` | 医薬品種類不明 | `sage_status` caution |

04〜17 は `diagnosis` v1 + マーカー（Sage UI）で描画されます。

## 環境変数（任意）

`DEV_ERROR_TRIGGER_*`（01〜07）および `DEV_SAGE_TRIGGER_*`（08〜17）で上書き可能。  
未設定時は上表の既定トークンを使用。

## テスト

`tests/chat/test_chat_dev_triggers.py`
