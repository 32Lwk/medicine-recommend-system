# ライブデモ台本 — aws.medicine.yutok.dev

**デモ URL**: https://aws.medicine.yutok.dev  
**所要時間**: 90〜120秒（プレゼン5分のうち約2分）  
**作成日**: 2026-08-01  
**発表者**: 川嶋宥翔

> **免責（口頭でも必ず）**: 本デモは β版の参考情報提供です。医師・薬剤師の診断・指導の代替ではありません。重い症状は医療機関を受診してください。

---

## 疎通確認記録

| 日時 | エンドポイント | 結果 | 備考 |
|------|----------------|------|------|
| 2026-08-01 17:09 JST | `GET /health` | **HTTP 503** | ECS `desiredCount=0` または Budget 停止の可能性（[`AWS_ARCHITECTURE_DIAGRAMS.md`](../../ops/AWS_ARCHITECTURE_DIAGRAMS.md) 注記） |

**T-3日までに必須**: `./scripts/resume-aws-staging.sh` で ECS 起動 → `/health` が 200 になることを確認。

```bash
# 復旧（AWS プロファイル medicine-recommend-dev 想定）
./scripts/resume-aws-staging.sh
curl -s https://aws.medicine.yutok.dev/health
curl -s https://aws.medicine.yutok.dev/health/aws
```

---

## 事前準備（発表30分前）

### ネットワーク・端末

- [ ] 会場 Wi-Fi または **スマホテザリング**（5GHz 推奨）を確認
- [ ] ノート PC フル充電 + 充電器持参
- [ ] ブラウザ: Chrome / Edge 最新（シークレット不要、キャッシュクリア推奨）
- [ ] ブックマーク: `https://aws.medicine.yutok.dev`
- [ ] 投影: 解像度 1920×1080（16:9）で文字サイズ「大」を一度確認

### AWS ステージング

- [ ] `./scripts/resume-aws-staging.sh` 実行済み
- [ ] `GET /health` → `status: ok`（または 200）
- [ ] `GET /health/aws` → Translate / Polly / KB フラグが期待どおり
- [ ] メインデモを **通し1回** リハーサル（入力〜音声まで）

### バックアップ

- [ ] 録画 MP4 をローカルに保存（下記「フォールバック」）
- [ ] `docs/planning/aws-contest/demo-fallback/` にスクリーンショット 5枚以上
- [ ] PDF スライドを USB にコピー

### デモ用設定

| 項目 | 推奨値 |
|------|--------|
| 言語 | シナリオA: 日本語 / シナリオB: English |
| 文字サイズ | **大**（高齢者想定デモ） |
| 音声読み上げ | オン（Polly — AWS ステージング） |
| 入力 | **コピペ可**（ライブタイプは1回のみ、下書きメモに文言保持） |

---

## メインデモシナリオ — A: 高齢者想定（日本語）

**所要**: 約100秒 | **AWS 訴求**: Polly + ルールベース推奨 + ECS

| Step | 操作 | 期待画面 | 話すセリフ（目安） |
|------|------|----------|-------------------|
| 1 | ブラウザで `https://aws.medicine.yutok.dev` を開く | Sage Terrace UI、免責・β版表示 | 「AWS 東京リージョンのステージング環境を開きます。」 |
| 2 | 設定で **文字サイズ「大」**、言語 **日本語** | UI が拡大 | 「高齢者向けに文字を大きくします。」 |
| 3 | チャット入力欄に以下を **貼り付けまたは入力** | — | 「症状を自然な日本語で入力します。」 |
| | `昨夜から喉が痛くて、微熱があります。` | | |
| 4 | 送信 | ステータスカード → OTC 推奨カード（sage_reco） | 「ルールベースで候補が選ばれます。LLM が薬名を創作しません。」 |
| 5 | 推奨カードの **注意点・受診目安** を指差し | 軽症向け注意 + 必要時受診の記載 | 「β版ですが、重い症状は受診を勧める安全設計です。」 |
| 6 | **音声読み上げ**ボタンをタップ | Amazon Polly による読み上げ | 「AWS の Polly で回答を読み上げます。聴力に配慮した利用イメージです。」 |
| 7 | （余裕あれば）URL バーまたは `/health/aws` | AWS 機能フラグ | 「Translate や Bedrock もこの環境で動いています。」 |

---

## サブシナリオ — B: 訪日外国人（英語）30秒版

**トリガー**: メインが503・タイムアウト・推奨失敗時の **予備** または Q&A 用。

