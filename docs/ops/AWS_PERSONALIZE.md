# Amazon Personalize（OTC 表示順）

AWS ステージング Web のみ。`PERSONALIZE_CAMPAIGN_ARN` 未設定時はルール順フォールバック。

## セットアップ

```bash
export AWS_PROFILE=medicine-recommend-dev
./scripts/setup-aws-personalize.sh
# scripts/.aws-personalize-env に TRACKING_ID 等
```

ECS Express 反映:

```bash
source scripts/.aws-personalize-env
./scripts/update-aws-express-env.sh
```

## 冷スタート手順

1. **イベント取込** — Web で `view` / `select` / `recommend` を `personalize_ranker.py` から送信（`PERSONALIZE_TRACKING_ID` 必須）
2. **Dataset import** — Personalize コンソールまたは CLI で INTERACTIONS CSV を S3 から import
3. **Solution + Campaign** — 学習完了後 `PERSONALIZE_CAMPAIGN_ARN` を ECS env に設定

最低数百イベントの蓄積を推奨（計画 Phase 4）。

## 関連

- [AWS_FEATURES_ROLLOUT.md](./AWS_FEATURES_ROLLOUT.md)
- [AWS_STAGING_CHECKLIST.md](./AWS_STAGING_CHECKLIST.md)
