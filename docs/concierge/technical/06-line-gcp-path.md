# LINE と GCP 本番経路

## LINE のホスティング

- **LINE Messaging API Webhook** → **GCP Cloud Run** 上の `medicine.yutok.dev` 同一アプリ
- AWS ステージング（`aws.medicine.yutok.dev`）は Web 試験用。**LINE 専用の AWS 改修は行わない**
- 医薬品画像 URL のみ Cloudflare R2（`images.yutok.dev/otc/`）で GCP/AWS 共通

## Webhook 処理（受信から返信まで）

1. **POST `/line/webhook`** — LINE Platform からイベント受信
2. **署名検証** — Channel Secret で `X-Line-Signature` を検証。失敗時は 403
3. **即 200 返却** — LINE の再送タイムアウトを避けるため、検証成功後すぐ応答
4. **去重** — 同一 `webhookEventId` の重複イベントをスキップ（プロセス内 + DB）
5. **非同期処理** — 専用スレッド上のイベントループで `process_line_events` を実行
6. **会話パイプライン** — `handle_chat_post_async` → Chat Pipeline v2 → Physical / Concierge / Emotional 等
7. **返信** — LINE Messaging API でテキスト / Flex（推奨カード・status カード）を push
8. **Concierge 技術 FAQ** — Web と同じ `try_concierge_response` 経路（深掘り・i18n 共通）

## LINE 固有 UX

- Flex 文字数上限 → 長文は切り詰め + Web チャット誘導
- 「詳しく」等があれば Web と同様 deep モード（medium）
- 言語: LINE プロフィール + メッセージから `detected_language` → DeepL（GCP 本番）
- ローディング表示: 長処理中は LINE ローディングアニメーションを維持（最大約 60 秒）

## LINE と Web の機能差（利用者向け）

| 観点 | LINE | Web ブラウザ |
|------|------|-------------|
| 入口 URL | LINE アプリ内 | medicine.yutok.dev / aws.medicine.yutok.dev |
| ホスティング | GCP Cloud Run 本番のみ | GCP 本番 + AWS ステージング |
| セッション | `line:{userId}` | 数値 sid |
| 長期記憶 | 属性・相談要約を保持 | 引き継ぎなしならなし |
| Web 引き継ぎ | ワンタイムトークンでブラウザへ | トークン redeem で履歴・属性を引き継ぎ |
| 技術 FAQ | 同一 Concierge 経路 | 同一 |
| 読み上げ | LINE 内テキスト中心 | Web UI の TTS ボタン（GCP = Google TTS） |
| 表示履歴上限 | 直近 24 件（trim） | セッション存続中はより多く保持 |

## GCP 本番 vs AWS ステージング（利用者向け説明）

| | GCP 本番 + LINE | AWS ステージング |
|--|-----------------|------------------|
| URL | medicine.yutok.dev | aws.medicine.yutok.dev |
| LINE | ○ Webhook 受信 | ×（Web 試験のみ） |
| 翻訳 | DeepL | Amazon Translate |
| TTS | Google Cloud Text-to-Speech（POST /api/tts） | Amazon Polly |
| ホスティング | Cloud Run | ECS Express |

## 横断 FAQ（LINE × データ × プライバシー）

- LINE userId は **生のまま保存せず**、ハッシュ化または仮名 ID として扱う（プライバシーポリシー第2条）
- 相談要約・属性の長期保存は LINE 連携利用時のみ（Web のみセッションには紐づかない）
- 削除依頼は LINE チャット内または第7条連絡先 — 詳細は `doc_privacy` intent

---

## Q: LINE からのメッセージはどのサーバで処理されますか

<!-- rag-keywords: LINE サーバ 処理 どこ Cloud Run GCP webhook 経路 -->

**回答要点**

- LINE Messaging API の Webhook は **GCP Cloud Run** 上の本番アプリ（medicine.yutok.dev）が受信
- AWS ステージングには LINE Webhook を向けない方針
- 署名検証後に即 200 を返し、会話処理はバックグラウンドで実行
- **関連**: `01-cross-cloud-architecture.md`

## Q: LINE と Web でチャットの保存は同じですか

<!-- rag-keywords: LINE Web 保存 違い 同じ データ セッション 長期記憶 -->

**回答要点**

- **共通**: いずれも PostgreSQL に保存
- **相違**: LINE は `line:{userId}` セッション + 長期記憶（属性・要約）。Web のみセッションには長期記憶なし
- **引き継ぎ**: LINE → Web ワンタイムトークンで履歴・属性をブラウザへコピー。Web 側の更新は LINE オーナーへ非同期反映可
- **関連**: `04-data-security.md`

## Q: LINE で技術 FAQ（インフラの質問）は答えられますか

<!-- rag-keywords: LINE 技術 FAQ インフラ Concierge 構成 デプロイ -->

**回答要点**

- **Yes**: Web と同一の Concierge 経路（`try_concierge_response`）
- Flex 文字数制限により長文は切り詰め。深掘りは「詳しく」等のトリガーで medium モード
- 長い説明が必要な場合は Web チャットへの誘導文を付けることがある
- **関連**: `00-disclosure-policy.md`（深掘りルール）

## Q: LINE から Web ブラウザに相談を引き継げますか

<!-- rag-keywords: LINE Web 引き継ぎ ブラウザ トークン 継続 handoff -->

**回答要点**

- **What**: ワンタイムトークンで LINE セッションのスナップショット（履歴・属性・要約）を Web へ
- **Why**: 大画面 UI・TTS・長文表示のため（プライバシーポリシー第2・3条）
- トークンは短期・一回限り。redeem 後に新 Web セッションを作成
- **関連**: `04-data-security.md`

## Q: LINE Webhook が失敗したときはどうなりますか

<!-- rag-keywords: LINE webhook 失敗 エラー 署名 再送 503 -->

**回答要点**

- 署名不一致 → 403（処理しない）
- Webhook 無効または Channel Secret 未設定 → 503
- 処理成功後は 200 を先に返すため、内部エラーは LINE 再送とは独立（去重で二重応答を防止）
- 利用者向け回答では内部エラーコードや設定名は述べない
