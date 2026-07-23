# Cloudflare R2 — OTC 商品画像

**公開 CDN**: `https://images.yutok.dev/otc/{slug}.webp`  
**バケット**: `medicine-recommend-otc-images`（APAC）  
**状態**: Custom Domain Active（2026-07-23 確認）

## アプリ連携

```bash
# ローカル / GCP / AWS 共通（画像のみクラウド非依存）
MEDICINE_IMAGE_CDN_BASE=https://images.yutok.dev/otc/
```

- **GCP 本番**: [cloudbuild.yaml](../../cloudbuild.yaml) の `gcloud run deploy --update-env-vars` で自動設定
- **AWS ステージング**: [setup-aws-ecs-secrets.sh](../../scripts/setup-aws-ecs-secrets.sh)（未設定時デフォルトあり）

- 解決ロジック: [src/services/medicine_image_urls.py](../../src/services/medicine_image_urls.py)
- 明示 `https://` の `image_url` は優先
- 未設定時は `image_slug` / JAN / 製品名スラッグ → CDN URL
- オブジェクト未配置時は 404 → UI は `onerror` でプレースホルダー（今後カード側で対応可）

## CORS Policy（R2 ダッシュボード）

```json
[
  {
    "AllowedOrigins": [
      "https://medicine.yutok.dev",
      "https://aws.medicine.yutok.dev",
      "http://localhost:5000"
    ],
    "AllowedMethods": ["GET", "HEAD"],
    "AllowedHeaders": ["*"],
    "ExposeHeaders": ["ETag", "Content-Length", "Content-Type"],
    "MaxAgeSeconds": 86400
  }
]
```

## テスト画像アップロード

```bash
# Python（Windows 含む）
py -3.11 scripts/upload_r2_otc_image.py test
py -3.11 scripts/upload_r2_otc_image.py my-product path/to/image.webp

# bash + aws cli
./scripts/upload-r2-otc-image.sh test static/line/medicine-noimage-hero.png
curl -sI https://images.yutok.dev/otc/test.webp
# → HTTP/1.1 200
```

S3 API エンドポイント（ユーザー向け URL ではない）:

`https://2a1ac0678cd0b207ca4fa5681a9a0690.r2.cloudflarestorage.com/medicine-recommend-otc-images`

## 関連

- 一括計画: [.cursor/plans/aws_cloudflare_一括改善_afd2b593.plan.md](../../.cursor/plans/aws_cloudflare_一括改善_afd2b593.plan.md)
- AWS 機能 env: [AWS_FEATURES_ROLLOUT.md](./AWS_FEATURES_ROLLOUT.md)
