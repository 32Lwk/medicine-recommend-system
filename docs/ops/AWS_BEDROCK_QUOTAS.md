# Bedrock クォータ — 429 / 新規アカウント provisioning

ap-northeast-1（東京）の Bedrock 推論クォータが **0 のまま**だと、use case 承認後も `ThrottlingException` が続くことがあります（re:Post 既知問題）。

## 当プロジェクトで影響するクォータ

| 用途 | モデル | 優先 |
|------|--------|------|
| **KB ingestion** | `amazon.titan-embed-text-v2:0` | **P0** |
| Concierge 生成（将来） | `jp.anthropic.claude-sonnet-4-5-20250929-v1:0` 等 | P1 |

### エラーの読み分け

| メッセージ | 意味 | 対処 |
|-----------|------|------|
| `Too many requests` | RPM/TPM または **未 provisioning (0)** | Service Quotas 確認 / Support |
| `Too many tokens per day` | 日次上限 | **JST 09:00** まで待つ or Support |
| `AccessDenied` / use case | Anthropic 未承認 | コンソールで use case 提出 |

## セルフサービス（Adjustable: true）

[Service Quotas — Amazon Bedrock](https://ap-northeast-1.console.aws.amazon.com/servicequotas/home/services/bedrock/quotas)

引き上げ候補（ステージング目安）:

| クォータ | 希望値（目安） |
|---------|---------------|
| Titan Embed Text v2 — requests/min | 6000 |
| Titan Embed Text v2 — tokens/min | 300000 |
| Claude Haiku 4.5 cross-region — requests/min | 100+ |
| Claude Haiku 4.5 cross-region — tokens/min | 100000+ |

CLI（QuotaCode はコンソールで確認してから）:

```bash
export AWS_PROFILE=admin
aws service-quotas request-service-quota-increase \
  --service-code bedrock \
  --quota-code <QuotaCode> \
  --desired-value <値> \
  --region ap-northeast-1
```

## CLI でモデル利用可否を確認（use case 承認後）

```bash
aws bedrock get-foundation-model-availability \
  --model-id amazon.titan-embed-text-v2:0 --region ap-northeast-1

aws bedrock get-foundation-model-availability \
  --model-id anthropic.claude-sonnet-4-5-20250929-v1:0 --region ap-northeast-1
```

`authorizationStatus: AUTHORIZED` かつ `entitlementAvailability: AVAILABLE` なら use case は OK。  
429 が続く場合は **クォータ provisioning 未完了**（下記）。

## 当アカウントで確認済み（2026-07-23）

| QuotaCode | 名称 | 現在値 | Adjustable |
|-----------|------|--------|------------|
| — | Titan Embed v2 **On-demand RPM/TPM/day** | **Service Quotas にエントリなし** | Support 要 |
| L-1074C53D | Titan Embed v2 Provisioned model units | 0 | Yes（Provisioned 用・ingestion とは別） |
| L-8EA73537 | Claude Sonnet 4.5 cross-region TPM | **0** | **Yes → セルフ引き上げ可** |
| L-E107194C | Claude Sonnet 4.5 tokens/day | **0** | **No → Support 必須** |

`get-foundation-model-availability` は両モデル **AUTHORIZED / AVAILABLE**（アクセス拒否ではない）。

### Step 2: セルフサービス（Claude TPM）

```bash
aws service-quotas request-service-quota-increase \
  --service-code bedrock \
  --quota-code L-8EA73537 \
  --desired-value 100000 \
  --region ap-northeast-1
```

（ステージング目安: 100000〜500000。本番は利用見込みに応じて調整）

### Step 3: AWS Support（1 ケースにまとめる）

**件名:** `Bedrock on-demand quota provisioning - ap-northeast-1 - account 290780119994`

**本文（英語）— テンプレート:**

Subject: Bedrock on-demand quota provisioning issue - ap-northeast-1

Account: 290780119994
Region: ap-northeast-1

Issue: On-demand InvokeModel quotas for amazon.titan-embed-text-v2:0 do NOT
appear in Service Quotas at all (not even as 0). KB ingestion fails with
ThrottlingException 429 on InvokeModel.

get-foundation-model-availability shows AUTHORIZED/AVAILABLE for:
- amazon.titan-embed-text-v2:0
- anthropic.claude-sonnet-4-5-20250929-v1:0

Please provision default on-demand quotas for Titan Embed Text v2
(documented defaults: RPM 6,000 / TPM 300,000 / tokens per day).

Also please increase or provision:
- QuotaCode L-E107194C (Claude Sonnet 4.5 tokens/day = 0, Not adjustable)

Knowledge Base ID: 4PEWLBZGTH (Concierge RAG for OTC medicine chatbot staging).

Use case: Anthropic use case form already submitted and approved.

## ingestion 実行（クォータ復旧後）

```bash
# 事前確認
AWS_PROFILE=admin py -3.11 scripts/test_bedrock_titan_embed.py
AWS_PROFILE=admin py -3.11 scripts/test_bedrock_claude_invoke.py

# 指数バックオフ付き ingestion（最大10分 preflight 待機）
INGESTION_PREFLIGHT_WAIT_SEC=600 AWS_PROFILE=admin \
  ./scripts/sync-aws-bedrock-kb-ingestion.sh 4PEWLBZGTH
```

## 日次リセット

- **tokens/day** → UTC 00:00 = **JST 09:00**
- **RPM/TPM** → ローリング 1 分窗口

## 関連

- [AWS_BEDROCK_KB.md](./AWS_BEDROCK_KB.md)
- [AWS re:Post — new account quota stuck at 0](https://repost.aws/questions)
