# LINE 応答速度ベンチ（dev のみ）

対象: **medicine-recommend-dev**（ウォームインスタンス前提）

## 事前確認

1. Cloud Run `min-instances=1` を設定済み（[CLOUD_RUN_LLM_ENV.md](CLOUD_RUN_LLM_ENV.md)）
2. `GET /admin/system_status` で以下を確認:
   - `database.available: true`
   - `database.persist_enabled: true`
   - `database.uses_pooler: true`（推奨）
3. 直前に Web または LINE で 1 通送り、インスタンスをウォームにする

## ベンチ A: 挨拶（目標 LINE < 1秒）

| 手順 | Web | LINE |
|------|-----|------|
| メッセージ | 「こんにちは」 | 同文を LINE で送信 |
| 計測 | ブラウザ DevTools Network（POST `/` 〜 最初の SSE チャンク） | LINE クライアントの応答までの体感 + Cloud Logging |
| 合格 | Web ~0.25s 前後 | **< 1秒**（ウォーム） |

## ベンチ B: 症状相談（目標 LINE 4〜6秒）

| 手順 | Web | LINE |
|------|-----|------|
| メッセージ | 「頭が痛いです」等 | 同文 |
| 合格 | Web 3.6〜5.9s 前後 | **4〜6秒**（ウォーム） |

## ログ確認（受け入れ判定）

Cloud Logging で次を検索し、差分を記録する:

```
PIPELINE_PERF
POST処理開始
LINE reply ok
line_loading_start
line_reply_done
```

確認ポイント:

- `loading` 〜 `reply ok` の間に DB 再接続ログ（`Reconnection attempt`）が無いこと
- Physical 推奨時、carousel Push が 3 秒以内に完了、または最終 reply に carousel が含まれること
- `PIPELINE_PERF` の計測起点が Web / LINE で同程度（handler 入口の二重計測が無いこと）

## 記録テンプレート

```
日付:
リビジョン:
database.available:
Web 挨拶:
LINE 挨拶:
Web 症状:
LINE 症状:
備考（ログ異常など）:
```
