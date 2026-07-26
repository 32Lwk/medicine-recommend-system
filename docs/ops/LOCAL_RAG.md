# Local RAG 運用ガイド

Bedrock Managed KB の代替として、リポジトリ内コーパス（`build/medicine` + Concierge SSOT）から retrieve する local RAG の設定・ビルド・評価手順。

## 方針

- **推奨順位（scoring）は変更しない** — RAG は説明・Q&A 層のみ
- AWS ステージング / GCP 本番で同一実装（`CONCIERGE_RAG_PROVIDER=local`, `MEDICINE_RAG_PROVIDER=local`）
- OpenSearch OCU なし。ランタイムは BM25 +（任意）OpenAI embedding ハイブリッド

## 環境変数

| 変数 | デフォルト | 説明 |
|------|-----------|------|
| `CONCIERGE_RAG_PROVIDER` | `local` | `local` / `bedrock_kb` |
| `MEDICINE_RAG_PROVIDER` | `local` | `local` / `bedrock_kb` |
| `LOCAL_RAG_MEDICINE_EMBEDDING_MODEL` | `text-embedding-3-large` | Medicine query embed |
| `LOCAL_RAG_CONCIERGE_EMBEDDING_MODEL` | `text-embedding-3-small` | Concierge query embed |
| `LOCAL_RAG_HYBRID_ALPHA` | `0.4` | BM25 重み（残り cosine） |
| `LOCAL_RAG_EMBED_CACHE_TTL_SEC` | `600` | クエリ embed LRU TTL |
| `LOCAL_RAG_FALLBACK_BM25_ONLY` | `true` | embed 失敗時 BM25 のみ |
| `LOCAL_RAG_MEDICINE_HYBRID` | `false` | Medicine BM25 path で embedding hybrid rerank |
| `LOCAL_RAG_RETRIEVE_CACHE` | `true` | Redis retrieve キャッシュ（local） |
| `LOCAL_RAG_RETRIEVE_CACHE_TTL_SEC` | `600` | キャッシュ TTL |
| `LOCAL_RAG_CONTEXT_LLM` | `false` | 会話 follow-up の LLM query rewrite |
| `LOCAL_RAG_CATEGORY_LLM_FALLBACK` | `false` | カテゴリ confidence 低時のみ LLM |
| `MEDICINE_QA_FOCUS_LLM` | `false` | rule が general のみのとき focus LLM 補完 |
| `MEDICINE_QA_FOCUS_LLM_MODEL` | `gpt-4o-mini` | focus 補完モデル |
| `LOCAL_RAG_MIN_SCORE` | `0.4` | 最低スコア |
| `COMPREHEND_MEDICAL_ENABLED` | AWS のみ | Medicine クエリ拡張（GCP は **router + ルールベース NER** で代替） |

## Medicine QA 配線（Phase A）

`MEDICINE_RAG_PROVIDER=local`（GCP 本番デフォルト）でも **`augment_medicine_prompt_with_kb()` が KB ブロックを Ask / Explanation プロンプトに注入**する。

- 入口: [`src/services/bedrock_kb_retrieve.py`](../src/services/bedrock_kb_retrieve.py) — `retrieve_medicine_context`, `augment_medicine_prompt_with_kb`
- Ask: [`src/core/medicine/medicine_response_builder.py`](../src/core/medicine/medicine_response_builder.py) — `conversation_history` を KB retrieve に渡す
- 文脈: [`src/services/local_rag_context.py`](../src/services/local_rag_context.py) — `build_contextual_retrieval_query`

### GO 条件（retrieve + QA）

| 評価 | 目標 | コマンド |
|------|------|----------|
| 公式 Medicine fixture | ≥ 95% | `eval_medicine_kb.py --provider local` |
| 言い換え 19 問 | ≥ 95% | `eval_local_rag_paraphrase.py` |
| diverse + context 52 問 | ≥ 90% | `eval_local_rag_diverse.py` |
| **Medicine QA E2E** | ≥ 90%（19 問） | `MEDICINE_RAG_PROVIDER=local eval_medicine_qa_e2e.py` |
| LLM ストレス（任意） | ≥ 85% | `eval_local_rag_diverse.py --with-llm-stress` |
| P95 retrieve | < 800ms | `local_rag_retrieve_benchmark.py` |

### Medicine QA multi-focus retrieve（Phase B）

比較・成分・年齢・写真など複合 intent 向けに **multi-doc retrieve** を追加。

- 入口: [`src/services/local_rag_retrieve.py`](../src/services/local_rag_retrieve.py) — `retrieve_medicine_docs_multi`
- ルーティング: [`src/services/local_rag_router.py`](../src/services/local_rag_router.py) — `route_medicine_docs`（`comparison` カテゴリ、CSV brand 解決）
- KB 統合: [`src/services/bedrock_kb_retrieve.py`](../src/services/bedrock_kb_retrieve.py) — `qa_focuses` / focus 別 category fallback
- focus 推定: [`src/services/medicine_qa_routing.py`](../src/services/medicine_qa_routing.py) — `infer_medicine_qa_focuses`

