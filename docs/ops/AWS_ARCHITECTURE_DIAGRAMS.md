# AWS 統合アーキテクチャ図 — medicine-recommend

> **対象環境**: AWS ステージング `https://aws.medicine.yutok.dev`  
> **アカウント**: `290780119994` / **リージョン**: `ap-northeast-1`（東京）  
> **調査日**: 2026-07-28（AWS CLI `medicine-recommend-dev` プロファイルで実リソース確認）

本番トラフィックは **GCP Cloud Run**（`medicine.yutok.dev`）が正本。AWS はステージング試験環境として、Translate / Polly / Bedrock KB / CloudFront 等の AWS ネイティブ機能を検証する。

**draw.io 版**（AWS アイコン付き・**3ゾーン構成 + 用途別分解図**）:

| 図 | 内容 | 用途 |
|----|------|------|
| **[`medicine-recommend-aws-staging-complete.drawio`](../medicine-recommend-aws-staging-complete.drawio)** | **マルチページ統合版（13 シート）** — 目次 + 全体構成 + 分解図 + LINE + データ | **推奨：最初に開くファイル** |
| [`aws-integrated-architecture.drawio`](../diagrams/aws-integrated-architecture.drawio) | **統合全体像** — 左: User+External / 中央: AWS Runtime / 右: CI/CD | 全体俯瞰 |
| [`aws-user-request-flow.drawio`](../diagrams/aws-user-request-flow.drawio) | ユーザーリクエストのみ（Browser → WAF → ALB → ECS） | ランタイム理解 |
| [`aws-cicd-flow.drawio`](../diagrams/aws-cicd-flow.drawio) | CI/CD のみ（GitHub → Pipeline → ECR → ECS + S3 sync） | デプロイ理解 |
| [`aws-external-integrations.drawio`](../diagrams/aws-external-integrations.drawio) | ECS 中心の外部連携（OpenAI / Neon / R2 / AI） | 接続先一覧 |
| [`aws-runtime-services.drawio`](../diagrams/aws-runtime-services.drawio) | AWS 内サービスのみ（WAF〜CloudWatch） | AWS リソース一覧 |
| [`aws-cross-cloud-overview.drawio`](../diagrams/aws-cross-cloud-overview.drawio) | GCP 本番 vs AWS ステージング vs 共通 R2 | クロスクラウド比較 |
| [`aws-multi-agent-architecture.drawio`](../diagrams/aws-multi-agent-architecture.drawio) | マルチエージェント会話パイプライン | アプリ内部 |
| [`aws-agent-detail-architecture.drawio`](../diagrams/aws-agent-detail-architecture.drawio) | エージェント詳細 | アプリ内部 |

再生成:

```bash
# マルチページ統合版（13 シート — 推奨）
python scripts/generate_aws_staging_complete_diagram.py

# 単体分解図（docs/diagrams/ 配下 6 ファイル）
python scripts/generate_aws_integrated_diagram.py

# 01 全体構成のみ（A3 1 ページ詳細版）
python scripts/generate_aws_staging_diagram.py
```

### マルチページ統合版（13 シート）の構成

| シート | 内容 |
|--------|------|
| 00 目次 | 全シートの説明一覧 |
| 01 全体構成 | AWS ステージング全コンポーネント（ユーザー / ECS / CI/CD / AI / 外部 / 監視） |
| 02 統合 3 ゾーン | ユーザー / AWS ランタイム / CI/CD / 外部 SaaS |
| 03 ユーザーリクエスト | Browser → WAF → ALB → ECS |
| 04 CI/CD パイプライン | GitHub → CodePipeline → CodeBuild → デプロイ |
| 05 外部連携マップ | OpenAI / Neon / R2 / AWS AI サービス |
| 06 クロスクラウド比較 | GCP 本番 vs AWS ステージング |
| 07 Chat Pipeline v2 | マルチエージェント会話フロー |
| 08 症状相談 Physical | ルールベース推奨 + AWS サービス |
| 09 Bedrock KB RAG | KB 同期・ingestion・Retrieve |
| 10 運用・コスト管理 | CloudWatch / Budget / Lambda / IAM |
| 11 LINE Webhook (GCP) | LINE → Cloud Run 本番経路 |
| 12 シークレット・データ | Secrets Manager / Neon / Web vs LINE 保存 |

