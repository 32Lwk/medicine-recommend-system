# データ保存・セキュリティ

## 保存データ

| 種別 | 保存先 | 用途 |
|------|--------|------|
| チャットセッション・メッセージ | PostgreSQL（本番 Neon / ローカル Docker） | 会話履歴・再開 |
| 実行ログ | Cloud Logging（GCP）/ CloudWatch（AWS） | 障害調査 |
| 分析 JSONL | リポジトリ `log/`（開発・検証） | 品質評価（本番利用者データはマスク方針に従う） |
| OTC 医薬品マスタ | `data/` CSV | ルールベース推奨 |
| Secrets | GCP Secret Manager / AWS Secrets Manager → ECS 注入 | API キー・DB URL（**利用者向け回答に env 名は出さない**） |

## 利用者データの扱い

- 症状・属性（年齢・妊娠等）は推奨精度のためセッションに保持
- 管理画面（admin_chat）からオペレーターがセッション閲覧可能（試験運用）
- 入力ブロック: 脅迫・違法薬物・システム abuse 等はカテゴリ別応答（`input_block_responses`）

## 公開 Web の境界

- `/health` — `status`, `git_commit` のみ（軽量プローブ）
- `/health/aws` — 機能フラグ名相当の情報（Translate/Polly 等の**利用有無**）。環境変数そのものは返さない
- 管理画面・API キー・DATABASE_URL は外部非公開

## クロスクラウド

- **GCP 本番** と **AWS ステージング** は DB・ログは別。画像 CDN（R2）のみ共通 URL 可
- LINE Webhook は GCP Cloud Run 上の同一アプリ（AWS LINE 専用改修なし）
