# 開発用 LINE Flex プレビュー（5パターン）

**対象環境:** `APP_ENV=development`（`is_development_runtime()` が true）かつ **dev Cloud Run** 等。  
**本番:** トリガー語を送っても通常のチャットとして処理されます。

実装: `src/handlers/line/line_dev_triggers.py`  
連携: `src/handlers/line/line_message_handler.py`

Web のエラー UI プレビュー（[DEV_ERROR_UI_PREVIEW.md](DEV_ERROR_UI_PREVIEW.md)）と同様、**完全一致のトリガー文字列だけ**を LINE に送るとサンプル応答が Push されます。LLM / 推奨パイプラインは走りません。

## 使い方

1. dev 環境で `APP_ENV=development` を設定する。
2. `LINE_WEBHOOK_ENABLED=true` と Reply/Push 用トークンを設定する。
3. @456olljz などの開発用公式アカウントに、下表の **トリガー文字列だけ** を送信する。
4. サーバーログにトリガー一覧が初回出力される。

## 5パターン一覧

| # | トリガー（完全一致で送信） | 種類 | LINE 表示 |
|---|---------------------------|------|-----------|
| 01 | `mrcdevline00000001` | Flex 成功 | アドバイス bubble + 医薬品カルーセル3件（`line.json` 風） |
| 02 | `mrcdevline00000002` | エスカレーション | 赤ヘッダー status Flex（critical） |
| 03 | `mrcdevline00000003` | 危機支援 | 赤ヘッダー status Flex（critical） |
| 04 | `mrcdevline00000004` | 追加質問 | 青ヘッダー status Flex（notice） |
| 05 | `mrcdevline00000005` | 薬剤師フォールバック | 黄ヘッダー status Flex（caution） |

Reply では「【開発プレビュー】サンプルメッセージを送信します。」が返り、続けて Push が届きます。

## 環境変数（任意）

| キー | 既定トリガー |
|------|----------------|
| `DEV_LINE_TRIGGER_FLEX_SUCCESS` | `mrcdevline00000001` |
| `DEV_LINE_TRIGGER_FLEX_ESCALATION` | `mrcdevline00000002` |
| `DEV_LINE_TRIGGER_FLEX_CRISIS` | `mrcdevline00000003` |
| `DEV_LINE_TRIGGER_FLEX_QUESTIONS` | `mrcdevline00000004` |
| `DEV_LINE_TRIGGER_FLEX_SAFE_ERROR` | `mrcdevline00000005` |

## ローカルで JSON のみ確認

```bash
python scripts/line_push_preview.py --trigger flex_success --dry-run
python scripts/line_push_preview.py --trigger flex_escalation --dry-run
```

## Flex Message Simulator でデザイン調整

[Flex Message Simulator](https://developers.line.biz/flex-simulator/) に bubble の `contents` を貼って色・余白を調整できます。

```bash
# 一覧
python scripts/export_line_flex_simulator_samples.py --list

# 1種類を標準出力（Simulator に貼り付け）
python scripts/export_line_flex_simulator_samples.py --kind status_caution

# 全種類を tests/fixtures/line_flex_simulator/ に書き出し
python scripts/export_line_flex_simulator_samples.py --all
```

| `--kind` | 内容 |
|----------|------|
| `success_advice` | 推奨アドバイス bubble |
| `success_carousel` | 医薬品カルーセル |
| `status_caution` | 黄・ご確認ください |
| `status_critical` | 赤・重要なお知らせ |
| `status_notice` | 青・追加質問 |
| `status_pharmacist` | 薬剤師フォールバック |
| `status_info` | 緑・カウンセリング風ご案内 |

## テスト

`tests/test_line_dev_triggers.py` — 本番無効・完全一致・各パターンの Flex/テキスト生成。