| Step | 操作 | 期待画面 | 話すセリフ |
|------|------|----------|------------|
| 1 | 言語を **English** に変更 | UI 英語化 | 「仙台などの観光客向けに英語 UI です。」 |
| 2 | 入力: `I have a headache since this morning.` | — | 「英語で入力します。」 |
| 3 | 送信 | 英語の推奨・注意 | 「Amazon Translate が裏で日本語処理に連携し、英語で返します。」 |

---

## サブシナリオ — C: 受診勧奨（安全設計）20秒版

**用途**: 時間が余った場合 or 審査員の安全性質問への実演。

| Step | 操作 | 期待画面 | 話すセリフ |
|------|------|----------|------------|
| 1 | 入力: `激しい胸の痛みと息苦しさがあります。` | — | 「危険キーワードを含む例です。」 |
| 2 | 送信 | **受診勧奨 / Emergency** カード | 「OTC を出さず、医療機関受診を優先します。診断ではありません。」 |

---

## AWS 機能の指差し説明ポイント

| タイミング | サービス | 指差し・言い回し |
|------------|----------|------------------|
| 英語切替後 | **Amazon Translate** | 「非日本語は Translate が AWS ステージングの翻訳エンジンです。」 |
| 音声ボタン | **Amazon Polly** | 「読み上げは Polly。本番 GCP では Google Cloud TTS です。」 |
| アーキ説明時 | **ECS Fargate + WAF + ALB** | 「ブラウザのリクエストは WAF と ALB を経て ECS に届きます。」 |
| 技術 FAQ 入力時 | **Bedrock KB** | 「Concierge の技術質問は Bedrock Knowledge Base の RAG を試験中です。」 |
| 静的 CSS 読込 | **CloudFront + S3** | 「JS/CSS は CloudFront 経由。DevTools の Network で CDN URL を見せられる。」 |
| デプロイ話 | **CodePipeline** | 「GitHub main の push で CodeBuild が ECR に載せ ECS を更新します。」 |

**言わないこと**: Personalize / ElastiCache は **Phase 4・未本番** — 「将来」と言う。

---

## 既知リスクとフォールバック

| リスク | 症状 | フォールバック |
|--------|------|----------------|
| ECS 停止 | HTTP 503 | `./scripts/resume-aws-staging.sh` → 30秒待機 → 再試行。ダメなら **録画再生** |
| 会場 Wi-Fi 不安 | タイムアウト | **スマホテザリング** → それも不可なら録画 / スクリーンショット |
| OpenAI API 遅延 | 30秒以上スピナー | サブシナリオB短縮 or 事前録画の該当区間 |
| Polly 失敗 | 音声なし | 「Polly は AWS 側設定。今日は文字表示で、Polly はスライド6で説明」と口頭 |
| 推奨空 | CSV 未マッチ | 別症状 `頭が痛い` に切替（事前リハーサルで確認） |

### 録画・スクリーンショット準備手順

1. ローカルまたはステージング復旧後、メインデモ A を **OBS / Win+G** で 1080p 録画（60〜90秒）
2. ファイル名: `demo-fallback/aws-staging-demo-YYYYMMDD.mp4`
3. スクリーンショット（PNG）:
   - `01-top.png` — トップ画面・β版免責
   - `02-input-ja.png` — 日本語入力中
   - `03-reco-card.png` — 推奨カード
   - `04-polly.png` — 音声読み上げ UI
   - `05-en.png` — 英語 UI
4. 保存先: `docs/planning/aws-contest/demo-fallback/`
5. プレゼン PC に **録画と PNG を両方** コピー

**参考 UI 画像**: `docs/archive/gikushosai/presentation_deck/04-demo.png`、`static/img/about/generated/`（類似トーン）

---

## デモ用アカウント・設定

| 項目 | 値 |
|------|-----|
| ログイン | **不要**（匿名セッション） |
| URL | `https://aws.medicine.yutok.dev` のみ（QR もこの URL のみ） |
| 管理者 | デモでは `/admin` は開かない |
| 下書きメモ（入力文） | メモ帳に3シナリオ分をコピペ用で保持 |

### 入力文クイックコピー

```
昨夜から喉が痛くて、微熱があります。
I have a headache since this morning.
激しい胸の痛みと息苦しさがあります。
```

---

## デモ後の一言（スライド8へつなぐ）

> 「この環境は β版の AWS 試験運用です。7県の高齢者から観光客まで、同じ Web 入口で参考相談できる拡張性を、これから専門家のフィードバックとともに磨いていきます。」

---

## 関連

- [02-presentation-deck.md](02-presentation-deck.md) — スライド7以降
- [04-aws-tech-story.md](04-aws-tech-story.md) — AWS 技術詳細
- [scripts/resume-aws-staging.sh](../../scripts/resume-aws-staging.sh) — ECS 復旧
