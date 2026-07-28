# Meta KB 統合索引 — ドキュメントレイヤ・Intent・例外哲学

> Concierge / Local RAG / Bedrock KB 同期の**メタ索引 SSOT**。
> 「どの doc をどの intent で引くか」「例外・境界の優先順位」を一覧化する。
> 個別 FAQ の回答正文は各レイヤの RAG md を正本とする。

---

## 1. ドキュメントレイヤ概要

```
┌─────────────────────────────────────────────────────────────────┐
│  Layer A: public/          利用者向け公開正本（規約・概要）        │
├─────────────────────────────────────────────────────────────────┤
│  Layer B: concierge/rag/   RAG 最適化 FAQ（BM25 + 境界ブロック）   │
├─────────────────────────────────────────────────────────────────┤
│  Layer C: concierge/technical/ 00–12  技術 SSOT・深掘り Why       │
├─────────────────────────────────────────────────────────────────┤
│  Layer D: docs/ops/        運用 Runbook・インフラ手順            │
├─────────────────────────────────────────────────────────────────┤
│  Layer E: docs/dev/        開発者向けパイプライン仕様            │
├─────────────────────────────────────────────────────────────────┤
│  Layer F: research/        内部調査メモ（RAG index 除外）         │
└─────────────────────────────────────────────────────────────────┘
```

| レイヤ | パス | 役割 | RAG 索引 |
|--------|------|------|----------|
| **A public** | `docs/public/*.md` | 規約・ポリシー・概要の**法的・利用者正本** | ✅（path タグ付き） |
| **B rag** | `docs/concierge/rag/*.md` | 想定質問・keywords・**例外・境界**の retrieve 最適化 | ✅ 主索引 |
| **C technical** | `docs/concierge/technical/00–12` | アーキテクチャ・パイプライン・開示ポリシー SSOT | ✅（`## Q:` 形式） |
| **D ops** | `docs/ops/*.md` | デプロイ・KB 同期・ログ分析手順 | ✅ |
| **E dev** | `docs/dev/*.md` | エージェント・ルート仕様 | ✅ |
| **F research** | `docs/concierge/technical/research/` | カバレッジ調査・未確定メモ | ❌ 除外 |

---

## 2. technical SSOT（00–12）一覧

| ID | ファイル | 内容 |
|----|----------|------|
| 00 | [00-disclosure-policy.md](00-disclosure-policy.md) | 開示深度・env 禁止・doc intent 例外 |
| 01 | [01-cross-cloud-architecture.md](01-cross-cloud-architecture.md) | GCP 本番 / AWS ステージング / R2 / LINE |
| 02 | [02-chat-pipeline-agents.md](02-chat-pipeline-agents.md) | Chat Pipeline v2・エージェント |
| 03 | [03-deployment-operations.md](03-deployment-operations.md) | デプロイ・CI/CD・KB 同期 |
| 04 | [04-data-security.md](04-data-security.md) | データ保存・セキュリティ境界 |
| 05 | [05-chat-pipeline-v2-flags.md](05-chat-pipeline-v2-flags.md) | v2 / RECO_* フラグ |
| 06 | [06-line-gcp-path.md](06-line-gcp-path.md) | LINE → GCP 経路 |
| 07 | [07-observability-ops.md](07-observability-ops.md) | health・ログ・運用 |
| 08 | [08-technical-decisions.md](08-technical-decisions.md) | 技術選定 Why |
| 09 | [09-glossary.md](09-glossary.md) | 用語集 |
| 10 | [10-agent-routing-rationale.md](10-agent-routing-rationale.md) | ルーティング設計意図 |
| 11 | [11-app-mission-and-status.md](11-app-mission-and-status.md) | ミッション・β 現状 |
| 12 | [12-technical-faq-rag.md](12-technical-faq-rag.md) | 技術横断 RAG FAQ |
| **13** | **本ファイル** | **Meta KB 統合索引（レイヤ・intent・例外哲学）** |

---

## 3. rag/ レイヤ FAQ 一覧

| ファイル | ドメイン | FAQ 規模（目安） |
|----------|----------|------------------|
| [app-overview-rag.md](../rag/app-overview-rag.md) | アプリ概要・β・対象者 | 20+ |
| [author-mission-rag.md](../rag/author-mission-rag.md) | 作成者・ミッション（公開安全） | 15+ |
| [enterprise-overview-rag.md](../rag/enterprise-overview-rag.md) | **企業・B2B・データ・制限・窓口** | **15** |
| [legal-crossdoc-rag.md](../rag/legal-crossdoc-rag.md) | **規約×プライバシー横断・免責・人間案内** | **12** |
| [technical-decisions-rag.md](../rag/technical-decisions-rag.md) | 技術選定 trade-off |
| [technical-pipeline-rag.md](../rag/technical-pipeline-rag.md) | パイプライン・SSE・例外 |
| [technical-infra-rag.md](../rag/technical-infra-rag.md) | インフラ横断 |
| [technical-security-rag.md](../rag/technical-security-rag.md) | 保存×プライバシー・LINE・開示 |

**chunk 形式**: `## Q:` + `<!-- rag-keywords: ... -->` + 箇条書き + **`例外・境界`**（`local_rag_index.py` が `###` / `## Q:` 単位で分割）。

---

## 4. public/ レイヤ（intent 直結）

