# PMDA データ取り込み運用

## 概要

PMDA 公的情報（市販薬検索・添付文書相互作用・副作用）を `data/*.csv` 正本に取り込み、
[`build_medicine_kb_documents.py`](../../scripts/build_medicine_kb_documents.py) 経由で Bedrock Medicine KB に反映する。

## データソース

| ソース | URL | 出力 CSV |
|--------|-----|----------|
| 市販薬検索 | https://www.pmda.go.jp/PmdaSearch/otcSearch/ | `data/otc_medicine_data.csv` |
| 添付文書（相互作用 §10） | https://www.info.pmda.go.jp/psearch/PackinsSearch | `data/medicine_interactions.csv` |
| 添付文書（副作用 §11） | https://www.info.pmda.go.jp/psearch/PackinsSearch | `data/medicine_side_effects.csv` |

**注意:** PMDA は一括 API を提供していない。live fetch は **礼儀正しい低速アクセス**（2.5–5s jitter、30 件/セッション上限、24h クールダウン）。

## 利用規約・robots.txt（Phase 0 調査結果）

| 項目 | 結論 |
|------|------|
| 一括ダウンロード API | **なし** |
| info.pmda PackinsSearch | GET パラメータのみではエラー。Bot 対策（cookie/fingerprint）あり。**GO/NO-GO テスト必須** |
| 副作用等報告データセット | 簡易パスワード必須。**自動一括 DL は不可** |
| 推奨 | catalog expansion を正本とし、live は **PMDA 原文取得成功分のみ差し替え** |

## live fetch ポリシー（Phase B 以降）

| 項目 | 値 |
|------|-----|
| リクエスト間隔 | **2.5–5.0 秒**（uniform jitter、`--min-interval 3` 下限） |
| 1 セッション上限 | **30 件**（`--live-batch-size 30`） |
| abort 条件 | 403 / 429×3 / 連続 empty HTML×3 |
| 429 バックオフ | 60s → 120s → 300s 後 abort |
| 再実行禁止 | abort 後 **24 時間**（`data/pmda/manifest.json`） |
| User-Agent | 固定 `medicine-recommend-pmda-import/1.0`（偽装禁止） |
| 実行場所 | **ローカル回線のみ**（CodePipeline / AWS IP 禁止） |
| 推奨時間帯 | JST 22:00–06:00 |

### GO/NO-GO 手順

```bash
.venv/bin/python scripts/pmda/fetch_interactions.py --live --limit 5 --min-interval 3
```

- 403/429/empty HTML **0 件** → GO
- **1 件でも** → NO-GO。live 中止。高リスクペアは `data/pmda/staging/interactions.json` 手動配置

### abort 時の手動フォールバック

1. `data/pmda/staging/interactions.json` に `{ "rows": [ ... ] }` を配置（出典: `PMDA PackinsSearch`）
2. `python scripts/pmda/run_pmda_import.py --sources interactions --dry-run`
3. 問題なければ merge（`--live` なし）

## パイプライン

```bash
# dry-run（catalog expansion、CSV 変更なし）
.venv/bin/python scripts/pmda/run_pmda_import.py --dry-run

# merge 実行（バックアップ自動作成）
.venv/bin/python scripts/pmda/run_pmda_import.py

# live 小批量（GO/NO-GO 後）
.venv/bin/python scripts/pmda/run_pmda_import.py --sources interactions --live --live-batch-size 30 --limit 30 --dry-run
```

## ディレクトリ

```
scripts/pmda/          # fetch / normalize / validate / merge
data/pmda/
  staging/             # interactions.json, side_effects.json, otc_products.json
  backups/YYYYMMDD/    # import 前 CSV 退避
  manifest.json
  common_rx_medications.json
  otc_ingredients.json # 自動生成
log/analysis/pmda_*.json
```

## 品質ゲート

- `validate_pmda_import.py` — 必須列・重複ペア
- import 前 `data/pmda/backups/` に CSV 退避
- merge 後: `pytest tests/scripts/test_pmda_import.py`
- 推奨順位: `tests/integration/test_golden_regression.py`

## KB 反映（Phase 2）

```bash
python scripts/build_medicine_kb_documents.py
AWS_PROFILE=admin ./scripts/sync-medicine-kb-to-s3.sh
# Bedrock data source 0ZCBZWSQ7N re-ingest
AWS_PROFILE=admin python scripts/eval_medicine_kb.py \
  --phase phase2_kb \
  --output log/analysis/medicine_kb_phase2_YYYYMMDD.json
pytest tests/integration/test_golden_regression.py -q
```

### Phase 2 結果（2026-07-24）

| 指標 | Before (baseline) | After (Phase 2) | After (ingestion fix) |
|------|-------------------|-----------------|------------------------|
| score_pass | 65% (13/20) | 80% (16/20) | **85% (17/20)** |
| pass_all (raw) | 60% (12/20) | 80% (16/20) | **80% (16/20)** |
| runtime pass_all | — | — | **85% (17/20)** |
| ingestion failed | — | — | **0**（job `YRKIVGBVZR`） |
| 相互作用 | — | — | **5/5** |

詳細: `log/analysis/medicine_kb_after_ingestion_fix_20260724.json`

### live fetch GO/NO-GO（2026-07-24）

**結果: GO**（iyakuSearch フロー修正後、JST 16:48 実施）

| 項目 | 旧 (PackinsSearch GET) | 新 (iyakuSearch POST) |
|------|------------------------|------------------------|
| 403 / 429 | 0 | **0** |
| empty HTML | 3 → abort | **0**（GO/NO-GO 5 成分） |
| hits | 0 | **29**（8 成分バッチ） |
| エンドポイント | `info.pmda PackinsSearch` GET ❌ | `pmda.go.jp/PmdaSearch/iyakuSearch` POST ✅ |

**本日 live 取得結果**

| ソース | 成分/件数 | HTTP req | hits | CSV merge |
|--------|-----------|----------|------|-----------|
| interactions | 8 優先成分 | 17 | 29 → 27 rows | +8（live_replace） |
| side_effects | 8 優先成分 | 17 | 7 | +1 |
| OTC | 10 品目 | 10 | 0 | 変更なし（品名マッチ要改善） |

出典ラベル: `PMDA iyakuSearch`（`PMDA PackinsSearch` も live_replace 対象）

**OTC live**: 初回 10 品目は PMDA ヒット 0（CSV 製品名と検索結果テキストのマッチ改善が必要）。

## ロールバック

```bash
cp data/pmda/backups/YYYYMMDD/*.csv data/
cp data/pmda/backups/YYYYMMDD/ingredient_dictionary.json data/
```
