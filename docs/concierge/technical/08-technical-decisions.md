# 技術選定 — 主要な Why（Concierge SSOT）

各項目は **What / Why / Trade-off / 現状** で整理。環境変数名はユーザー向け回答に出さない。

## GCP 本番と AWS ステージングを分けた理由

<!-- rag-keywords: GCP AWS ステージング 本番 分けた 理由 クロスクラウド なぜ 分離 -->

- **What**: 本番 = GCP Cloud Run（medicine.yutok.dev）、ステージング = AWS ECS Express Gateway（aws.medicine.yutok.dev）
- **Why**: 本番安定性を最優先し、AWS 固有機能（Translate / Polly / Bedrock KB / ElastiCache / Personalize / Comprehend Medical 等）の試験をステージングに閉じ込める
- **Trade-off**: クロスクラウド運用・ドキュメント二系統の保守コスト
- **現状**: 画像 CDN（R2）のみ共通 URL。DB・ログ・Secrets は環境別。GCP 本番は DeepL + Cloud TTS + Local RAG

## Local RAG（GCP 本番・AWS 共通・既定）

<!-- rag-keywords: Local RAG Bedrock KB なぜ OpenSearch コスト BM25 embedding ハイブリッド -->

- **What**: リポジトリ内 Markdown + JSON（`build/medicine` + Concierge SSOT）から BM25 + OpenAI embedding ハイブリッドで retrieve
- **Why**: Bedrock Managed KB の OpenSearch OCU コスト回避（~$0/月 vs 旧 KB ~$700/月）、**GCP/AWS で同一実装**、コーパスを Git で管理
- **Trade-off**: embedding index のビルド・運用が必要。Managed KB より ops 負荷
- **現状**: GCP 本番・AWS ステージングとも `local` が既定。Bedrock KB は復旧スクリプト残存・比較用

## Bedrock KB を使う場合（例外）

<!-- rag-keywords: Bedrock KB いつ 使う 切替 Managed KB 復旧 -->

- **What**: AWS マネージドナレッジベース（OpenSearch Serverless 上）への retrieve
- **When**: ステージングで Managed retrieve の A/B 比較、旧 KB 復旧手順の検証、OpenSearch OCU 再開後の再評価
- **Why not 既定**: OCU 常時課金・GCP 本番では利用不可（AWS 専用）
- **Trade-off**: ops 簡素化 vs 月額コスト・ベンダーロックイン
- **現状**: 本番 GCP / ステージング AWS とも Local RAG 既定。詳細は `docs/ops/LOCAL_RAG.md`

## ハイブリッド RAG（BM25 + embedding）

<!-- rag-keywords: ハイブリッド RAG BM25 embedding cosine alpha 検索 -->

- **What**: BM25（キーワード）と OpenAI embedding cosine（意味類似）を重み付け合成して chunk をランク
- **Why**: 専門用語・略語は BM25、言い換え・口語は embedding でカバー。単独 BM25 より paraphrase 耐性
- **Trade-off**: クエリごとに embed API 呼び出し（~$4–5/月 @10k retrieve/日）。失敗時は BM25 のみ fallback
- **現状**: Concierge = `text-embedding-3-small`、Medicine = `text-embedding-3-large`（任意 hybrid rerank）。alpha 既定 0.4（BM25 重み）

## ルールベース推奨 + LLM 説明

<!-- rag-keywords: ルールベース LLM 薬 スコアリング hallucination PhysicalOrchestrator -->

- **What**: 市販薬候補は CSV スコアリング、LLM は triage・説明・Concierge
- **Why**: 薬名 hallucination 防止、薬事的根拠の説明可能性
- **Trade-off**: 柔軟な自然言語だけでは候補選定できない edge case あり
- **現状**: `PhysicalOrchestrator` + `data/` CSV が正本。RAG は説明・Q&A 層のみ（スコアリングは変更しない）

## Neon PostgreSQL（セッション DB）

<!-- rag-keywords: Neon PostgreSQL データベース サーバーレス セッション 履歴 -->