### 図の選び方

| 知りたいこと | 開く図 |
|-------------|--------|
| **全体を一度に（推奨）** | `medicine-recommend-aws-staging-complete.drawio` → タブ「01 全体構成」 |
| シート一覧から選びたい | 同上 → タブ「00 目次」 |
| チャット API の流れだけ | `aws-user-request-flow.drawio` |
| デプロイの流れだけ | `aws-cicd-flow.drawio` |
| ECS から何に繋がっているか | `aws-external-integrations.drawio` |
| AWS 内のサービス一覧 | `aws-runtime-services.drawio` |
| GCP 本番との違い | `aws-cross-cloud-overview.drawio` |
| アプリ内部のエージェント | `aws-multi-agent-architecture.drawio` |

### 統合図の 3 ゾーン構成

```
┌─────────────────┬──────────────────────────────┬─────────────────┐
│ ① User & External│  ② AWS Runtime              │  ③ CI/CD        │
│                 │  (ap-northeast-1)            │                 │
│  Web Browser    │  Request: WAF→ALB→ECS        │  GitHub (main)  │
│  OpenAI API     │  Static:  S3 → CloudFront    │  CodeStar       │
│  Neon PostgreSQL│  AI: Translate/Polly/KB    │  CodePipeline   │
│  Cloudflare R2  │  Secrets / CloudWatch      │  CodeBuild→ECR  │
└─────────────────┴──────────────────────────────┴─────────────────┘
```

ゾーン間は破線枠と縦区切り線で分離。矢印はゾーンをまたいで最小限にルーティング。

## 1. 統合アーキテクチャ全体像

```mermaid
flowchart TB
  subgraph Users["利用者"]
    Browser["Web Browser"]
  end

  subgraph DNS["DNS（リポジトリ外）"]
    CF_DNS["aws.medicine.yutok.dev<br/>→ ALB / CloudFront"]
  end

  subgraph GitHub["GitHub（正本）"]
    GH["32Lwk/medicine-recommend-system<br/>main branch"]
  end

  subgraph AWS["AWS Cloud ap-northeast-1 (290780119994)"]

    subgraph Edge["エッジ・セキュリティ"]
      WAF["WAF Web ACL<br/>medicine-recommend-web-acl<br/>Rate 2000/5min + CommonRuleSet"]
      ALB["ALB<br/>ecs-express-gateway-alb-c8b801ce<br/>internet-facing"]
      CF["CloudFront<br/>d1hux8767tyzd1.cloudfront.net<br/>E3P9RCD6JXOZIR"]
    end

    subgraph Compute["コンピュート"]
      ECS["ECS Express Gateway<br/>cluster: default<br/>service: medicine-recommend<br/>Fargate 512 CPU / 1024 MiB"]
      ECR["ECR<br/>medicine-recommend:latest"]
    end

    subgraph CICD["CI/CD"]
      CS["CodeStar Connection<br/>medicine-recommend-github"]
      CP["CodePipeline<br/>medicine-recommend-main"]
      CB["CodeBuild<br/>medicine-recommend-build<br/>buildspec.yml"]
      S3A["S3 Artifacts<br/>medicine-recommend-pipeline-artifacts-*"]
    end

    subgraph Storage["ストレージ・CDN"]
      S3S["S3 Static<br/>medicine-recommend-static-*"]
      S3KB["S3 KB Source<br/>medicine-recommend-kb-source-*"]
    end

    subgraph AI["AI / ML サービス"]
      BR["Bedrock Knowledge Base<br/>Concierge 2CNAGQ2V4P<br/>Medicine 30BCEJCJHA"]
      TR["Amazon Translate"]
      PO["Amazon Polly"]
      CM["Comprehend Medical<br/>（任意 NLU 補助）"]
      PZ["Amazon Personalize<br/>（Phase 4・任意）"]
    end

    subgraph Cache["キャッシュ（Phase 4）"]
      RC["ElastiCache Serverless Redis<br/>（REDIS_URL 設定時）"]
    end

    subgraph Secrets["シークレット・監視"]
      SM["Secrets Manager<br/>medicine-recommend/aws-staging/*"]
      CW["CloudWatch Logs<br/>/ecs/medicine-recommend"]
      BD["AWS Budgets + SNS"]
      LM["Lambda<br/>medicine-recommend-budget-action"]
    end
  end

  subgraph External["外部 SaaS（AWS 外）"]
    Neon["Neon PostgreSQL<br/>DATABASE_URL"]
    OAI["OpenAI API<br/>生成・IntentRouter"]
    R2["Cloudflare R2<br/>images.yutok.dev/otc/"]
    GCP["GCP Cloud Run<br/>medicine.yutok.dev（本番）"]
  end

  Browser --> CF_DNS
  CF_DNS --> WAF --> ALB --> ECS
  Browser --> CF
  CF --> S3S

  GH --> CS --> CP --> CB
  CP --> S3A
  CB --> ECR --> ECS
  CB --> S3S --> CF
  CB --> S3KB --> BR

  ECS --> Neon
  ECS --> OAI
  ECS --> R2
  ECS --> TR
  ECS --> PO
  ECS --> BR
  ECS --> CM
  ECS --> PZ
  ECS --> RC
  ECS --> CW
  SM -.->|ECS Express secrets 注入| ECS

  BD --> LM
  LM -.->|コスト超過時| ECS
  LM -.->|コスト超過時| CB

  GCP -.->|本番トラフィック| Neon
  GCP -.->|LINE Webhook| Neon
```

