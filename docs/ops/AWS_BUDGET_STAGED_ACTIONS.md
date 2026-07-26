# AWS Budgets 段階的コスト削減

月次 AWS 予算のしきい値に応じて、**自動で段階的に**ステージング環境を縮小・停止する構成。

## 概要

AWS Budgets の標準アクション（EC2 停止など）は **ECS Fargate には効かない**ため、次の構成を使う。

```
AWS Budgets アラート
    ↓ SNS（stage ごとに別トピック）
Lambda: medicine-recommend-budget-action
    ↓ boto3
ECS Express 縮小 / env 最小化 / CodeBuild KB 停止 / ECS 完全停止
```

| Alert | しきい値 | 測定 | 動作 |
|-------|----------|------|------|
| #1 | 50% | 実際 | **メールのみ**（自動アクションなし） |
| #2 | 60% | 予測 | Fargate **512 CPU / 1024 MiB** に縮小 |
| #3 | 75% | 実際 | DeepL + ローカル RAG 等 **minimal env** |
| #4 | 80% | 実際 | CodeBuild **KB sync 停止** + CloudWatch Logs **7日** |
| #5 | 90% | 実際 | **ECS タスク 0** + CodePipeline 自動デプロイ停止 |
| #6 | 100% | 実際 | 同上（冪等・再実行可） |

### メール通知先

| Alert | kawashima | yuto.k_1028 | tachibana@heptagon |
|-------|-----------|-------------|---------------------|
| #1–#4（50–80%） | ✅ | — | — |
| #5–#6（90–100%） | ✅ | ✅ | ✅ |

**注意**: ALB / WAF / Secrets / Pipeline 基本料金は停止後も課金される。

## 1. インフラ作成（1回）

```bash
export AWS_PROFILE=admin   # iam:CreateRole が必要
./scripts/setup-aws-budget-staged-actions.sh
./scripts/apply-aws-budget-notifications.sh
```

`apply-aws-budget-notifications.sh` は予算 **My Monthly Cost Budget** の 6 アラートを一括設定する。

**注意**: 全通知の削除→再作成は ALARM 中に再送メールが発生する。購読者だけ変える場合は `aws budgets delete-subscriber` / `create-subscriber` を使う。

メール変更:

```bash
BUDGET_EMAIL_PRIMARY=you@example.com BUDGET_EMAIL_SECONDARY=you2@example.com \
BUDGET_EMAIL_HEPTAGON=tachibana@heptagon.co.jp \
  AWS_PROFILE=admin ./scripts/apply-aws-budget-notifications.sh
```

作成物:

- IAM ロール `medicine-recommend-budget-action-role`
- Lambda `medicine-recommend-budget-action`
- SNS トピック `medicine-recommend-budget-stage1` 〜 `stage5`
- 設定 JSON `scripts/.aws-budget-staged-actions.json`

## 2. 予算コンソール設定

