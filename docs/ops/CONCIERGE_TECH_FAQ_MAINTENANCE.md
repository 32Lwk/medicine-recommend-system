# Concierge 技術 FAQ / Meta KB 運用ガイド

> 対象: SSOT・public doc・RAG index・eval の更新手順。計画 v3（2026-07-28）に基づく。

## 1. 正本（SSOT）の所在

| 種別 | パス | 用途 |
|------|------|------|
| 技術 SSOT | `docs/concierge/technical/00-11*.md` | architecture 直接注入 + RAG |
| 公開 doc | `docs/public/*.md`（7件） | 法務 direct + RAG 横断 |
| JSON | `src/content/concierge_knowledge.ja.json` | capabilities / app 要約 |
| リサーチ | `docs/concierge/technical/research/` | 内部メモ（ユーザー回答に直引用しない） |

## 2. 更新フロー

### 2.1 技術 FAQ を追加・修正するとき

1. SSOT md を編集（ユーザー向け文言のみ。env 名は書かない）
2. `docs/concierge/technical/README.md` 索引を更新
3. 必要なら `concierge_knowledge.ja.json` を同期
4. ローカル eval:
   ```bash
   .venv/bin/python scripts/eval_concierge_kb.py --provider local --all-fixtures
   .venv/bin/python scripts/eval_concierge_intent_routing.py
   .venv/bin/python scripts/eval_concierge_technical_quality.py
   ./scripts/concierge-technical-faq-contract.sh
   ```
5. embedding index 再ビルド（OPENAI_API_KEY あり）:
   ```bash
   .venv/bin/python scripts/build_local_rag_index.py --namespace concierge
   ```

### 2.2 public doc（法務・概要）を更新するとき

1. `docs/public/*.md` を編集
2. **direct intent**（`doc_privacy` / `doc_terms` 等）は RAG ではなく `generate_doc_answer_text` が md 全文参照
3. `tests/fixtures/concierge_kb_legal_meta.yaml` に横断質問があれば expected を確認
4. boundary eval: `.venv/bin/python scripts/eval_concierge_boundary.py`

### 2.3 CHANGELOG

- RAG index から **除外**（`local_rag_index.py` の `_CONCIERGE_RAG_EXCLUDED_CONTENT`）
- 要約は `scripts/write_changelog_digest.py` → `static/changelog-digest.json`
- retrieve boost: `doc_changelog` intent + digest `score_hint`

## 3. Eval tier（CI）

| Tier | 内容 | LLM | 実行タイミング |
|------|------|-----|----------------|
| L1 | pytest contract + intent routing + quality + boundary + LINE smoke | なし | MR / push（GitLab `local-rag-retrieve-eval` 拡張） |
| L2 | retrieve 60問 + benchmark | なし | CodeBuild `RUN_LOCAL_RAG_EVAL=true` |
| L3 | live LLM quality + dialogue E2E | あり | 手動 / `RUN_LIVE_QUALITY=1` |

### L3 ライブ（OPENAI_API_KEY 必須）

```bash
# ルール tier（技術 35 + 口語 24）
.venv/bin/python scripts/eval_concierge_technical_quality_live.py --tier rule
.venv/bin/python scripts/eval_concierge_technical_quality_live.py \
  --fixture tests/fixtures/concierge_live_casual.yaml --tier rule

# judge tier（L3b 救済 / L3c 厳格）
.venv/bin/python scripts/eval_concierge_technical_quality_live.py --tier judge-failures
.venv/bin/python scripts/eval_concierge_technical_quality_live.py --tier judge-pass

# 多ターン E2E（scripted + GPT ユーザー simulation）
.venv/bin/python scripts/eval_concierge_dialogue_e2e.py --judge

# 一括
RUN_LIVE_QUALITY=1 RUN_LIVE_JUDGE=1 ./scripts/run_concierge_comprehensive_eval.sh
```

| L3 目標 | 閾値 |
|---------|------|
| technical + casual live（rule） | ≥ 85% / ≥ 80% |
| dialogue E2E | ≥ 80% |

### L1 一括（ローカル）

```bash
./scripts/concierge-technical-faq-contract.sh
.venv/bin/python scripts/eval_concierge_intent_routing.py --min-pass-pct 92
.venv/bin/python scripts/eval_concierge_technical_quality.py --min-pass-pct 90
.venv/bin/python scripts/eval_concierge_boundary.py
.venv/bin/python scripts/eval_concierge_line_smoke.py
```

### L2 一括

```bash
RUN_LOCAL_RAG_BENCHMARK=1 ./scripts/run_local_rag_eval.sh
```

## 4. GO 条件（v3）

| eval | 閾値 |
|------|------|
| retrieve（全 fixture） | ≥ 90% |
| intent routing | ≥ 92%（目標 100%） |
| quality contract | ≥ 90% |
| boundary | 100% |
| LINE smoke | 100% |

## 5. デプロイ時

- **GCP Cloud Run**: `docs/concierge/` をイメージ同梱。BM25 corpus は **起動後 lazy 構築**（`get_bm25_index`）。embedding npz（`build/local_rag/`）は gitignore — 本番は BM25 中心またはランタイム embedding
- **Concierge Bedrock KB**: **利用しない**（2026-07-28〜）。Medicine Bedrock KB は AWS staging のみ任意
- **AWS CodeBuild**: `sync-all-kb-to-s3.sh` 内で `build_local_rag_index.py --namespace all`（OPENAI_API_KEY 時）
- post_deploy: `RUN_LOCAL_RAG_EVAL=true` + `LOCAL_RAG_EVAL_STRICT=true` で L2 gate

## 6. faithfulness / sanitize

- 出力後段: `src/services/concierge_output_sanitize.py`
  - env 名・内部パス除去
  - 法務断言緩和（`doc_terms` / `doc_privacy`）
  - 運営者 PII マスク（`doc_operator`）
- 法務 direct intent は **RAG スキップ**（`augment_reference_with_kb`）

## 7. 四半期レビュー

- `research/question-coverage-matrix.md` の未カバー質問を確認
- mitou/archive から公開可能な更新があれば SSOT 11 へ反映
- eval fixture に口語 paraphrase を追加

## 8. 関連スクリプト

| スクリプト | 役割 |
|-----------|------|
| `scripts/eval_concierge_kb.py` | retrieve eval |
| `scripts/eval_concierge_intent_routing.py` | intent probe |
| `scripts/eval_concierge_technical_quality.py` | SSOT 参照 contract |
| `scripts/eval_concierge_boundary.py` | faithfulness boundary |
| `scripts/eval_concierge_line_smoke.py` | LINE contract |
| `scripts/build_local_rag_index.py` | embedding index |
| `scripts/run_concierge_comprehensive_eval.sh` | L1 + 任意 L3 一括 |
| `scripts/eval_concierge_technical_quality_live.py` | L3 ライブ品質（tier: rule / judge-*） |
| `scripts/eval_concierge_dialogue_e2e.py` | L3 多ターン E2E + GPT ユーザー simulation |
| `src/services/concierge_live_judge.py` | L3 LLM judge 共有 |