E2E fixture（`tests/fixtures/medicine_qa_e2e.yaml`）に比較・写真・成分・年齢を追加。比較・成分・年齢は `recommended_medicines` を fixture に明示すると retrieve が安定する。

広域 eval（`tests/fixtures/local_rag_broad_eval.yaml`）に `comparison` カテゴリ 3 問を追加。`eval_local_rag_broad.py` で category + prefix を検証。

### Medicine QA ロバストネス eval（Phase C）

日常口語・方言・指示語 follow-up・GPT 会話シミュレーションで **routing（focus / clarify / unified / info_q）** を検証。

| 評価 | 目標 | コマンド |
|------|------|----------|
| 固定 everyday + context | 100% | `eval_medicine_qa_robustness.py` |
| + GPT 会話 | ≥ 90% | `--with-gpt-conversation` |
| + LLM 言い換え stress | ≥ 90% | `--with-llm-stress`（`MEDICINE_QA_FOCUS_LLM` 自動 ON） |

- スクリプト: [`scripts/eval_medicine_qa_robustness.py`](../scripts/eval_medicine_qa_robustness.py)
- Fixture: `tests/fixtures/medicine_qa_everyday_eval.yaml`（31 単発 + 12 文脈）, `medicine_qa_gpt_conversation.yaml`
- 技術詳細: [`docs/dev/MEDICINE_QA_ROUTING.md`](../dev/MEDICINE_QA_ROUTING.md)
- 成果物: `log/analysis/medicine_qa_robustness_eval.json`

**2026-07-26 結果**: 固定 43/43、GPT + LLM stress 含む 74/75 (98.7%)

## コスト目安（~10k retrieve/日）

| 項目 | 月額 |
|------|------|
| ランタイム embed（ハイブリッド） | ~$4–5 |
| 増分 index rebuild | ~$0.3–0.5 |
| Comprehend Medical（AWS） | ~$1–3 |
| **合計** | **~$6–9** |

OpenSearch OCU **$0**（KB 削除済み）。

## Fallback

- OpenAI embed 障害 → `LOCAL_RAG_FALLBACK_BM25_ONLY=true` で BM25 のみ
- router 命中時 → embed スキップ（レイテンシ短縮）
- Bedrock KB 復旧手順: [`scripts/resume-aws-bedrock-kb.sh`](../scripts/resume-aws-bedrock-kb.sh)

## 単体テスト

```bash
.venv/bin/pytest tests/services/test_local_rag_router.py -q
```

## CI / CodeBuild

| 変数 | デフォルト | 説明 |
|------|-----------|------|
| `RUN_LOCAL_RAG_EVAL` | `false` | CodeBuild post_deploy で retrieve eval |
| `LOCAL_RAG_EVAL_STRICT` | `false` | eval 失敗でビルド失敗 |
| `RUN_LOCAL_RAG_E2E_HTTP` | `false` | staging URL で HTTP E2E（要 `E2E_BASE_URL`） |
| `LOCAL_RAG_MIN_MEDICINE_PCT` | `80` | Medicine pass 率下限 |
| `LOCAL_RAG_MIN_CONCIERGE_PCT` | `90` | Concierge pass 率下限 |

```bash
# 手動 / GitLab CI 相当
chmod +x scripts/run_local_rag_eval.sh
RUN_LOCAL_RAG_BENCHMARK=1 ./scripts/run_local_rag_eval.sh

# レイテンシのみ
.venv/bin/python scripts/local_rag_retrieve_benchmark.py
```

GitLab CI ジョブ: `.gitlab-ci.yml` → `local-rag-retrieve-eval`

Docker ビルド時に `scripts/build_medicine_kb_documents.py` で `build/medicine/` を生成（`build/` は gitignore）。

## E2E smoke

retrieve 固定（サーバー不要）:

```bash
.venv/bin/python scripts/eval_local_rag_e2e.py
```

HTTP E2E（Concierge + Medicine Q&A、要起動中 app）:

```bash
.venv/bin/python scripts/eval_local_rag_e2e.py --with-http --base-url http://127.0.0.1:5000/
E2E_BASE_URL=https://aws.medicine.yutok.dev/ .venv/bin/python scripts/eval_local_rag_e2e.py --with-http
```

Concierge 技術 FAQ 代表 10 問:

```bash
.venv/bin/python scripts/concierge_local_technical_faq_smoke.py --representative10
```

## コスト・レイテンシ監視

ランタイムは `log/local_rag_detail.jsonl` に structured log を出力:

- `local_rag_retrieve_ms` — retrieve レイテンシ
- `local_rag_embed_*` — embed API 呼び出し（cache hit 含む）

月次見積:

```bash
.venv/bin/python scripts/report_local_rag_cost.py --days 30
```

## 関連

- [`scripts/reflect_medicine_kb.sh`](../scripts/reflect_medicine_kb.sh) — PMDA 更新後 KB 反映 + **local index rebuild / eval**
- [`docs/ops/AWS_BEDROCK_KB.md`](AWS_BEDROCK_KB.md) — Bedrock KB 一時停止・復旧
