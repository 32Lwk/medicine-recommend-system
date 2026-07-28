# 技術スタック inventory（R0 調査メモ）

> 開発者向け調査メモ。ユーザー向け回答の SSOT は `docs/concierge/technical/` および `docs/public/`。

| レイヤ | コンポーネント | 本番 (GCP) | AWS ステージング | 公開可否 |
|--------|---------------|------------|------------------|----------|
| ホスティング | Cloud Run / ECS | Cloud Run | ECS Express + ALB | OK |
| DB | PostgreSQL (Neon) | Neon | Neon | OK（接続先詳細は非公開） |
| 生成 AI | OpenAI GPT | 利用 | 利用 | OK |
| 翻訳 | DeepL / Translate | DeepL | Amazon Translate | OK |
| TTS | Cloud TTS / Polly | Cloud TTS | Polly | OK |
| 画像 CDN | Cloudflare R2 | 共通 | 共通 | OK |
| キャッシュ | Redis | なし/限定的 | ElastiCache | OK |
| Concierge RAG | Local RAG | local | local (+ Bedrock KB 準備) | OK |
| Medicine RAG | Local RAG / build/medicine | local | local | OK |
| CI/CD | Cloud Build / CodePipeline | Cloud Build | CodePipeline | OK |
| リポジトリ | GitHub + GitLab mirror | GitHub 正本 | 同左 | OK |

## アプリ層

- FastAPI (`main.py`), Chat Pipeline v2, IntentRouter, マルチエージェント（Triage / Physical / Concierge / Ask 等）
- Sage Terrace UI (`static/css/sage_terrace.css`)

## 更新トリガー

インフラ変更時: 該当 SSOT + 本 inventory + `verify-concierge-ssot.sh`
