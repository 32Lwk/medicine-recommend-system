# LINE と GCP 本番経路

## LINE のホスティング

- **LINE Messaging API Webhook** → **GCP Cloud Run** 上の `medicine.yutok.dev` 同一アプリ
- AWS ステージング（`aws.medicine.yutok.dev`）は Web 試験用。**LINE 専用の AWS 改修は行わない**
- 医薬品画像 URL のみ Cloudflare R2（`images.yutok.dev/otc/`）で GCP/AWS 共通

## Webhook 処理

1. 署名検証 → 200 即返し
2. 非同期で `handle_chat_post_async` → Chat Pipeline v2 / Concierge / Physical 等
3. 返信: テキスト / Flex（推奨カード・status カード）
4. Concierge 技術 FAQ も **Web と同じ** `try_concierge_response` 経路（深掘り・i18n 共通）

## LINE 固有 UX

- Flex 文字数上限 → 長文は切り詰め + Web チャット誘導
- 「詳しく」等があれば Web と同様 deep モード（medium）
- 言語: LINE プロフィール + メッセージから `detected_language` → Translate/DeepL

## GCP 本番 vs AWS ステージング（利用者向け説明）

| | GCP 本番 + LINE | AWS ステージング |
|--|-----------------|------------------|
| URL | medicine.yutok.dev | aws.medicine.yutok.dev |
| 翻訳 | DeepL | Amazon Translate |
| TTS | Web Speech API | Amazon Polly |
| ホスティング | Cloud Run | ECS Express |
