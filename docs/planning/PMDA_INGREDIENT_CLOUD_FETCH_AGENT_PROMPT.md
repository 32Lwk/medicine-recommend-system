# Cursor Cloud Agent 命令文 — PMDA 成分 fetch（並列・高速）

**このファイルを Cursor Cloud Agent に貼り付けて実行する。**

---

## あなたの役割

リポジトリ `medicine-recommend` で PMDA 成分データ fetch を担当する。  
**Coordinator（1 体）** または **Worker shard 0–3（最大 4 体並列）** のどちらか。  
メッセージ冒頭で `ROLE=coordinator` または `ROLE=worker SHARD_ID=0`（0–3）を宣言すること。

---

## 確定方針

| 項目 | 内容 |
|------|------|
| 対象 | OTC **1,337 ユニーク成分**（§10 相互作用 + §11 副作用） |
| 再試行 | **`--requeue-failed`** — 約 **848 成分**を再 fetch |
| 100% | **1,337 成分すべてに fetch を試行**。empty_section / failed 残存は **受け入れてクローズ** |
| 環境 | **Cursor Cloud Agent**（VM ごとに 1 Worker = 1 シャード） |
| 反映範囲 | **CSV 更新 + local RAG rebuild まで**（**AWS S3 / Bedrock は今回しない**） |
| 並列 | **4 シャード同時起動**（別 Agent 4 体）。同一 VM 内の multiprocess 並列は **禁止** |

---

## 禁止事項

- AWS IP / CodeBuild からの live fetch
- 同一 Cloud Agent 内で複数 shard を同時実行
- `catalog expansion` 復元
- User-Agent 偽装
- **git push**（ユーザー指示まで禁止）
- `reflect_medicine_kb.sh` / S3 sync / Bedrock ingestion

---

# ROLE=coordinator（最初に 1 体だけ実行）

## Step C0 — GO/NO-GO

```bash
cd "$REPO_ROOT"
python3 -m venv .venv 2>/dev/null || true
.venv/bin/pip install -q -r requirements-prod.txt 2>/dev/null || pip install -q -r requirements-prod.txt

.venv/bin/python scripts/pmda/fetch_interactions.py --live --limit 5 --min-interval 3
```

403/429/empty HTML **1 件でも** → **全 Worker 中止** し、完了報告で NO-GO を記載。

## Step C1 — キュー再構築 + 4 シャード分割

```bash
chmod +x scripts/pmda/start_cloud_ingredient_fetch.sh
./scripts/pmda/start_cloud_ingredient_fetch.sh \
  --prepare-queue --requeue-failed \
  --prepare-shards 4 \
  --fetch-only
```

期待出力 `total_pending` ≈ **848**。`per_shard` は各 **~200–220** 成分。

## Step C2 — Worker 4 体を並列起動

Cursor 上で **Cloud Agent を 4 つ同時起動** し、それぞれにこのファイルの **Worker 節** を貼る:

| Agent | 貼り付け時の先頭行 |
|-------|-------------------|
| Agent A | `ROLE=worker SHARD_ID=0 SHARD_COUNT=4` |
| Agent B | `ROLE=worker SHARD_ID=1 SHARD_COUNT=4` |
| Agent C | `ROLE=worker SHARD_ID=2 SHARD_COUNT=4` |
| Agent D | `ROLE=worker SHARD_ID=3 SHARD_COUNT=4` |

## Step C3 — 全 Worker 完了後（コーディネータ再開）

```bash
./scripts/pmda/start_cloud_ingredient_fetch.sh --merge-shards --shard-count 4 --fetch-only

.venv/bin/python scripts/pmda/reparse_from_raw.py
.venv/bin/pytest tests/scripts/test_pmda_parser.py tests/scripts/test_pmda_import.py tests/scripts/test_pmda_raw_store.py -q

.venv/bin/python scripts/build_medicine_kb_documents.py --clean
.venv/bin/python scripts/build_local_rag_index.py --namespace medicine

.venv/bin/python scripts/eval_medicine_kb.py --provider local
.venv/bin/python scripts/eval_medicine_qa_robustness.py
```