### 実リソース一覧（CLI 確認済み）

| カテゴリ | リソース名 / ID |
|---------|----------------|
| ALB | `ecs-express-gateway-alb-c8b801ce-655959205.ap-northeast-1.elb.amazonaws.com` |
| WAF | `medicine-recommend-web-acl` |
| CloudFront | `d1hux8767tyzd1.cloudfront.net`（Distribution `E3P9RCD6JXOZIR`） |
| ECS クラスタ | `default` |
| ECS サービス | `medicine-recommend`（Express Gateway / CANARY デプロイ） |
| タスク定義 | `default-medicine-recommend`（512 CPU / 1024 MiB / Gunicorn 2 workers） |
| ECR | `290780119994.dkr.ecr.ap-northeast-1.amazonaws.com/medicine-recommend` |
| CodePipeline | `medicine-recommend-main`（Source → Build） |
| S3 | `medicine-recommend-static-*`, `medicine-recommend-kb-source-*`, `medicine-recommend-pipeline-artifacts-*` |
| CloudWatch | `/ecs/medicine-recommend` |
| Lambda | `medicine-recommend-budget-action` |
| Secrets Manager | `medicine-recommend/aws-staging/*`（7 件: OpenAI, DB, SECRET_KEY, R2, DeepL, LINE 等） |

> **注**: 調査時点で ECS `desiredCount=0`（ステージング停止中）。Budget 段階的アクションまたは手動停止の可能性あり。アーキテクチャ自体は変わらない。

---

## 2. CI/CD デプロイフロー

GitHub `main` push をトリガーに、ビルド・デプロイ・静的アセット同期・KB ingestion・smoke test まで一連で実行。

```mermaid
sequenceDiagram
  autonumber
  actor Dev as 開発者
  participant GH as GitHub main
  participant CS as CodeStar Connection
  participant CP as CodePipeline
  participant CB as CodeBuild
  participant ECR as ECR
  participant ECS as ECS Express
  participant S3S as S3 Static
  participant CF as CloudFront
  participant S3KB as S3 KB Source
  participant BR as Bedrock KB
  participant ALB as ALB /health

  Dev->>GH: git push origin main
  GH->>CS: Webhook / poll
  CS->>CP: Source stage（CODEBUILD_CLONE_REF）
  CP->>CB: Build stage（buildspec.yml）

  Note over CB: pre_build
  CB->>ECR: docker login + cache pull
  CB->>CB: write_build_meta.py

  Note over CB: build
  CB->>CB: docker build linux/amd64
  CB->>ECR: docker push :latest

  Note over CB: post_build — codebuild-post-deploy.sh
  par 並列実行
    CB->>ECS: force-new-deployment
    CB->>ALB: wait /health git_commit
    opt static/ 変更時
      CB->>S3S: sync-static-to-s3.sh --invalidate
      S3S->>CF: CreateInvalidation
    end
    opt KB ソース変更時
      CB->>S3KB: sync-all-kb-to-s3.sh
    end
    CB->>CB: verify-concierge-ssot.sh
  end

  opt KB_INGESTION_ON_PUSH=true
    CB->>BR: start-managed-kb-ingestion.sh（非同期）
  end

  CB->>ALB: aws-staging-smoke.sh<br/>Translate / Polly / CDN / health
  CB-->>CP: Build 完了
```

