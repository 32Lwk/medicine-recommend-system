# デモフォールバック素材

ライブデモ（https://aws.medicine.yutok.dev）が 503 等で失敗した場合に使用する録画・スクリーンショットを置くディレクトリです。

## 準備手順

1. `./scripts/resume-aws-staging.sh` で ECS 起動
2. [03-demo-script.md](../03-demo-script.md) のメインデモ A を実行しながら録画（60〜90秒、1080p）
3. 以下の PNG をキャプチャ:
   - `01-top.png` — トップ・β版免責
   - `02-input-ja.png` — 日本語入力
   - `03-reco-card.png` — 推奨カード
   - `04-polly.png` — 音声読み上げ UI
   - `05-en.png` — 英語 UI
4. 録画ファイル名例: `aws-staging-demo-YYYYMMDD.mp4`

## 参考（リポジトリ内）

- `docs/archive/gikushosai/presentation_deck/04-demo.png`
- `static/img/about/generated/`

**作成日**: 2026-08-01 — 素材は T-3 までに発表者が追加
