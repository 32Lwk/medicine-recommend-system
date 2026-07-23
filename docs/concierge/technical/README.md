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
```
