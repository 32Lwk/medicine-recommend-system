# PMDA 成分 Cloud fetch 計画

OTC CSV **1,337 ユニーク成分**の §10（相互作用）・§11（副作用）を PMDA から取得し、  
`data/medicine_interactions.csv` / `data/medicine_side_effects.csv` 正本を拡充 → **Local RAG rebuild** まで行う。

**OTC 製品 fetch は [PR #92](https://github.com/32Lwk/medicine-recommend-system/pull/92) で完走済み（82.9% ヒット）。**

---

## 確定方針（2026-07-28）

| 項目 | 決定 |
|------|------|
| 再試行 | **`--requeue-failed`** — failed 833 + pending 15 ≈ **848 成分** |
| 100% の定義 | **1,337 成分すべてに fetch を試行**（§11/§10 が空・failed は **受け入れてクローズ**） |
| 実行環境 | **Cursor Cloud Agent**（並列シャード） |
| KB 反映 | **CSV 更新 + local RAG rebuild まで**（AWS S3 / Bedrock ingestion は **今回やらない**） |
| abort | 403/429 で当該シャード停止。empty_section / failed は **再試行後も残ればクローズ** |

---

## 現状

| 項目 | 値 |
|------|-----|
| OTC ユニーク成分 | **1,337** |
| fetch done | 489 |
| fetch failed | 833 |
| pending | 15 |
| raw HTML | 689（ok 489 / empty_section 200） |
| CSV side_effects | 275 行 |
| CSV interactions | 185 行 |
| 製品の副作用成分ヒット率 | **6,055 / 7,495（80.8%）** |

---

## 並列構成（推奨: 4 シャード）

| 項目 | 単一 Worker | **4 並列 Cloud Agent** |
|------|------------|------------------------|
| 処理件数 | 848 | **~212 / シャード** |
| HTTP 時間（min-interval 1.0） | ~1.6h | **~25–40 分**（wall-clock） |
| merge + reparse + RAG | +1–2h | **+1–2h**（コーディネータ 1 体） |
| **合計目安** | **~3–4h** | **~1.5–3h** |

各 Cloud Agent は **別 VM / 別出口 IP** を想定。同一 VM 内マルチプロセス並列は **禁止**（PMDA 429 リスク）。

---

## 目標（stretch）

| 指標 | 目標 | 備考 |
|------|------|------|
| 試行成分 | **1,337 / 1,337** | 全成分に HTTP 1 回以上 |
| CSV side_effects | **400–600+** 行 | empty_section・品質フィルタで 1,337 行にはならない |
| CSV interactions | **300–450+** 行 | ペア単位 |
| 製品副作用カバー | **85–95%** | 現状 80.8% → 成分 SE 拡充で向上 |
| eval | robustness **維持** | `eval_medicine_qa_robustness.py` |

---

## フェーズ

### Phase 0 — コーディネータ（1 体）

```bash
# GO/NO-GO
.venv/bin/python scripts/pmda/fetch_interactions.py --live --limit 5 --min-interval 3

# キュー再構築 + failed 再投入 + 4 シャード分割
./scripts/pmda/start_cloud_ingredient_fetch.sh \
  --prepare-queue --requeue-failed \
  --prepare-shards 4 --fetch-only
```

### Phase 1 — Worker ×4（**同時起動**）

Agent 0〜3 を **並列** に Cursor Cloud Agent で起動。  
命令文: `docs/planning/PMDA_INGREDIENT_CLOUD_FETCH_AGENT_PROMPT.md` の Worker 節。

### Phase 2 — コーディネータ（マージ + RAG）

```bash
./scripts/pmda/start_cloud_ingredient_fetch.sh --merge-shards --shard-count 4 --fetch-only
.venv/bin/python scripts/pmda/reparse_from_raw.py
.venv/bin/python scripts/build_medicine_kb_documents.py --clean
.venv/bin/python scripts/build_local_rag_index.py --namespace medicine
.venv/bin/python scripts/eval_medicine_kb.py --provider local
.venv/bin/python scripts/eval_medicine_qa_robustness.py
```

---

## 成果物

- `data/pmda/shards/ingredient_shard_*_of_4.json`
- `data/pmda/raw/ingredients/*.json`
- `data/medicine_*.csv`
- `build/medicine/` + `build/local_rag/`
- `log/analysis/pmda_ingredient_cloud_*.json`

---

## 関連

- `scripts/pmda/ingredient_parallel.py` — シャード分割・マージ
- `scripts/pmda/run_live_fetch_ingredient_cloud.py` — Cloud ランナー
- `docs/planning/PMDA_INGREDIENT_CLOUD_FETCH_AGENT_PROMPT.md` — **Cursor 貼り付け用命令文**