[AWS Budgets → 予算を編集](https://console.aws.amazon.com/billing/home#/budgets)

### ステップ 2（アラート）

各アラートの **Amazon SNS** に、対応するトピック ARN を設定する。

| Alert | SNS トピック ARN |
|-------|------------------|
| #1 (50% 実際) | **未設定**（メールのみ） |
| #2 (60% 予測) | `arn:aws:sns:ap-northeast-1:290780119994:medicine-recommend-budget-stage1` |
| #3 (75% 実際) | `...medicine-recommend-budget-stage2` |
| #4 (80% 実際) | `...medicine-recommend-budget-stage3` |
| #5 (90% 実際) | `...medicine-recommend-budget-stage4` |
| #6 (100% 実際) | `...medicine-recommend-budget-stage5` |

SNS を初めて設定すると **「確認待ち」** になる。メールの Confirm subscription をクリックする（Budgets 側の SNS ポリシーは setup スクリプトが付与済み）。

### ステップ 3（Budget Actions）

**Budget Actions（EC2 停止 / IAM Deny）は使わない。** Alert #3 に付いている `AWSServiceRoleForAmazonOpenSearchServerless` 等の IAM ロールアクションは **削除** すること（ECS には効かず、誤設定の原因になる）。

このステップは **アクションなし** で「次へ」→ 保存してよい。自動化は SNS → Lambda が担当する。

## 3. 手動テスト

特定ステージだけ試す場合:

```bash
# stage2 (minimal env) をシミュレート
aws lambda invoke \
  --function-name medicine-recommend-budget-action \
  --region ap-northeast-1 \
  --payload "$(python3 - <<'PY'
import json
print(json.dumps({
  "Records": [{
    "Sns": {
      "TopicArn": "arn:aws:sns:ap-northeast-1:290780119994:medicine-recommend-budget-stage2"
    }
  }]
}))
PY
)" \
  /tmp/budget-action-out.json && cat /tmp/budget-action-out.json
```

ログ: CloudWatch Logs → `/aws/lambda/medicine-recommend-budget-action`

## 4. 復旧

段階的に戻す場合（予算期間リセット後など）:

```bash
# 完全停止から復旧
./scripts/resume-aws-staging.sh

# Fargate サイズを元に戻す（必要なら）
CPU=1024 MEMORY=2048 ./scripts/downsize-aws-ecs.sh --restore

# Bedrock KB を再開する場合（8月以降など）
./scripts/resume-aws-bedrock-kb.sh
```

minimal env から AWS 機能付き env に戻す場合は `scripts/update-aws-express-env.sh` または `.env` ベースの各 setup スクリプトを参照。

## 5. 関連スクリプト

| スクリプト | 役割 |
|-----------|------|
| `scripts/setup-aws-budget-staged-actions.sh` | SNS + Lambda 作成 |
| `scripts/downsize-aws-ecs.sh` | 手動 Fargate 縮小 |
| `scripts/stop-aws-staging.sh` | 手動完全停止 |
| `scripts/resume-aws-staging.sh` | 手動復旧 |
| `scripts/apply-aws-minimal-env.sh` | 手動 minimal env |

## 6. Budget Actions（コンソール ステップ 3）に表示できるか

**結論: ECS/Fargate 向けの自動化を Budget Actions UI に表示することはできません。**

AWS Budget Actions がサポートするのは次の 3 種類のみです（[公式ドキュメント](https://docs.aws.amazon.com/cost-management/latest/userguide/budgets-controls.html)）:

| ActionType | 内容 | medicine-recommend への適用 |
|------------|------|----------------------------|
| `APPLY_IAM_POLICY` | IAM Deny ポリシー付与 | 新規 EC2 起動の抑制のみ（Fargate 非対象） |
| `APPLY_SCP_POLICY` | SCP 付与 | Organizations 利用時のみ |
| `RUN_SSM_DOCUMENTS` | EC2/RDS の停止 | **EC2/RDS インスタンスが必要**（Fargate 非対象） |

本プロジェクトは **ECS Express（Fargate）** のため、Budget Actions では ECS 縮小・停止を実行できません。そのため **SNS → Lambda** で代替しており、これは Budget Actions 一覧には **表示されません**（Actions 列は空のままが正常）。

**UI で確認できる場所**

- 予算詳細 → **Alerts**: メール + SNS トピック（設定済み）
- [Lambda コンソール](https://ap-northeast-1.console.aws.amazon.com/lambda/home?region=ap-northeast-1#/functions/medicine-recommend-budget-action): 実行ログ
- [SNS トピック](https://ap-northeast-1.console.aws.amazon.com/sns/v3/home?region=ap-northeast-1): `medicine-recommend-budget-stage1` 〜 `stage5`

補足として 100% で `APPLY_IAM_POLICY`（EC2 起動 Deny）を Budget Actions に追加することは可能ですが、Fargate コスト削減効果はなく、本番運用の IAM 操作と競合する可能性があるため **推奨しません**。

## 7. トラブルシュート

| 症状 | 確認 |
|------|------|
| 予算超過なのに何も起きない | SNS サブスクリプションが Confirmed か、Lambda ログにエラーがないか |
| Lambda AccessDenied | `setup-aws-budget-staged-actions.sh` を再実行して IAM を更新 |
| ECS は止まったが ALB 料金が残る | 想定どおり（ALB は別途停止が必要） |
| 同じ月に再通知されない | Budgets は OK→Exceeded の遷移時のみ通知（同一期間内は1回） |