## Step C4 — コミット（push 禁止）

```bash
git add data/medicine_interactions.csv data/medicine_side_effects.csv
git add data/pmda/manifest.json data/pmda/raw/ data/pmda/shards/
git add build/medicine/ build/local_rag/ 2>/dev/null || true
git add log/analysis/pmda_ingredient_cloud_*.json log/analysis/pmda_ingredient_cloud_*.log
git status
```

コミット例: `feat(pmda): parallel Cloud ingredient fetch — expand CSV and local RAG`

---

# ROLE=worker SHARD_ID={0|1|2|3} SHARD_COUNT=4

**他の Worker と同時並行実行する。Coordinator の C1 完了後に開始。**

## Step W1 — 環境

```bash
cd "$REPO_ROOT"
python3 -m venv .venv 2>/dev/null || true
.venv/bin/pip install -q -r requirements-prod.txt 2>/dev/null || pip install -q -r requirements-prod.txt
```

`SHARD_ID` を 0, 1, 2, 3 のいずれかに置換して以下を実行:

```bash
SHARD_ID=0   # ← この Agent 用 ID に変更
SHARD_COUNT=4

./scripts/pmda/start_cloud_ingredient_fetch.sh \
  --shard-id "$SHARD_ID" \
  --shard-count "$SHARD_COUNT" \
  --min-interval 1.0 \
  --merge-every 50 \
  --max-hours 6 \
  --allow-daytime \
  2>&1 | tee "log/analysis/pmda_ingredient_cloud_shard${SHARD_ID}_$(date +%Y%m%d).log"
```

## Step W2 — 完了条件

- `shard.pending == 0` **または** HTTP abort（403/429）
- abort 時: **24h クールダウンを記録**し、当該シャードは **クローズ**（Coordinator が merge）

## Step W3 — Worker 完了報告（チャットに投稿）

```
Worker shard {ID}/4 完了
- processed / done / failed / no_data_ix / no_data_se
- raw_saved
- aborted: true/false
- elapsed_hours
- log path
```

**Worker は reparse / RAG rebuild / git commit を実行しない。**

---

## 完了報告テンプレート（Coordinator 最終）

```markdown
## PMDA 成分 Cloud fetch 結果

### 試行
- 対象成分: 1,337（全成分定義）
- 再試行: 848（requeue-failed）
- 並列: 4 shards

### キュー / raw
- interactions done / failed:
- side_effects CSV: before → after 行
- interactions CSV: before → after 行
- raw ingredients: 件数（ok / empty_section）

### 製品カバー（副作用成分ヒット）
- before: 6055/7495 (80.8%)
- after: ???/7495

### eval
- medicine_kb pass%:
- robustness pass%:

### クローズ
- empty_section / failed 残存: 受け入れ
- AWS KB 反映: 未実施（方針どおり）
```

---

## 時間目安（4 並列）

| フェーズ | 時間 |
|---------|------|
| Coordinator C0–C1 | ~10 分 |
| Worker ×4 並列 fetch | **~30–60 分** |
| Coordinator C3（reparse + RAG + eval） | **~1–2 時間** |
| **合計 wall-clock** | **~1.5–3 時間** |

403/429 abort 時は **+24h** の可能性あり（当該シャードのみクローズ、他シャード結果は保持）。

---

## トラブルシュート

| 症状 | 対処 |
|------|------|
| shard pending が減らない | manifest / shard JSON を確認。abort ならクローズ |
| merge 競合 | Coordinator のみ `--merge-shards` を実行 |
| eval 回帰 | 報告のみ。修正は別 issue |
| OPENAI_API_KEY 無し | `build_local_rag_index.py` スキップ可（BM25 のみ） |

---

## 参照

- `docs/planning/PMDA_INGREDIENT_CLOUD_FETCH_PLAN.md`
- `docs/ops/PMDA_DATA_IMPORT.md`
- `scripts/pmda/ingredient_parallel.py`
