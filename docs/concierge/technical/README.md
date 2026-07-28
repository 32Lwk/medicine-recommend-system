# Concierge 技術 FAQ — SSOT 索引

Amazon Q 型の技術回答の**唯一の根拠**。Concierge architecture 深掘りは `src/content/concierge_tech_reference.py` が本ディレクトリを自動読込する。

## ドキュメント一覧

| ファイル | 内容 |
|----------|------|
| [00-disclosure-policy.md](00-disclosure-policy.md) | 開示ポリシー（公開 OK / 深掘りは聞かれたとき / env メタ禁止） |
| [01-cross-cloud-architecture.md](01-cross-cloud-architecture.md) | GCP 本番 / AWS ステージング / R2 / LINE 概要 |
| [02-chat-pipeline-agents.md](02-chat-pipeline-agents.md) | Chat Pipeline v2・エージェント役割 |
| [03-deployment-operations.md](03-deployment-operations.md) | デプロイ・CI/CD・Bedrock KB・ロールバック |
| [04-data-security.md](04-data-security.md) | データ保存・セキュリティ境界 |
| [05-chat-pipeline-v2-flags.md](05-chat-pipeline-v2-flags.md) | v2 / RECO_* / AWS 機能フラグ |
| [06-line-gcp-path.md](06-line-gcp-path.md) | LINE → GCP Cloud Run 経路 |
| [07-observability-ops.md](07-observability-ops.md) | `/health`・ログ・運用確認 |
| [11-app-mission-and-status.md](11-app-mission-and-status.md) | 作成意図・理由・β現状・将来像・境界 |
| [../rag/app-overview-rag.md](../rag/app-overview-rag.md) | **アプリ概要 RAG FAQ**（20+ 想定質問・境界） |
| [08-technical-decisions.md](08-technical-decisions.md) | 主要技術選定の Why |
| [09-glossary.md](09-glossary.md) | 技術用語集（ユーザー向け） |
| [10-agent-routing-rationale.md](10-agent-routing-rationale.md) | マルチエージェント分岐の設計意図 |
| [12-technical-faq-rag.md](12-technical-faq-rag.md) | **RAG 最適化 FAQ**（想定質問・キーワード・回答要点・例外） |
| [13-meta-kb-unified-index.md](13-meta-kb-unified-index.md) | **Meta KB 統合索引**（レイヤ・intent・例外哲学） |
| [../rag/enterprise-overview-rag.md](../rag/enterprise-overview-rag.md) | **企業・B2B RAG FAQ**（導入・データ・制限・法務 cross-link） |
| [../rag/legal-crossdoc-rag.md](../rag/legal-crossdoc-rag.md) | **法務横断 RAG FAQ**（規約×プライバシー・免責・人間案内） |
| [../rag/technical-decisions-rag.md](../rag/technical-decisions-rag.md) | **横断 Decision FAQ**（trade-off 比較表 + Q 形式） |
| [../rag/technical-pipeline-rag.md](../rag/technical-pipeline-rag.md) | **パイプライン・ルーティング統合 FAQ**（エージェント・SSE・例外） |
| [../rag/technical-security-rag.md](../rag/technical-security-rag.md) | **セキュリティ横断 RAG**（保存×プライバシー・開示境界・LINE） |

## RAG 最適化方針

- 技術 SSOT は `## Q:` 形式 + `<!-- rag-keywords: ... -->` で BM25 向けに索引
- チャンク: `###` 単位分割 + `[section]` / `[keywords]` プレフィックス（`local_rag_index.py`）
- `12-technical-faq-rag.md` — 想定質問・回答要点の RAG 専用 SSOT（深い Why）
- `rag/technical-security-rag.md` — データ保存・プライバシー・LINE・開示境界の横断 FAQ（12+ 問）
- `rag/enterprise-overview-rag.md` — 企業・B2B・データ取り扱い・制限・窓口（15 問）
- `rag/legal-crossdoc-rag.md` — 規約×プライバシー横断・免責・人間 escalations（12 問）
- `13-meta-kb-unified-index.md` — public / rag / technical / ops レイヤと intent 索引
- `docs/concierge/rag/technical-pipeline-rag.md` — パイプライン・ルーティング・SSE・例外の統合 FAQ
- `research/` は RAG index から除外（内部メモのノイズ防止）
- retrieve クエリは topic 限定ヒント（汎用「デプロイ」語で ops doc に偏らない）
- 深い Why は `12-technical-faq-rag.md` と `08-technical-decisions.md` を正本とする

## public ドキュメント（Amazon Q 型メタ KB）

| ファイル | intent |
|----------|--------|
| `docs/public/アプリ概要.md` | doc_app_overview |
| `docs/public/プライバシーポリシー.md` | doc_privacy（直接 intent = 全文参照） |
| `docs/public/免責事項・利用規約.md` | doc_terms |
| `docs/public/医薬品相談先.md` | doc_consultation |
| `docs/public/運営者情報.md` | doc_operator 補助 |
| `docs/public/会社向け概要書類.md` | enterprise（RAG） |
| `docs/public/企業向け簡略版概要資料.md` | enterprise（RAG） |

## research/（開発者向け調査メモ）

R0 リサーチ成果物。回答 SSOT ではない — `research/tech-stack-inventory.md` 等。

## メンテナンス

| イベント | 更新 |
|----------|------|
| インフラ変更 | 該当 `.md` + `docs/ops/` |
| 機能リリース | `CHANGELOG.md` → `python scripts/write_changelog_digest.py` |
| KB 反映（Support 後） | `scripts/sync-concierge-kb-to-s3.sh` → ingestion |

## 検証

```bash
./scripts/verify-concierge-ssot.sh
./scripts/concierge-technical-faq-contract.sh
./scripts/run_concierge_comprehensive_eval.sh
# ライブ品質（OPENAI_API_KEY）:
RUN_LIVE_QUALITY=1 RUN_LIVE_JUDGE=1 ./scripts/run_concierge_comprehensive_eval.sh
```

詳細: [`docs/ops/CONCIERGE_TECH_FAQ_MAINTENANCE.md`](../../ops/CONCIERGE_TECH_FAQ_MAINTENANCE.md)