| ファイル | intent | 備考 |
|----------|--------|------|
| `docs/public/アプリ概要.md` | doc_app_overview | 一般向け概要 |
| `docs/public/プライバシーポリシー.md` | **doc_privacy** | 全文参照のみ・paraphrase 禁止 |
| `docs/public/免責事項・利用規約.md` | **doc_terms** | 同上・薬機法断言禁止 |
| `docs/public/医薬品相談先.md` | doc_consultation | 受診・相談先 |
| `docs/public/運営者情報.md` | doc_operator 補助 | チャットでは PII 非開示 |
| `docs/public/会社向け概要書類.md` | enterprise（RAG） | B2B 詳細 |
| `docs/public/企業向け簡略版概要資料.md` | enterprise（RAG） | B2B 簡略 |

横断 retrieve 用の濃縮 FAQ → `enterprise-overview-rag.md` / `legal-crossdoc-rag.md`。

---

## 5. ops/ レイヤ

| 例 | 用途 |
|----|------|
| `docs/ops/LOCAL_RAG.md` | Local RAG ビルド・eval |
| `docs/ops/AWS_BEDROCK_KB.md` | KB 同期（レガシー参照） |
| `docs/ops/CONCIERGE_TECH_FAQ_MAINTENANCE.md` | FAQ メンテ手順 |
| `docs/ops/GITLAB_TEMPORARY_MIGRATION.md` | リモート正本 |

`config/concierge_rag_sources.py` の `CONCIERGE_OPS_DOCS` / `CONCIERGE_DEV_DOCS` が同期対象リスト。

---

## 6. Intent ルーティング（Concierge）

**分類器**: `src/services/concierge_intent.py`  
**エージェント**: `src/agents/concierge_agent.py`（`_DOC_REFERENCE_ONLY_INTENTS`）

| intent | 主根拠 | retrieve ヒント | 深掘り |
|--------|--------|-----------------|--------|
| `doc_privacy` | プライバシーポリシー md のみ | `local/public/プライバシー` | 条項創作禁止 |
| `doc_terms` | 利用規約 md のみ | `local/public/免責` | 合法/違法断言禁止 |
| `doc_operator` | 運営者情報 + 窓口 | 運営者・問い合わせ | 個人名は LLM 文に出さない |
| `doc_app_overview` | public 概要 + rag/app-overview | mission / app-overview boost | 概要 2–6 文 → 深掘り |
| `architecture` | 01, 04, rag/infra, rag/security | クロスクラウド | env 名サニタイズ |
| `capabilities` | 02, 11, rag/pipeline | 機能一覧 | 症状助言は Physical へ |
| enterprise 系（暗黙） | public 企業資料 + **enterprise-overview-rag** | `local/public/企業` | 契約・SLA 未公開は拒否 |
| legal 横断（暗黙） | **legal-crossdoc-rag** + doc_privacy/doc_terms | プライバシー×規約 | 混在時は両 doc 案内 |

**synonym boost**: `concierge_tech_synonyms.py` — 企業向け → `local/public/企業`、作成意図 → `author-mission-rag` 等。

---

## 7. 例外処理哲学（優先順位）

1. **正本優先**: public 規約・ポリシー > rag FAQ > technical SSOT > ops/dev > research
2. **intent 例外**: `doc_privacy` / `doc_terms` は横断 KB を補助に留め、**条文創作禁止**
3. **開示深度**: 初回概要（2–6 文）→ 深掘りトリガーで medium（`00-disclosure-policy.md`）
4. **PII 二層**: ℹ️ モーダル = public 全文可 / チャット LLM = 運営者個人名・所属非開示
5. **env メタ禁止**: 利用者向け出力に環境変数名・「設定を確認しました」を出さない
6. **医療境界**: Concierge 技術 FAQ でも症状・用法の具体助言はしない → Physical / 受診案内
7. **β 明示**: 保証・SLA・薬剤師 live 応答など**未提供**を過大宣伝しない
8. **人間 escalations**: 削除請求・商用ライセンス・法的断言要求 → doc カード + 窓口（`legal-crossdoc-rag.md`）

---

## Q: どの doc を更新すれば KB に反映されますか

<!-- rag-keywords: 更新 反映 KB sync メンテ どの ファイル -->

**回答要点**

- **public / rag / technical 変更** → Local RAG 再 index → `scripts/sync-all-kb-to-s3.sh`（Support 環境）
- **検証**: `./scripts/verify-concierge-ssot.sh`、`./scripts/concierge-technical-faq-contract.sh`
- **research/** は index 対象外 — SSOT に昇格させる場合のみ rag/ または technical/ へ
- **関連**: `docs/ops/CONCIERGE_TECH_FAQ_MAINTENANCE.md`

**例外・境界**: エージェントが自動で git push しない — 運用手順は ops doc 正本。

---

## Q: 企業・法務の質問はどの FAQ を引くべきですか

<!-- rag-keywords: 企業 法務 どの FAQ 引く ルーティング -->

**回答要点**

- **B2B 概要・導入・制限・窓口** → `enterprise-overview-rag.md` + public 企業資料
- **プライバシー vs 規約・免責・削除・人間案内** → `legal-crossdoc-rag.md`
- **条項正文** → intent `doc_privacy` / `doc_terms` で public md のみ
- **保存の技術詳細** → `04-data-security.md` + `technical-security-rag.md`
- **索引** → 本ファイル §3–§6

**例外・境界**: 1 つの retrieve 結果だけで法務回答を完結させない — intent に応じて正本を切替。
