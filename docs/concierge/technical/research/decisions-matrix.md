# 技術選定 decisions matrix — R0 リサーチ（内部）

> 公開 SSOT: `08-technical-decisions.md`。本ファイルは比較表・トレードオフの網羅メモ。

| 決定 | 候補 | 採用 | 主な理由 | 却下理由 |
|------|------|------|----------|----------|
| Concierge RAG | Bedrock KB / Local RAG | Local RAG | コスト・GCP/AWS 共通化 | OpenSearch OCU コスト |
| 本番 compute | Render / AWS / GCP | GCP Cloud Run | 既存運用・Neon 連携 | — |
| ステージング | GCP dev / AWS ECS | AWS ECS | Translate/Polly/Bedrock 試験 | — |
| 翻訳 GCP | DeepL / Google | DeepL | 品質・既存契約 | — |
| 翻訳 AWS | DeepL / Translate | Translate | AWS ネイティブ統合 | — |
| 画像 CDN | S3+CF / R2 | R2 | クロスクラウド共通・低コスト | — |
| 推奨エンジン | LLM-only / ルール+LLM | ルール+LLM | hallucination 防止 | LLM-only は薬名リスク |
| Git 正本 | GitLab / GitHub | GitHub | CI/deploy 正本 | GitLab はミラー |
| CHANGELOG RAG | 全文 chunk / digest | digest のみ | ノイズ・重複 | 全文は retrieve 精度低下 |
| 法務 doc | RAG / md 全文 | md 全文（direct） | 条項精度 | RAG paraphrase リスク |
| 法務横断 | — | RAG 補助 | データ×プライバシー等 | direct intent は全文維持 |
| embedding | local / managed | OpenAI embed | 既存 API・品質 | — |

## 更新トリガ

- infra 変更（cloudbuild / buildspec / ops doc）
- SSOT 08 更新
- eval 失敗時の retrieve boost 調整
