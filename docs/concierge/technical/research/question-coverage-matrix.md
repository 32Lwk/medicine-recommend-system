# 質問カバレッジ matrix — Meta KB（R0）

| カテゴリ | 代表 intent | eval fixture | 目標問数 | 備考 |
|----------|-------------|--------------|----------|------|
| 技術 architecture | architecture | kb_eval, paraphrase, technical_deep, context | 45 | SSOT 01-07 + ops |
| 法務 direct | doc_privacy, doc_terms | intent_routing, legal_meta | 12 | 全文参照 |
| アプリ概要 | doc_app_overview, app_about | app_overview, intent_routing | 10 | 11 + public |
| 作成意図/現状 | doc_app_overview | app_overview, quality | 8 | mission SSOT |
| 相談窓口 | doc_consultation | legal_meta, intent_routing | 5 | #7119 |
| 運営者 | doc_operator | intent_routing | 3 | 個人情報マスク |
| 横断 composite | architecture / doc_* | legal_meta, context | 10 | cross-doc retrieve |
| Medicine QA 境界 | None（Physical） | intent_routing | 8 | probe が None |
| 更新履歴 | doc_changelog | kb_eval | 3 | digest boost |
| enterprise | architecture | app_overview | 4 | RAG のみ |

## GO 条件（計画 v3）

| gate | 閾値 | 現状 |
|------|------|------|
| retrieve eval | 90%+ | 60問中 54 pass（90%） |
| intent routing | 92%+ | 新設 |
| quality contract | 90%+ | 新設 |
| integration pytest | 100% | 18 pass |

## 未カバー（許容）

- 多言語 paraphrase 全網羅
- enterprise 専用 intent
- LINE 固有 UI 質問（smoke 3-5問で P2）
