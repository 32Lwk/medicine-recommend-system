# ドキュメント索引

開発・運用で参照する正本は下記カテゴリに整理しています。提出用・過去資料は `archive/` に格納しています。

## 公開・法務（`public/`）

| ファイル | 用途 |
|---------|------|
| [アプリ概要.md](public/アプリ概要.md) | 製品概要（β版） |
| [プライバシーポリシー.md](public/プライバシーポリシー.md) | プライバシー |
| [免責事項・利用規約.md](public/免責事項・利用規約.md) | 利用規約 |
| [医薬品相談先.md](public/医薬品相談先.md) | 公的相談窓口 |
| [運営者情報.md](public/運営者情報.md) | 運営者（Web 公開用） |
| [会社向け概要書類.md](public/会社向け概要書類.md) | 企業・行政向け詳細 |
| [企業向け簡略版概要資料.md](public/企業向け簡略版概要資料.md) | 企業向け短版 |

Concierge 用のお問い合わせ文面: [concierge/お問い合わせ・試験運用.md](concierge/お問い合わせ・試験運用.md)

## 開発（`dev/`）

| ファイル | 用途 |
|---------|------|
| [ARCHITECTURE_MULTI_AGENT.md](dev/ARCHITECTURE_MULTI_AGENT.md) | マルチエージェント正本 |
| [FASTAPI_ARCHITECTURE.md](dev/FASTAPI_ARCHITECTURE.md) | FastAPI 構成 |
| [ROUTE_SPEC.md](dev/ROUTE_SPEC.md) | ルート仕様 |
| [ROUTING_ARCHITECTURE_AUDIT.md](dev/ROUTING_ARCHITECTURE_AUDIT.md) | ルーティング監査 |
| [AGENT_DEDUP_AUDIT.md](dev/AGENT_DEDUP_AUDIT.md) | LLM 呼び出し重複監査 |
| [ASYNC_IMPLEMENTATION_GUIDE.md](dev/ASYNC_IMPLEMENTATION_GUIDE.md) | 非同期実装 |
| [SDK_SPIKE.md](dev/SDK_SPIKE.md) | SDK 調査 |

## 運用・QA（`ops/`）

| ファイル | 用途 |
|---------|------|
| [LINE_WEBHOOK_SETUP.md](ops/LINE_WEBHOOK_SETUP.md) | LINE 連携 |
| [CLOUD_RUN_LLM_ENV.md](ops/CLOUD_RUN_LLM_ENV.md) | Cloud Run 環境変数 |
| [SMOKE_MANUAL.md](ops/SMOKE_MANUAL.md) | 手動スモーク |
| [DEV_LINE_FLEX_PREVIEW.md](ops/DEV_LINE_FLEX_PREVIEW.md) | LINE Flex 開発プレビュー |
| [DEV_ERROR_UI_PREVIEW.md](ops/DEV_ERROR_UI_PREVIEW.md) | エラー UI プレビュー |
| [MANUAL_QA_PREFERENCES.md](ops/MANUAL_QA_PREFERENCES.md) | 嗜好 NLU 手動 QA |
| [PREFERENCE_NLU_DEV_REVIEW.md](ops/PREFERENCE_NLU_DEV_REVIEW.md) | 嗜好 NLU レビュー |
| [CAPACITY_PLANNING.md](ops/CAPACITY_PLANNING.md) | キャパシティ |
| [CLOUDFLARE_R2_IMAGES.md](ops/CLOUDFLARE_R2_IMAGES.md) | OTC 商品画像 R2 / CDN |
| [RECOMMENDATION_PRODUCT_FILTERS.md](ops/RECOMMENDATION_PRODUCT_FILTERS.md) | 推奨候補の製品除外リスト |
| [AWS_FEATURES_ROLLOUT.md](ops/AWS_FEATURES_ROLLOUT.md) | AWS 機能 env ゲート |

## LLM（`llm/`） / セキュリティ（`security/`） / UI（`ui/`）

- LLM: [LLM_ROLLBACK.md](llm/LLM_ROLLBACK.md), [PHASE_EXIT_CHECKLISTS.md](llm/PHASE_EXIT_CHECKLISTS.md)
- Security: [SECURITY_IMPLEMENTATION.md](security/SECURITY_IMPLEMENTATION.md), [ADMIN_PII_PLAYBOOK.md](security/ADMIN_PII_PLAYBOOK.md)
- UI: [SCROLLBAR_STYLE.md](ui/SCROLLBAR_STYLE.md), [PARTICLE_*.md](ui/), [STATIC_SEASON_ASSETS.md](ui/STATIC_SEASON_ASSETS.md)

## 計画・分析

- [planning/](planning/) — GCP 移行、改善計画、開発用プロンプト、レビュー報告書
- [analysis/](analysis/) — ログ分析脚本、SRP 確認

## 図面（`diagrams/`）

Draw.io / PNG のアーキテクチャ図・データフロー図。旧 `drowio/` から移行。

## アーカイブ（`archive/`）

| フォルダ | 内容 |
|---------|------|
| [archive/mitou/](archive/mitou/) | 未踏提案・公募資料 |
| [archive/gikushosai/](archive/gikushosai/) | 技育祭スライド |
| [archive/gikushokai/](archive/gikushokai/) | 学祭プレゼン |
| [archive/latex/](archive/latex/) | LaTeX 論文・技術文書 |