- **What**: サーバーレス PostgreSQL（Neon）でチャットセッション・メッセージ履歴を保存
- **Why**: Cloud Run との相性（接続プール・スケール-to-zero）、運用負荷の低さ、本番 DB として実績
- **Trade-off**: AWS RDS 等への統一はせず GCP 本番専用 DB。ステージング AWS は別 DB インスタンス
- **現状**: 本番 Neon、ローカル Docker Postgres で同等スキーマ。GCP/AWS で DB は混在しない

## Cloudflare R2 画像 CDN

<!-- rag-keywords: Cloudflare R2 画像 CDN images.yutok.dev OTC 医薬品 -->

- **What**: OTC 画像を `https://images.yutok.dev/otc/{slug}.webp` で配信
- **Why**: GCP/AWS 共通の低コスト CDN、S3+CloudFront と役割分担（static は AWS CF、画像は R2）
- **Trade-off**: 別ベンダー管理（Cloudflare ダッシュボード）
- **現状**: 本番・ステージング共通。未配置画像は UI プレースホルダー

## GitHub 正本 + GitLab ミラー

<!-- rag-keywords: GitHub GitLab 正本 ミラー origin リポジトリ CI deploy -->

- **What**: `origin` = GitHub（32Lwk/medicine-recommend-system）、GitLab = バックアップミラー
- **Why**: CI/CD・Issues・デプロイトリガーの正本を GitHub に集約（2026-07 復旧後）
- **Trade-off**: 双方向 sync は手動（GitHub 障害時フェイルオーバー用）
- **現状**: PR / deploy / CodeBuild は GitHub main。GitLab push はミラーのみ（CI/デプロイは走らない）

## Amazon Comprehend Medical（AWS ステージング・任意）

<!-- rag-keywords: Comprehend Medical AWS 医療 NLP エンティティ 症状 薬剤 -->

- **What**: AWS 医療 NLP で症状・薬剤エンティティ抽出（Medicine QA クエリ拡張・ログ分析）
- **Why**: 口語症状の構造化、retrieve クエリ enriched（併用薬・症状名の補完）
- **Trade-off**: AWS 専用・リージョン制約あり。GCP 本番は **router + ルールベース NER** で代替
- **現状**: AWS ステージングのみ任意有効。失敗時は None を返しパイプライン継続

## Amazon Personalize（AWS ステージング・イベント蓄積中）

<!-- rag-keywords: Personalize 推奨 ランキング rerank AWS イベント -->

- **What**: OTC 候補カードの表示順 rerank + クリック等イベント蓄積
- **Why**: 将来的なパーソナライズ表示順の試験（スコアリング本体はルールベースのまま）
- **Trade-off**: campaign データ待ち・AWS 専用。本番 GCP では未使用
- **現状**: イベント送信のみ。ranking campaign はデータ蓄積中

## 法務 doc は RAG ではなく全文参照

<!-- rag-keywords: 法務 プライバシー 利用規約 direct intent 全文 RAG 除外 -->

- **What**: プライバシーポリシー・免責事項等は `generate_doc_answer_text` が md 全文参照
- **Why**: 条項の paraphrase リスク回避、利用者への正確な法務表示
- **Trade-off**: 横断質問（データ×プライバシー等）は RAG 補助可
- **現状**: `doc_privacy` / `doc_terms` 等は RAG スキップ

## CHANGELOG は RAG index から除外

<!-- rag-keywords: CHANGELOG digest RAG 除外 更新履歴 -->

- **What**: `CHANGELOG.md` 全文は index 対象外。要約 digest のみ `doc_changelog` intent で参照
- **Why**: 全文 chunk は retrieve ノイズ・重複が多く精度低下
- **Trade-off**: 細かい commit 履歴は digest 経由のみ
- **現状**: `write_changelog_digest.py` → `static/changelog-digest.json`

## 関連

- RAG 最適化 FAQ: `12-technical-faq-rag.md`
- 横断 decision FAQ: `docs/concierge/rag/technical-decisions-rag.md`
- 比較表（内部）: `research/decisions-matrix.md`
- Local RAG 運用: `docs/ops/LOCAL_RAG.md`