### CodeBuild 環境変数（主要）

| 変数 | 既定 | 説明 |
|------|------|------|
| `SYNC_STATIC_TO_S3` | `true` | static/ → S3 + CloudFront 無効化 |
| `SYNC_KB_TO_S3` | `true`（Console 設定） | Concierge + Medicine KB ソース同期 |
| `KB_INGESTION_ON_PUSH` | `true` | Managed KB ingestion 非同期起動 |
| `RUN_KB_EVAL` | `false` | retrieve 精度 eval |
| `SMOKE_STRICT` | `false` | smoke 失敗で build fail にするか |
| `AWS_STAGING_URL` | `https://aws.medicine.yutok.dev` | ヘルス・smoke 先 |

変更パス検知: `scripts/lib/codebuild_deploy_paths.py` — `src/` のみ push 時は static/KB sync をスキップ（検知不能時はフル sync フォールバック）。

---

## 3. Web リクエストパス（ランタイム）

ブラウザからの HTTP リクエストが ALB 経由で FastAPI コンテナに到達するまでの経路。

```mermaid
flowchart LR
  subgraph Client
    U["Browser<br/>aws.medicine.yutok.dev"]
  end

  subgraph Edge
    DNS["DNS CNAME"]
    WAF["WAF<br/>Rate limit + OWASP CRS"]
    ALB["ALB<br/>HTTPS :443"]
    TG["Target Group<br/>ECS Express"]
  end

  subgraph ECS["ECS Fargate Task"]
    GW["Express Gateway<br/>CANARY routing"]
    GUN["Gunicorn + UvicornWorker<br/>FastAPI main.py"]
  end

  subgraph StaticPath["静的アセット（別経路）"]
    CF["CloudFront"]
    S3["S3 static/"]
  end

  U -->|HTML/API POST| DNS --> WAF --> ALB --> TG --> GW --> GUN
  U -->|JS/CSS/img| CF --> S3
  GUN -->|resolve_static_asset_url| CF
```

### ヘルスチェック

| エンドポイント | 用途 |
|---------------|------|
| `GET /health` | ALB プローブ + CI commit 確認（`status`, `git_commit`） |
| `GET /health/aws` | AWS 機能フラグ（Translate/Polly/KB 等の利用有無） |
| `POST /api/smoke/aws-translate` | CodeBuild smoke 用 |

---

## 4. Chat Pipeline v2 — マルチエージェント会話フロー

アプリケーション内部の会話処理パイプライン。GCP/AWS 共通ロジックで、AWS 固有サービスは env ゲートで切替。

```mermaid
flowchart TB
  subgraph Entry["入口"]
    POST["POST /api/chat<br/>chat_post_pipeline.py"]
  end

  subgraph PreRoute["前処理"]
    SG1["SafetyGate (pre)<br/>入力ブロック・脅迫検知"]
    FP["SessionOps fast-path<br/>セッション再開等"]
    TRI["TriageAgent<br/>入力分類"]
    SG2["SafetyGate (post)"]
    SOT["SessionOps triage<br/>セッション永続化"]
    CTX["sync_routing_context"]
    IR["IntentRouter<br/>LLM 構造化 + legacy hint"]
    GATE["gate.py<br/>緊急・カウンセリング・店舗"]
  end

  subgraph Dispatch["AgentDispatcher"]
    AD["intent → handler 振分"]
  end

  subgraph Agents["専門エージェント"]
    PHY["PhysicalOrchestrator<br/>症状→ルールベース推奨"]
    CON["ConciergeAgent<br/>FAQ・技術・挨拶"]
    ASK["AskAgent<br/>推奨後 Q&A"]
    EXP["ExplanationAgent<br/>推奨理由説明"]
    STR["StoreInquiryAgent<br/>店舗・遺失物"]
    CSL["CounselingManager<br/>心理カウンセリング"]
    EMG["EmergencyRouter<br/>緊急受診案内"]
  end

  subgraph Response["応答"]
    SSE["SSE ストリーミング<br/>sse_emit.py / chat_stream.py"]
    UI["Sage Terrace UI<br/>status カード + reco カード"]
  end

  POST --> SG1 --> FP --> TRI --> SG2 --> SOT --> CTX --> IR --> GATE --> AD

  AD --> PHY
  AD --> CON
  AD --> ASK
  AD --> EXP
  AD --> STR
  AD --> CSL
  AD --> EMG

  PHY --> SSE --> UI
  CON --> SSE
  ASK --> SSE
  EXP --> SSE
  STR --> SSE
  CSL --> SSE
  EMG --> SSE
```

