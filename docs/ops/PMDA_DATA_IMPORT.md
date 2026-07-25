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
| 推奨 | **live + raw 再パース** を正本とする。catalog expansion はテンプレート重複が多く **復元しない** |

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

## 正本ポリシー（2026-07-24 更新）

| 項目 | 方針 |
|------|------|
| 正本 | **`data/medicine_interactions.csv` / `data/medicine_side_effects.csv`** |
| 再生成元 | **`data/pmda/raw/ingredients/*.json` の `detail_html`**（680 件） |
| catalog expansion | **復元しない**（~2,869 行テンプレートは RAG 品質を下げる） |
| 手動 curated | 出典空欄行（ix ~73 / se ~34）は **常に保持** |
| PMDA 行 | `live_replace=True` で **全置換**（旧 PMDA 行は残さない） |

### 正本品質（再パース後）

| CSV | 合計 | PMDA | 品質フィルタ |
|-----|------|------|--------------|
| interactions | 180 | 107 | 100% OK |
| side_effects | **271** | **237** | 100% OK |

### 既知の残課題（purge 前に認識）

- interactions: **複数薬剤が 1 行に混在**（~27/107）— §10 表行単位パースが次改善
- side_effects: ~~§17 臨床成績の末尾混入~~ → **2026-07-24 後半: §17 終端 + section17_leak フィルタで解消**（237 行）

---

## raw HTML 永続化

fetch 成功時に **プロセス内メモリだけでなくディスクへ保存**。パーサー修正後も **HTTP 再取得なし**で正本を再生成できる。

### 保存先

```
data/pmda/raw/
  index.json                 # count, by_ingredient → ファイル名
  ingredients/{sha20}.json   # 成分ごとの raw
```

### JSON スキーマ

```json
{
  "ingredient": "成分名",
  "fetched_at": "ISO8601 UTC",
  "status": "ok | empty_section",
  "detail_html": "<html>…</html>",
  "section10_text": "（参考・再パースでは使わない）",
  "section11_text": "（参考・再パースでは使わない）"
}
```

### 関連スクリプト

| スクリプト | 用途 |
|-----------|------|
| `raw_store.py` | `save_ingredient_raw()` / `raw_stats()` |
| `fetch_ingredient_live.py` | fetch 後に raw 保存 |
| `requeue_missing_raw.py` | raw 欠損の done を pending に戻す |
| `reparse_from_raw.py` | **680 raw → staging → CSV** |
| `quality_filter.py` | merge 前 reject |

---

## 正本再生成（reparse）

```bash
# 1. dry-run（staging + validate のみ）
.venv/bin/python scripts/pmda/reparse_from_raw.py --dry-run

# 2. 本番（data/pmda/backups/YYYYMMDD/ に CSV 退避 → merge）
.venv/bin/python scripts/pmda/reparse_from_raw.py

# 3. テスト
.venv/bin/pytest tests/scripts/test_pmda_parser.py tests/scripts/test_pmda_raw_store.py -q
```

**重要:** 再パースは **`detail_html` から §10/§11 を再抽出**。保存済み `section10_text` / `section11_text` は旧パーサー出力のため使わない。

---

## パーサー修正概要（2026-07-24）

| 問題 | 修正 |
|------|------|
| `10.2併用注意` と `10.2 併用注意` の不一致 | 正規表現で空白許容 |
| セクション未検出 → 全文返却 | **空文字**（§18/HTML 混入防止） |
| side_effects キーワード列挙 | §11 要約（最大 800 字） |
| interactions 240 字スニペット | partner 周辺 500 字 |
| merge `live_replace` バグ | 旧 PMDA 行が OR 条件で残る問題を修正 |
| §17 臨床成績の §11 末尾混入 | `_SECTION11_END` に `17. 臨床成績` 追加 + `section17_leak` フィルタ |

---

## Bedrock 評価（任意）

改善内容・正本 CSV を **独立に** LLM 評価する場合:

```bash
export AWS_BEARER_TOKEN_BEDROCK='(短期キー)'
export AWS_REGION=us-east-1
.venv/bin/python scripts/eval_pmda_bedrock.py
# → log/analysis/pmda_bedrock_eval.json
```

日次トークン上限（Throttling）時は error を JSON に記録。正本生成自体は **ルールベース**（Bedrock 不要）。

---

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
scripts/pmda/          # fetch / normalize / validate / merge / raw / reparse
data/pmda/
  raw/ingredients/     # 成分別 detail HTML（正本の種・680 件）
  staging/             # interactions.json, side_effects.json, otc_products.json
  backups/YYYYMMDD/    # import 前 CSV 退避
  manifest.json
  common_rx_medications.json
  otc_ingredients.json # 自動生成
