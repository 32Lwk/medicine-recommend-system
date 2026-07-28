# 技術選定 — 横断 Decision FAQ（RAG 用）

> **目的**: `08-technical-decisions.md`（What/Why 要約）と `12-technical-faq-rag.md`（想定 Q）を補完する、**trade-off 比較 + 例外** の横断 SSOT。
> ユーザー向け回答では env 名を出さない。

---

## 比較表（主要 trade-off）

| 決定領域 | 候補 A | 候補 B | 採用 | 主な理由 | 却下・非既定の理由 |
|----------|--------|--------|------|----------|-------------------|
| Concierge RAG | Bedrock Managed KB | Local RAG | **Local RAG** | OpenSearch OCU $0、GCP/AWS 共通化 | Managed KB は OCU 常時課金・GCP 不可 |
| Medicine RAG | Bedrock KB | Local RAG | **Local RAG** | 同上 + Git 管理コーパス | 同上 |
| retrieve 方式 | BM25 のみ | BM25 + embedding | **ハイブリッド** | paraphrase 耐性 | BM25 のみは言い換え弱い |
| 本番 compute | AWS ECS / Render | GCP Cloud Run | **GCP Cloud Run** | 既存運用・Neon 連携 | — |
| ステージング | GCP dev | AWS ECS | **AWS ECS** | Translate/Polly/Bedrock 試験 | — |
| 翻訳 GCP | Google Translate | DeepL | **DeepL** | 品質・既存契約 | — |
| 翻訳 AWS | DeepL | Amazon Translate | **Translate** | AWS ネイティブ統合 | — |
| 画像 CDN | S3+CloudFront | Cloudflare R2 | **R2** | クロスクラウド共通・低コスト | — |
| static CDN | R2 | S3+CloudFront | **CloudFront（AWS）** | ステージング deploy 連動 | 画像とは役割分担 |
| セッション DB | RDS / Supabase | Neon | **Neon（GCP 本番）** | Cloud Run 相性 | AWS ステージングは別 DB |
| 推奨エンジン | LLM-only | ルール+LLM | **ルール+LLM** | hallucination 防止 | LLM-only は薬名リスク |
| Git 正本 | GitLab | GitHub | **GitHub** | CI/deploy 正本 | GitLab はミラー |
| 法務 doc | RAG chunk | md 全文 | **全文（direct）** | 条項精度 | RAG paraphrase リスク |
| CHANGELOG | 全文 index | digest のみ | **digest のみ** | retrieve ノイズ | 全文は重複多い |
| 医療 NLP GCP | Comprehend Medical | router+NER | **router+NER** | AWS 非依存 | Comprehend は AWS 専用 |
| 医療 NLP AWS | なし | Comprehend Medical | **任意** | クエリ拡張 | 失敗時はスキップ |
| 表示順 | スコアのみ | Personalize rerank | **スコア+Personalize（試験）** | 将来パーソナライズ | campaign データ待ち |
| embedding | Bedrock Titan | OpenAI | **OpenAI** | 品質・既存 API | — |

内部網羅: `docs/concierge/technical/research/decisions-matrix.md`

---

## Q: Local RAG vs Bedrock KB — どちらを選ぶべきか

<!-- rag-keywords: Local RAG Bedrock KB 比較 選ぶ trade-off OpenSearch コスト -->

**回答要点**

| 観点 | Local RAG | Bedrock Managed KB |
|------|-----------|-------------------|
| 月額コスト | ~$6–9（embed） | OpenSearch OCU 常時（旧 ~$700/月） |
| GCP 本番 | ✅ 利用可 | ❌ AWS 専用 |
| コーパス更新 | Git push + index rebuild | S3 sync + ingestion |
| ops 負荷 | index ビルド必要 | Managed（ingestion 429 等あり） |
| **現行既定** | **両環境** | 比較・復旧用のみ |

**この場合は別 doc を参照**

- 運用 GO 条件 → `docs/ops/LOCAL_RAG.md`
- 復旧 → `docs/ops/AWS_BEDROCK_KB.md`
- コード分岐 → `src/services/bedrock_kb_retrieve.py`

**答えないこと**

- 具体的 env 名・KB ID の列挙

---

## Q: ハイブリッド RAG の alpha（BM25 vs embedding 重み）はなぜ 0.4 か

<!-- rag-keywords: hybrid alpha BM25 embedding 重み 0.4 チューニング -->

**回答要点**

- **What**: BM25 重み 0.4、残り cosine（既定）。Concierge / Medicine で namespace 別チューニング可
- **Why**: 技術 FAQ は固有名詞・略語（BM25）と言い換え（embed）の両方が必要。eval fixture で pass 率と P95 を確認
- **調整**: eval 失敗時に boost 調整。利用者向けには「キーワードと意味の両方」と説明

**この場合は別 doc を参照**

- 変数一覧 → `docs/ops/LOCAL_RAG.md` 環境変数表
- benchmark → `scripts/local_rag_retrieve_benchmark.py`

**答えないこと**

- `LOCAL_RAG_HYBRID_ALPHA` 等の env 名

---

## Q: Neon を GCP 本番 DB にした理由（AWS RDS ではない）

<!-- rag-keywords: Neon PostgreSQL GCP 本番 DB RDS 選定 -->

**回答要点**

- **Why Neon**: Cloud Run + サーバーレス Postgres、接続プール、運用軽量
- **Why not 統一 DB**: クロスクラウド構成上、AWS ステージングは別 DB。データ混在防止
- **Trade-off**: ベンダー分散（Neon + AWS RDS/Postgres）