### IntentRouter 振分先（主要）

| ルート | エージェント | 典型入力 |
|--------|-------------|---------|
| Physical | PhysicalOrchestrator | 「頭痛がする」「風邪の薬」 |
| Concierge | ConciergeAgent | 「このサービスとは」「デプロイ方法」 |
| Medicine QA | AskAgent | 推奨後の「副作用は？」 |
| Store | StoreInquiryAgent | 「営業時間は？」 |
| Emergency | EmergencyRouter | 重篤症状・緊急 |
| Counseling | CounselingManager | 心理的相談 |

---

## 5. 症状相談フロー（PhysicalOrchestrator + AWS サービス）

市販薬推奨の核心パス。薬名選定は **ルールベース**（LLM は説明・NLU のみ）。

```mermaid
flowchart TB
  subgraph Input
    MSG["ユーザー症状入力"]
  end

  subgraph NLU["症状解析"]
    NLU1["症状辞書 NLU<br/>data/ CSV"]
    CM["Comprehend Medical<br/>（COMPREHEND_MEDICAL_ENABLED）"]
  end

  subgraph Scoring["ルールベース推奨"]
    RB["rule_based_recommendation.py"]
    CSV["data/ 医薬品 CSV<br/>効能・年齢・相互作用等"]
    PZ["Personalize<br/>表示順最適化（任意）"]
  end

  subgraph RAG["Medicine RAG（任意）"]
    MKBR["Bedrock KB Medicine<br/>30BCEJCJHA"]
    ASK["AskAgent / ExplanationAgent<br/>augment_medicine_prompt_with_kb"]
  end

  subgraph Media["メディア"]
    R2["Cloudflare R2<br/>OTC 画像 CDN"]
    TR["Amazon Translate<br/>非日本語応答"]
    PO["Amazon Polly<br/>TTS 音声"]
  end

  subgraph Persist
    DB["Neon PostgreSQL<br/>セッション・メッセージ"]
    CW["CloudWatch Logs<br/>PIPELINE_PERF 等"]
  end

  MSG --> NLU1
  MSG --> CM
  NLU1 --> RB
  CSV --> RB
  RB --> PZ
  RB --> R2
  RB --> TR
  RB --> PO
  RB --> DB
  RB --> CW

  MSG -->|推奨後 Q&A| MKBR --> ASK
  ASK --> TR
  ASK --> DB
```

### AWS vs GCP 機能切替（env ゲート）

| 機能 | GCP 本番 | AWS ステージング |
|------|---------|-----------------|
| 翻訳 | DeepL | Amazon Translate |
| TTS | Google Cloud Text-to-Speech | Amazon Polly |
| Concierge RAG | ローカル JSON | Bedrock KB `2CNAGQ2V4P` |
| Medicine RAG | ローカル | Bedrock KB `30BCEJCJHA` |
| 静的 JS/CSS | アプリ同梱 | CloudFront CDN |
| キャッシュ | なし | ElastiCache Redis（任意） |
| 表示順 | ルール順 | Personalize（任意） |

正本: [`config/aws_features.py`](../../config/aws_features.py)

---

## 6. Concierge / Bedrock KB RAG フロー

技術 FAQ・運用情報への回答。AWS ステージングでは Managed KB 経由で retrieve。

