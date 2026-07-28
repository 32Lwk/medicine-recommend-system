# データ保存・セキュリティ

## 保存データ

| 種別 | 保存先 | 用途 |
|------|--------|------|
| チャットセッション・メッセージ | PostgreSQL（本番 Neon / ローカル Docker） | 会話履歴・再開 |
| LINE 長期記憶（属性・要約） | 同一 PostgreSQL（`line:{userId}` セッション） | 継続相談の安全性・提案品質 |
| 会話アーカイブ | 同一 PostgreSQL（`message_archive`） | トリム前履歴・バックフィル |
| Web 引き継ぎトークン | 短期保持（ワンタイム） | LINE → Web ブラウザへの相談継続 |
| 実行ログ | Cloud Logging（GCP）/ CloudWatch（AWS） | 障害調査 |
| 分析 JSONL | リポジトリ `log/`（開発・検証） | 品質評価（本番利用者データはマスク方針に従う） |
| OTC 医薬品マスタ | `data/` CSV | ルールベース推奨 |
| Secrets | GCP Secret Manager / AWS Secrets Manager → ECS 注入 | API キー・DB URL（**利用者向け回答に env 名は出さない**） |

## 利用者データの扱い

- 症状・属性（年齢・妊娠等）は推奨精度のためセッションに保持
- **チャット内容の保存先**: PostgreSQL（本番 Neon）。メッセージ履歴はセッション単位で DB に保存
- **プライバシー**: 個人情報の取扱い詳細は `docs/public/プライバシーポリシー.md` を正本とする
- **原則収集しない情報**: 氏名・住所・電話番号など、個人を直接特定できる情報（プライバシーポリシー第2条）
- 管理画面（admin_chat）からオペレーターがセッション閲覧可能（試験運用）
- 入力ブロック: 脅迫・違法薬物・システム abuse 等はカテゴリ別応答（`input_block_responses`）

## Web と LINE の保存の違い

| 観点 | Web ブラウザ | LINE |
|------|-------------|------|
| セッション ID | 数値 sid（例: `sess-...`） | `line:{userId}` 形式 |
| 会話履歴 | PostgreSQL に保存 | 同一 DB。表示用は最大 24 件に trim |
| 長期記憶（属性・要約） | **なし**（引き継ぎなしの場合） | あり（プロファイル・相談要約） |
| Web 引き継ぎ後 | `handoff_from_line` で LINE 側記憶を参照 | オーナーは LINE セッションのまま |
| 削除依頼 | 第7条の連絡先、または LINE 経由でチャット内依頼 | チャット内で相談記憶・属性の削除依頼可 |
| ホスティング | GCP 本番 / AWS ステージング両方 | **GCP 本番のみ**（Webhook 経路） |

## 公開 Web の境界

- `/health` — `status`, `git_commit` のみ（軽量プローブ）
- `/health/aws` — 機能フラグ名相当の情報（Translate/Polly 等の**利用有無**）。環境変数そのものは返さない
- 管理画面・API キー・DATABASE_URL は外部非公開

## クロスクラウド

- **GCP 本番** と **AWS ステージング** は DB・ログは別。画像 CDN（R2）のみ共通 URL 可
- LINE Webhook は GCP Cloud Run 上の同一アプリ（AWS LINE 専用改修なし）

## 横断 FAQ（データ × プライバシー）

Concierge が「保存先」と「プライバシーポリシー」をまたぐ質問に答えるときの要点。

- **保存の事実** → 本ドキュメント（04）を根拠
- **取得・利用目的・削除権** → `docs/public/プライバシーポリシー.md` を根拠（条項の paraphrase は避け、direct intent では全文参照）
- **運営者の氏名・所属** → チャット上では開示しない（`00-disclosure-policy.md`）。問い合わせ窓口はプライバシーポリシー第7条・運営者情報 doc の連絡先

---

## Q: チャットの内容はどこに保存されますか

<!-- rag-keywords: チャット 保存 どこ PostgreSQL Neon データベース 履歴 メッセージ -->

**回答要点**

- チャットセッションとメッセージ履歴は **PostgreSQL**（本番は Neon、ローカルは Docker Postgres）に保存
- Web も LINE も同一 DB だが、セッション ID の形式と長期記憶の有無が異なる
- 実行ログは GCP 本番 = Cloud Logging、AWS ステージング = CloudWatch Logs
- **関連**: `06-line-gcp-path.md`（LINE 経路）

## Q: 症状や年齢などの情報は保存されますか（プライバシー）

<!-- rag-keywords: 症状 年齢 属性 保存 プライバシー 個人情報 妊娠 アレルギー -->

**回答要点**

- **What**: 推奨精度のため、ユーザーが入力した症状・属性（年齢層・性別・妊娠/授乳・アレルギー等）をセッションに保持
- **Why**: 市販薬推奨の安全性・提案品質のため（プライバシーポリシー第2・3条）
- **LINE 追加**: 属性・相談要約は長期記憶として一定期間保持（継続相談向け）
- **正本**: 取得範囲・利用目的・削除請求は `docs/public/プライバシーポリシー.md` — Concierge は条項を創作せず、direct intent では md 全文を参照
- **関連**: `docs/concierge/rag/technical-security-rag.md`

## Q: チャット保存とプライバシーポリシーの関係

<!-- rag-keywords: チャット 保存 プライバシー ポリシー 横断 データ 個人情報 -->

**回答要点**

- **保存の技術的事実**: PostgreSQL にセッション・メッセージを保存（本ドキュメント）
- **法的・運用上の枠組み**: プライバシーポリシーが取得情報・利用目的・第三者提供・削除権を定義
- **Concierge の答え方**: 技術 FAQ（architecture）では保存先と目的を概要説明。条項の詳細・削除手続きはプライバシーポリシー intent（`doc_privacy`）または ℹ️ モーダル全文へ誘導
- **禁止**: プライバシー条項の要約を LLM が独自に書き換えること（faithfulness guard）

## Q: データの削除はできますか

<!-- rag-keywords: 削除 データ 消して 記憶 属性 相談 依頼 -->

**回答要点**

- **LINE**: チャット内で相談記憶・属性情報の削除を依頼可能（プライバシーポリシー第7条）
- **Web / その他**: 第7条の連絡先（不具合報告フォーム・メール）から開示・訂正・削除を請求
- **技術**: MemoryDeleteAgent が削除意図を処理（プロファイル・要約・アーカイブ対象）
- **正本**: プライバシーポリシー第5・7条

## Q: GCP 本番と AWS ステージングでデータは混在しますか

<!-- rag-keywords: GCP AWS データ 混在 別 データベース ステージング 本番 -->

**回答要点**

- **No**: GCP 本番 DB と AWS ステージング DB は別インスタンス。利用者データは混在しない
- ログも Cloud Logging と CloudWatch Logs で分離
- 共通なのは医薬品画像 CDN（Cloudflare R2）の URL のみ
- **関連**: `01-cross-cloud-architecture.md`

## Q: API キーや DB 接続情報は利用者に見えますか

<!-- rag-keywords: API キー 秘密 シークレット DATABASE 接続 漏洩 セキュリティ -->

**回答要点**

- **No**: Secrets は Secret Manager 経由でサーバに注入。利用者向け API やチャット回答には出さない
- `/health` は稼働状態と git commit のみ。`/health/aws` は Translate/TTS 等の**利用有無**のみ
- Concierge 出力は env 名・「設定を参照しました」等のメタ表現をサニタイズ
- **関連**: `00-disclosure-policy.md`