log/analysis/pmda_*.json
```

## 品質ゲート

- `validate_pmda_import.py` — 必須列・重複ペア
- `quality_filter.py` — HTML ボイラープレート / §18 誤抽出 / §17 混入 / 短すぎ行を reject
- import 前 `data/pmda/backups/` に CSV 退避
- merge 後: `pytest tests/scripts/test_pmda_import.py tests/scripts/test_pmda_parser.py`
- 正本評価: `log/analysis/pmda_canonical_eval_report.json`
- 推奨順位: `tests/integration/test_golden_regression.py`

## KB 反映（Phase 2）

PMDA 正本 CSV 更新後、Medicine Managed KB へ一括反映:

```bash
AWS_PROFILE=admin ./scripts/reflect_medicine_kb.sh
# --skip-reparse  既に reparse 済みの場合
# --skip-eval     ingestion 後 eval を省略
```

手動ステップ:

```bash
.venv/bin/python scripts/pmda/reparse_from_raw.py
python scripts/build_medicine_kb_documents.py --clean
AWS_PROFILE=admin ./scripts/sync-medicine-kb-to-s3.sh
AWS_PROFILE=admin python scripts/start_bedrock_kb_ingestion.py 30BCEJCJHA 0ZCBZWSQ7N --skip-preflight
```

### PMDA 正本 → KB 反映結果（2026-07-24 後半）

**ジョブ**: `OG6SSAO4QN`（kb `30BCEJCJHA` / ds `0ZCBZWSQ7N`）— **COMPLETE**

| 指標 | 値 |
|------|-----|
| scanned | 19,952 |
| modified | 19,859 |
| new | 87 |
| deleted | 318 |
| failed | 1（`side_effects/グリチルレチン酸.md` — CSV から section17_leak で除外済みの stale メタデータ） |

**eval**（`log/analysis/medicine_kb_pmda_eval_20260724.json`）:

| 指標 | 値 |
|------|-----|
| pass_all (raw) | 75%（15/20） |
| score_pass | 85%（17/20） |
| 相互作用 | **5/5** |

詳細: `log/analysis/medicine_kb_pmda_reflect_20260724.json`

### Phase 2 結果（2026-07-24 前半・ingestion fix）

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

### OTC Cloud live 完走（2026-07-25）

**Cloud IP GO/NO-GO**: **GO**（403/429 = 0、hits = 7/10）

```bash
.venv/bin/python scripts/pmda/fetch_otc.py \
  --live --limit 10 --min-interval 1 --allow-daytime --force
# → requested=18 hits=7 errors=3 abort=''
```

**完走ランナー**: `scripts/pmda/run_live_fetch_otc_cloud.py`（4h gap / 日次上限無効、`--merge-every 100`、`--max-hours 20`）

| 指標 | 値 |
|------|-----|
| otc pending | **0**（unique key 7,251 = done 6,011 + failed/orphans 1,240） |
| CSV 行数 | **7,495**（全行保持・PMDA 優先 merge） |
| ヒット率 | **82.9%**（6,011 / 7,251）※目標 95% 未達 |
| orphans | **1,240**（理由: 全て `not_found` — PMDA otcSearch に該当なし） |
| HTTP 総数 | **13,929**（session 最終、errors **0**） |
| 所要時間 | **~14.5h**（elapsed_sec 52,290） |
| abort | false（403 リトライ 0 回） |
| Cloud IP | GO（遮断なし） |

進捗: `log/analysis/pmda_cloud_otc_20260725.json`  
orphans: `log/analysis/pmda_otc_orphans_20260725.json`

**マッチ改善（本ランで実装）**

- otcSearch は form 全項目 + `btnA.x/y` POST、詳細は `/PmdaSearch/otcDetail/{fname}`
- 品名: NFKC・括弧注釈除去・剤形/容量除去・空白無視・検索フォールバック（最大 5 候補）
- スコア: 完全一致 → 正規化一致 → 部分一致（ratio ≥ 50、弱部分一致の底上げは廃止）

**品質評価（vs `data/pmda/backups/20260724`）**

| 項目 | 結果 |
|------|------|
| 行・キー保持 | unique 7,250 → 7,251（欠落 0、orphans も baseline 保持） |
| 効能効果 / 用法用量 | 更新 5,473 / 5,940（空欄化 0） |
| 年齢制限 | 非空 44.4% → 48.0%（+259、新規は全て「歳/才」含む） |
| 成分 | 変化なし（既存値維持） |
| 分類 / 医薬品の種類 | **社内タクソノミ維持**（初回 merge で PMDA 薬効分類・リスク区分が混入→復元済み。以降は merge 対象外） |
| ドーピング列 | 変化 0 |
| 推奨フィルタ | 解熱鎮痛薬 1,207 / 風邪薬 1,131（baseline と同数） |

スポット: バファリンA・ロキソニンS の効能/用法/年齢は PMDA 添付文書と整合。

**PMDA 情報の保全（再取得なし・2026-07-25）**

| 置き場 | 内容 |
|--------|------|
| `data/otc_medicine_data.csv` の `pmda_薬効分類` / `pmda_リスク区分` | 専用カラム追加済み。過去ランは detail HTML 未保全のため**空**。今後の live fetch で充填 |
| `data/pmda/raw/otc/applied_updates_20260725.jsonl` | baseline 差分で回収した効能・用法・年齢の before/after（5,943 品目） |
| `data/pmda/raw/otc_products/*.json` | 同上の品目単位 raw（parsed のみ。`detail_html` 無し） |
| `data/pmda/raw/otc_index.json` | product_key → raw ファイル索引 |

```bash
# カラム追加 + 既存反映分の raw 保全（HTTP なし）
.venv/bin/python scripts/pmda/archive_otc_pmda_applied.py --stamp YYYYMMDD
```

今後の `process_otc_product` は成功時に `detail_html` 付きで `raw/otc_products/` へ保存し、`pmda_*` を CSV へ merge する。

**side_effects 残 pending 10 件**も本 Phase で消化（pending=0）。その後 `reparse_from_raw.py` で CSV 正本再構築。

**KB / eval（Cloud 環境）**

- `scripts/build_medicine_kb_documents.py` まで完了（products 7,495）
- S3 sync / Bedrock re-ingest / `eval_medicine_kb.py` は **AWS 未設定のため未実施**（ローカルまたは AWS 資格情報あり環境で C-3 続き）

## ロールバック

```bash
cp data/pmda/backups/YYYYMMDD/*.csv data/
cp data/pmda/backups/YYYYMMDD/ingredient_dictionary.json data/
```
