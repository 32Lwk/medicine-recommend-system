# Ingestion failure summary — job C5XVBS9G0L

**KB:** `30BCEJCJHA` / data source `0ZCBZWSQ7N`  
**Job:** `C5XVBS9G0L` (2026-07-24)  
**Result:** COMPLETE with **7,494 failed** (= product MD 全件)

## 原因

Phase 1.5 で product metadata に追加した `has_age_restriction` / `has_doping_info` が **Python bool → JSON `true`/`false`** で出力されていた。Bedrock Managed KB の `metadataAttributes` は **string 型のみ** 受け付けるため、7,494 件の product `*.md.metadata.json` が crawl/index 失敗。

topic/doping（string のみ）は 44 件 new index 成功。eval 85% は topic ヒットで成立していたが product 更新は全滅。

## 修正

`build_medicine_kb_documents.py` — `_stringify_metadata_values()` で全 metadata を string 化（`"true"` / `"false"`）。

## 再 ingest 後の確認

- `numberOfDocumentsFailed` ≈ 0
- Medicine eval ≥ 17/20、相互作用 5/5 維持

## 修正後結果（job YRKIVGBVZR / 2026-07-24）

- **failed: 0**（before: 7,494）
- modified: 19,637 / scanned: 19,671
- Medicine eval raw: **16/20（80%）**、runtime: **17/20（85%）**、相互作用 **5/5**
- `usage-dose-interval` が 0.46 → **0.52 pass** に改善
