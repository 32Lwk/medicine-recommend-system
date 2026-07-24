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

## ログ推奨上位 OTC の一括同期（マツキヨココカラ → R2）

推奨ログ頻度上位（既定 200 件）を [scripts/sync_otc_images_from_matsukiyo.py](../../scripts/sync_otc_images_from_matsukiyo.py) で取得・アップロードする。

```bash
# 一覧・マッチングのみ（アップロードなし）
py -3.11 scripts/sync_otc_images_from_matsukiyo.py --dry-run --limit 200

# R2 アップロード（.env の R2_* 必須）
py -3.11 scripts/sync_otc_images_from_matsukiyo.py --limit 200 --upload

# 中断後の再開
py -3.11 scripts/sync_otc_images_from_matsukiyo.py --limit 200 --upload --resume
```

成果物: `log/analysis/otc_image_sync/manifest.json` / `candidates.csv`  
画像ソース: `https://www.matsukiyococokara-online.com/store/`（商品検索 → JAN → 商品画像 `_01_` 優先）  
R2 キー: `otc/{slug}.webp`（`slugify_product_name` と同一規則）

**ローカルコピー**: `static/otc/{slug}.webp`（オフライン確認・再アップロード用）

```bash
# 既存 manifest から CDN → static/otc へ一括取得
py -3.11 scripts/export_otc_images_local.py

# 同期スクリプトは --upload 時に static/otc にも保存（--no-local で無効化）
py -3.11 scripts/sync_otc_images_from_matsukiyo.py --limit 200 --upload --local-dir static/otc
```

オフラインでローカル画像を使う場合（任意）:

```bash
MEDICINE_IMAGE_CDN_BASE=http://127.0.0.1:5000/static/otc/
```

S3 API エンドポイント（ユーザー向け URL ではない）:

`https://2a1ac0678cd0b207ca4fa5681a9a0690.r2.cloudflarestorage.com/medicine-recommend-otc-images`

## マツキヨ未掲載品 — 公式サイト等からの手動アップロード

マツキヨココカラ online に掲載がない OTC でも、**製造販売元の公式商品画像**があれば R2 へ手動配置できる。スラッグは `slugify_product_name()` と同一（`src/services/medicine_image_urls.py`）。

### 例: トキワイブプロエースＡ（2026-07-25）

| 項目 | 値 |
|------|-----|
| ソース | `https://www.tokiwayakuhin.co.jp/img/goods/L/H177300.jpg` |
| スラッグ | `トキワイブプロエースA` |
| 公開 URL | `https://images.yutok.dev/otc/トキワイブプロエースA.webp` |

```bash
# 公式 JPG を取得 → WebP 変換 → R2 PUT（.env の R2_* 必須）
curl -sL -o /tmp/tokiwa.jpg 'https://www.tokiwayakuhin.co.jp/img/goods/L/H177300.jpg'
py -3.11 scripts/upload_r2_otc_image.py トキワイブプロエースA /tmp/tokiwa.jpg
curl -sI 'https://images.yutok.dev/otc/トキワイブプロエースA.webp'
```

候補画像の調査ログ: `log/analysis/otc_image_candidates/`

### 画像が見つからない品目

**イブプロフェン錠200S** 等、公式 EC・ドラッグ EC にパッケージ写真がなく R2 未配置の品目は、推奨画面に載せない運用とする（[RECOMMENDATION_PRODUCT_FILTERS.md](./RECOMMENDATION_PRODUCT_FILTERS.md)）。添付文書 PDF の刷り込みは UI 向きではない。

## 関連

- 一括計画: [.cursor/plans/aws_cloudflare_一括改善_afd2b593.plan.md](../../.cursor/plans/aws_cloudflare_一括改善_afd2b593.plan.md)
- AWS 機能 env: [AWS_FEATURES_ROLLOUT.md](./AWS_FEATURES_ROLLOUT.md)
