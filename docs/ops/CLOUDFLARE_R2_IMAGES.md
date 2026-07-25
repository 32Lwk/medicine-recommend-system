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

**画像差し替え後**: R2 のオブジェクトは即時更新されるが、`images.yutok.dev` 経由では Cloudflare CDN が旧画像を最大 4 時間キャッシュする。差し替え直後に反映するには CDN パージが必要。

```bash
# .env に CLOUDFLARE_API_TOKEN / CLOUDFLARE_ZONE_ID を設定後
.venv/bin/python scripts/purge_otc_cdn_cache.py スカイブブロンのどスプレー
```

アプリ側は `data/otc_image_versions.json` の hash を `?v=` クエリに付与し、キャッシュ済み URL でも新画像を取得できる（`src/services/medicine_image_urls.py`）。

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

## 上位50品目一括同期（推奨ログ + Amazon 定番 → R2）

推奨ログ頻度上位と Amazon 健康・パーソナルケア定番 OTC を統合した **50 品目**を [scripts/sync_top50_otc_images.py](../../scripts/sync_top50_otc_images.py) で取得・審査・アップロードする（2026-07-25 時点 **50/50 CDN 確認済み**）。

```bash
# 計画ファイル（品目・スラッグ・R2 状態）
log/analysis/otc_image_sync_top50/top50_plan.json

# 未取得分を一括同期（マツキヨ → 公式URL → 審査 → R2）
.venv/bin/python scripts/sync_top50_otc_images.py --batch 0 --upload

# 12件ずつバッチ実行
.venv/bin/python scripts/sync_top50_otc_images.py --batch 1 --batch-size 12 --upload

# バッチ結果の統合
.venv/bin/python scripts/sync_top50_otc_images.py --merge-only
```

| 成果物 | 内容 |
|--------|------|
| `top50_plan.json` | 50品目リスト（推奨回数・スラッグ・`r2_status`） |
| `top50_results.json` | 同期サマリー（`r2_exists` / `missing_products`） |
| `results_batch*.json` / `results_all.json` | バッチ別の取得・審査・アップロード結果 |
| `official_url_candidates.json` | 公式サイト画像 URL 調査メモ |

**取得優先順位**: ① R2 既存スキップ → ② `OFFICIAL_IMAGE_URLS` / 計画の `official_url` → ③ マツキヨ検索（`MatsukiyoClient`、Referer 必須）

**審査** (`verify_image_match`): 最小解像度・ファイルサイズ・製品名/メーカー名のラベル一致。却下時は `static/otc/review_rejected/{slug}.webp` に保存。

**マツキヨ未掲載24品**はメーカー公式（例: all-p.co.jp）または薬局 EC（楽天 `shop.r10s.jp`、Yahoo ショッピング）のパッケージ画像を `OFFICIAL_IMAGE_URLS` に登録して取得。

### 画像が見つからない品目

**イブプロフェン錠200S** 等、公式 EC・ドラッグ EC にパッケージ写真がなく R2 未配置の品目は、推奨画面に載せない運用とする（[RECOMMENDATION_PRODUCT_FILTERS.md](./RECOMMENDATION_PRODUCT_FILTERS.md)）。添付文書 PDF の刷り込みは UI 向きではない。

## 関連

- 一括計画: [.cursor/plans/aws_cloudflare_一括改善_afd2b593.plan.md](../../.cursor/plans/aws_cloudflare_一括改善_afd2b593.plan.md)
- AWS 機能 env: [AWS_FEATURES_ROLLOUT.md](./AWS_FEATURES_ROLLOUT.md)