```mermaid
sequenceDiagram
  autonumber
  actor U as ユーザー
  participant CA as ConciergeAgent
  participant RT as concierge_runtime_reference
  participant KB as bedrock_kb_retrieve.py
  participant BR as Bedrock Agent Runtime<br/>Retrieve API
  participant RC as Redis Cache<br/>（任意）
  participant OAI as OpenAI API
  participant UI as SSE → Sage UI

  U->>CA: 「技術構成は？」（intent=architecture）
  CA->>RT: SSOT 注入<br/>docs/concierge/technical/*.md
  CA->>KB: augment_reference_with_kb()

  alt CONCIERGE_RAG_PROVIDER=bedrock_kb
    KB->>RC: キャッシュ確認
    RC-->>KB: miss
    KB->>BR: retrieve(managedSearchConfiguration)
    BR-->>KB: 関連チャンク
    KB->>RC: キャッシュ保存
  else local（GCP）
    KB->>KB: concierge_knowledge.ja.json
  end

  KB-->>CA: 参照コンテキスト
  CA->>OAI: プロンプト + 参照で生成
  OAI-->>CA: 回答テキスト
  CA->>UI: status カード（SSE done）
  UI-->>U: 仕組み・技術カード表示
```

### KB データパイプライン

```mermaid
flowchart LR
  subgraph Repo["リポジトリ"]
    DOC["docs/concierge/<br/>docs/ops/"]
    MED["data/ CSV<br/>→ build_medicine_kb_documents.py"]
  end

  subgraph S3["S3 KB Source"]
    P1["concierge/ ops/ content/ public/"]
    P2["medicine/ products/ interactions/ ..."]
  end

  subgraph Bedrock["Bedrock Managed KB"]
    KB1["Concierge KB<br/>2CNAGQ2V4P"]
    KB2["Medicine KB<br/>30BCEJCJHA"]
  end

  subgraph Trigger["同期トリガー"]
    CB["CodeBuild post_build<br/>sync-all-kb-to-s3.sh"]
    MAN["手動 scripts/"]
  end

  DOC --> CB --> P1 --> KB1
  MED --> CB --> P2 --> KB2
  MAN --> S3
  CB -->|KB_INGESTION_ON_PUSH| KB1
  CB -->|KB_INGESTION_ON_PUSH| KB2
```

---

## 7. シークレット・データ永続化フロー

```mermaid
flowchart TB
  subgraph SecretsManager["AWS Secrets Manager"]
    S1["openai-api-key"]
    S2["database-url"]
    S3["secret-key"]
    S4["r2-access-key-id / secret"]
    S5["deepl-api-key"]
    S6["line-channel-access-token"]
  end

  subgraph ECS["ECS Express Task"]
    APP["FastAPI App<br/>Gunicorn workers"]
  end

  subgraph ExternalDB["外部 DB"]
    Neon["Neon PostgreSQL<br/>セッション・メッセージ・属性"]
  end

  subgraph Logging["ログ"]
    CW["CloudWatch Logs<br/>/ecs/medicine-recommend"]
    JSONL["log/ 分析 JSONL<br/>（開発・品質評価）"]
  end

  S1 & S2 & S3 & S4 & S5 & S6 -->|primaryContainer.secrets| APP
  APP -->|DATABASE_URL| Neon
  APP -->|structured_logger| CW
  APP -.->|開発時| JSONL
```

> GCP 本番は Secret Manager + Cloud Logging。DB は Neon の別インスタンスまたは同一（環境により異なる）。

---

## 8. コスト管理フロー（Budget 段階的アクション）

月次予算超過時に Lambda が ECS / CodeBuild を段階的に縮小・停止。

```mermaid
flowchart TB
  subgraph Budget["AWS Budgets"]
    A1["50% 実績 → メールのみ"]
    A2["60% 予測 → ECS 512/1024 縮小"]
    A3["75% 実績 → minimal env<br/>DeepL + local RAG"]
    A4["80% 実績 → KB sync 停止<br/>Logs 7日保持"]
    A5["90% 実績 → ECS tasks=0<br/>Pipeline 停止"]
    A6["100% 実績 → 同上（冪等）"]
  end

  subgraph SNS["SNS Topics"]
    T1["budget-stage1"]
    T2["budget-stage2"]
    T3["budget-stage3"]
    T4["budget-stage4"]
    T5["budget-stage5"]
  end

  subgraph Lambda["Lambda"]
    LM["medicine-recommend-budget-action<br/>python3.12"]
  end

  subgraph Targets["対象リソース"]
    ECS["ECS Express<br/>desiredCount / CPU / memory"]
    CB["CodeBuild env<br/>SYNC_KB_TO_S3=false"]
    ENV["ECS env<br/>minimal 設定"]
  end

  A2 --> T1 --> LM
  A3 --> T2 --> LM
  A4 --> T3 --> LM
  A5 --> T4 --> LM
  A6 --> T5 --> LM

  LM --> ECS
  LM --> CB
  LM --> ENV
```