**この場合は別 doc を参照**

- 保存先一覧 → `04-data-security.md`

**答えないこと**

- 接続 URL・プロジェクト ID

---

## Q: R2 を画像 CDN にした理由（S3 ではない）

<!-- rag-keywords: R2 S3 画像 CDN 選定 Cloudflare クロスクラウド -->

**回答要点**

- **Why R2**: GCP/AWS **同一 URL**、低コスト、医薬品画像のみに特化
- **S3+CloudFront の役割**: AWS ステージング **static**（JS/CSS）— デプロイパイプラインと一体
- **Trade-off**: Cloudflare 別管理

**この場合は別 doc を参照**

- 運用 → `docs/ops/CLOUDFLARE_R2_IMAGES.md`

**答えないこと**

- バケット・API トークン

---

## Q: GitHub 正本に戻した理由（GitLab から）

<!-- rag-keywords: GitHub GitLab 正本 移行 復旧 CI deploy -->

**回答要点**

- **2026-07 復旧後**: GitHub = PR / CI / Cloud Build / CodeBuild トリガー
- **GitLab**: ミラーのみ（push 可、CI/デプロイは走らない）
- **Why**: 正本一本化、Issues / `gh` CLI、デプロイ自動化

**この場合は別 doc を参照**

- 履歴 → `docs/ops/GITLAB_TEMPORARY_MIGRATION.md` §10

**答えないこと**

- GitLab runner / CI 変数の内部設定

---

## Q: Comprehend Medical を GCP で使わない理由

<!-- rag-keywords: Comprehend Medical GCP 使わない NER 代替 router -->

**回答要点**

- **AWS のみ**: Comprehend Medical API は AWS 専用・リージョン制約
- **GCP 代替**: Medicine QA router + ルールベース NER で同等のクエリ拡張
- **Trade-off**: AWS ステージングのみ任意有効。失敗してもパイプライン継続

**この場合は別 doc を参照**

- 実装 → `src/services/comprehend_medical.py`
- LOCAL_RAG → `docs/ops/LOCAL_RAG.md` COMPREHEND 行

**答えないこと**

- リージョン設定の内部値

---

## Q: Personalize が推奨スコアリングを置き換えない理由

<!-- rag-keywords: Personalize スコアリング 置き換え rerank 表示順 ルールベース -->

**回答要点**

- **What**: Personalize は **表示順 rerank** とイベント蓄積のみ
- **Why not 置換**: 薬名決定はルールベース（hallucination 防止）。Personalize は UX 試験
- **現状**: campaign データ蓄積中

**この場合は別 doc を参照**

- 実装 → `src/services/personalize_ranker.py`

**答えないこと**

- campaign / dataset 内部名

---

## Q: 法務 direct vs RAG 横断 — いつどちらか

<!-- rag-keywords: 法務 direct RAG 横断 プライバシー 利用規約 使い分け -->

**回答要点**

| 質問タイプ | 方式 | 例 |
|------------|------|-----|
| 条項そのもの | **direct 全文** | 「プライバシーポリシーを見せて」 |
| 横断説明 | **RAG 補助** | 「データはどこに保存？プライバシーは？」 |
| sanitize | 出力後段 | env 除去・断言緩和 |

**この場合は別 doc を参照**

- boundary → `scripts/eval_concierge_boundary.py`
- メンテ → `docs/ops/CONCIERGE_TECH_FAQ_MAINTENANCE.md` §6

**答えないこと**

- 法務条文の要約・改変

---

## Q: Medicine RAG が推奨順位を変えない理由

<!-- rag-keywords: Medicine RAG 推奨 順位 スコアリング 変更しない Phase A -->

**回答要点**

- **原則**: RAG は Ask / Explanation **プロンプト注入**のみ
- **Why**: 安全性 SSOT。スコアリングは `PhysicalOrchestrator` + CSV
- **検証**: `eval_medicine_kb.py` / `eval_medicine_qa_e2e.py` で GO 条件

**この場合は別 doc を参照**

- Phase A–C → `docs/ops/LOCAL_RAG.md`
- routing → `docs/dev/MEDICINE_QA_ROUTING.md`

**答えないこと**

- 内部 pass 率閾値の詳細

---

## Q: embed 失敗時に BM25 のみで続行する理由

<!-- rag-keywords: fallback BM25 embed 失敗 継続 LOCAL_RAG_FALLBACK -->

**回答要点**

- **What**: OpenAI embed 障害時、retrieve は BM25 のみで継続（回答停止しない）
- **Why**: 可用性優先。技術 FAQ は BM25 でも多くは命中
- **Trade-off**: 言い換え耐性は一時低下

**この場合は別 doc を参照**

- Fallback 節 → `docs/ops/LOCAL_RAG.md`

**答えないこと**

- fallback フラグの env 名

---

## 関連 SSOT

| ファイル | 役割 |
|----------|------|
| `08-technical-decisions.md` | What/Why/Trade-off/現状（項目別） |
| `12-technical-faq-rag.md` | 想定 Q + 例外（25+ 件） |
| `docs/ops/LOCAL_RAG.md` | Local RAG 運用・eval・コスト |
| `research/decisions-matrix.md` | 内部比較表（更新トリガ付き） |

## 更新トリガ

- infra / provider 切替（cloudbuild / buildspec / ops doc）
- eval 閾値変更・retrieve boost 調整
- SSOT 08 / 12 の項目追加時 — 本ファイルの比較表を同期