手動復旧: `scripts/resume-aws-staging.sh` / `scripts/resume-aws-bedrock-kb.sh`

---

## 9. クロスクラウド位置づけ

AWS ステージングは GCP 本番と **同一アプリケーションコード** を共有。インフラと AI サービスのみ差分。

```mermaid
flowchart TB
  subgraph Shared["共通"]
    CODE["同一 Git リポジトリ<br/>32Lwk/medicine-recommend-system"]
    R2["Cloudflare R2<br/>images.yutok.dev/otc/"]
    OAI["OpenAI API"]
  end

  subgraph GCP_Prod["GCP 本番"]
    CR["Cloud Run<br/>medicine.yutok.dev"]
    LINE["LINE Webhook"]
    DEEPL["DeepL"]
    WS["Cloud Text-to-Speech"]
    NEON_G["Neon PostgreSQL"]
  end

  subgraph AWS_Stg["AWS ステージング"]
    ECS["ECS Express<br/>aws.medicine.yutok.dev"]
    TR["Translate / Polly / Bedrock"]
    CF["CloudFront static CDN"]
    NEON_A["Neon PostgreSQL"]
  end

  CODE --> CR
  CODE --> ECS
  CR --> NEON_G
  ECS --> NEON_A
  CR --> R2
  ECS --> R2
  CR --> OAI
  ECS --> OAI
  LINE --> CR
  CR --> DEEPL
  ECS --> TR
```

---

## 10. IAM ロール構成

```mermaid
flowchart LR
  subgraph Roles["IAM Roles"]
    R1["medicine-recommend-codepipeline-role"]
    R2["medicine-recommend-codebuild-role"]
    R3["ecsTaskExecutionRole"]
    R4["medicine-recommend-ecs-task-role"]
    R5["medicine-recommend-budget-action-role"]
  end

  subgraph Services["サービス"]
    CP["CodePipeline"]
    CB["CodeBuild"]
    ECS["ECS Task"]
    LM["Lambda Budget"]
  end

  subgraph Permissions["主要権限"]
    P1["S3 / ECR / ECS / CloudFront"]
    P2["Bedrock ingestion / S3 KB"]
    P3["Secrets Manager GetSecretValue<br/>ECR pull"]
    P4["Translate / Polly / Comprehend<br/>Bedrock Retrieve"]
    P5["ECS update / CodeBuild env"]
  end

  R1 --> CP --> P1
  R2 --> CB --> P1
  R2 --> P2
  R3 --> ECS --> P3
  R4 --> ECS --> P4
  R5 --> LM --> P5
```

---

## 関連ドキュメント

| ドキュメント | 内容 |
|-------------|------|
| [AWS_INFRA.md](./AWS_INFRA.md) | Phase 1: CloudWatch / WAF / CloudFront |
| [AWS_CODEPIPELINE.md](./AWS_CODEPIPELINE.md) | CI/CD 詳細・トラブルシュート |
| [AWS_FEATURES_ROLLOUT.md](./AWS_FEATURES_ROLLOUT.md) | env ゲート一覧 |
| [AWS_BEDROCK_KB.md](./AWS_BEDROCK_KB.md) | Bedrock KB 運用 |
| [AWS_BUDGET_STAGED_ACTIONS.md](./AWS_BUDGET_STAGED_ACTIONS.md) | コスト削減 |
| [01-cross-cloud-architecture.md](../concierge/technical/01-cross-cloud-architecture.md) | クロスクラウド概要 |
| [02-chat-pipeline-agents.md](../concierge/technical/02-chat-pipeline-agents.md) | エージェント詳細 |

## セットアップスクリプト索引

| Phase | スクリプト |
|-------|-----------|
| 1 | `setup-aws-infra.sh`（CloudWatch + WAF + CloudFront） |
| 2 | Translate / Polly（env 設定） |
| 3 | `setup-aws-bedrock-kb.sh` |
| 4 | `setup-aws-elasticache.sh`, `setup-aws-personalize.sh` |
| 5 | CodeBuild KB 自動 sync（`buildspec.yml` post_build） |
| CI/CD | `setup-aws-codepipeline.sh` |
| コスト | `setup-aws-budget-staged-actions.sh` |
