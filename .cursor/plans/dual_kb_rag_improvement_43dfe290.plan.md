---
name: Dual KB RAG Improvement
overview: AWS ステージング上の Managed KB 2 系統（Concierge / 医薬品）は ingestion 完了・retrieve 動作済み・一部アプリ接続済み。本タスクは RAG 精度向上と未接続経路の配線。医薬品 KB データ品質（Phase 1）を最優先し、Concierge は手を抜かず Phase 4 で同期・テストを実施する。
todos:
  - id: phase0-baseline
    content: "Step 1 Phase 0 残り: /health/aws 記録、medicine_kb_eval.yaml 20問、baseline 計測スクリプト（ECS env は反映済み）"
    status: completed
  - id: phase1-medicine-docs
    content: "Step 2 Phase 1: build_medicine_kb_documents.py（全7,494品目+interactions等）、sync 更新、re-ingest、20問再計測 80%+"
    status: completed
  - id: phase2-rag-wiring
    content: "Step 3 Phase 2: SSE KB、retrieve クエリ強化、Explanation 方式A、LINE(KB全経路+Comprehend Askのみ)、高リスク CSV 優先"
    status: completed
  - id: phase4-concierge-sync
    content: "Step 4 Phase 4: changelog-digest sync、intent 別 retrieve、augment_reference_with_kb テスト、UI 準備中文言削除"
    status: completed
  - id: phase3-external-data
    content: "Step 5 Phase 3: PubChem enrich（Phase 1 後・同義語不足分のみ）"
    status: pending
  - id: phase5-ops-gcp
    content: "Step 5 Phase 5/6: CodePipeline sync+ingestion、Guardrails/sanitize 検討、GCP RAG ADR"
    status: pending
isProject: false
---

# 技術・医薬品 二系統 RAG 精度改善計画（実装仕様）

## 目的

AWS ステージング上の Managed Knowledge Base 2 系統（Concierge / 医薬品）は **ingestion 完了・retrieve 動作済み・一部アプリ接続済み**。本タスクの目的は **RAG の精度向上** と **未接続経路の配線**。

### 変更してはいけない原則

- 推奨ランキングは [physical_orchestrator.py](src/agents/physical_orchestrator.py) の **rule_based のまま**
- RAG は **説明・Q&A 層のみ** に使う
- KB 取得失敗・空結果時は **既存 CSV / ローカル SSOT へフォールバック**
- GCP 本番は env 未設定 = レガシー動作を維持

---

## 現状（2026-07-24 時点）

### 完了済み

| 項目 | 状態 |
|------|------|
| Managed KB | Concierge `2CNAGQ2V4P` / Medicine `30BCEJCJHA`、ingestion COMPLETE |
| retrieve API | `managedSearchConfiguration` 対応（[bedrock_kb_retrieve.py](src/services/bedrock_kb_retrieve.py)） |
| ECS env | **手動反映済み**（`CONCIERGE_RAG_PROVIDER=bedrock_kb`, `MEDICINE_RAG_PROVIDER=bedrock_kb` 等） |
| コード接続（一部） | AskAgent **非ストリーム**、`generate_usage_notes_and_consultation_with_gpt` |
| S3 sync | [sync-medicine-kb-to-s3.sh](scripts/sync-medicine-kb-to-s3.sh)（現状 **生 CSV のみ**） |
| テスト | [test_bedrock_kb_retrieve.py](tests/services/test_bedrock_kb_retrieve.py)（medicine 側 unit 12 件 pass） |

### 未完了（優先対応 gaps）

1. 医薬品 KB = **生 CSV 5 ファイル** → チャンク品質が低い
2. AskAgent **SSE ストリーム**経路に KB 未注入（[medicine_response_builder.py](src/core/medicine/medicine_response_builder.py) `answer_prompt` 付近）
3. `generate_explanation()` — ルール文字列のみ、KB なし
4. `generate_individual_usage_notes_with_gpt()` — KB なし
5. Comprehend — NLU マージのみ、**retrieve クエリ未利用**
6. LINE — KB / Comprehend 未配線（方針確定済み、下記）
7. `changelog-digest.json` が KB 未同期
8. 評価 harness（医薬品 20 問 YAML）未作成
9. Concierge staging UI「KB 全文同期準備中」文言が残存

### KB 分離（固定）

| KB | ID | S3 prefix | 接続先 |
|----|-----|-----------|--------|
| Concierge | `2CNAGQ2V4P` | `concierge/`, `ops/`, `content/`, `public/` | `augment_reference_with_kb()` |
| Medicine | `30BCEJCJHA` | `medicine/` のみ | `augment_medicine_prompt_with_kb()` |

**旧 KB `4PEWLBZGTH`（Customer-managed / Titan 429）は参照・使用禁止。**

---

## 確定した設計判断

| 項目 | 決定 |
|------|------|
| Phase 1 ingest 範囲 | **全品目約 7,494 MD を一括**生成・ingest |
| 評価 20 問 | **エージェントが作成し baseline 確定**（後から YAML 修正可） |
| LINE Comprehend | **（推奨・採用）** KB RAG は Ask/Explanation 全経路。Comprehend は **Ask/Q&A と retrieve クエリ強化時のみ**（推奨 NLU には入れない） |
| `generate_explanation` | **方式 A**: ルール文字列維持 + retrieve citation 1–2 文末尾追記（LLM 追加呼び出しなし）。方式 B はスコープ外 |
| 検索モード | `BEDROCK_KB_SEARCH_MODE=managed` のみ（`vectorSearchConfiguration` 禁止） |
| デプロイ | AWS staging 検証 → 問題なければ GCP 本番 RAG 検討（Phase 5 ADR） |

---

## 実装順序（この順番を守ること）

### Step 1 — Phase 0 残り（1 日）

**ECS env は反映済み** — 再設定は不要。残タスク:

1. staging `/health/aws` 確認 → 結果を [log/analysis/](log/analysis/) に短く記録
   - `medicine_kb_rag: true`、両 KB ID 表示
2. **新規** [tests/fixtures/medicine_kb_eval.yaml](tests/fixtures/medicine_kb_eval.yaml)
   - 20 問: 相互作用 5 / 用法 5 / 副作用 3 / ドーピング 3 / 年齢 4
   - 各問: `expected_source_prefix`（Phase 0 時点 `medicine/data/`、Phase 1 後 `medicine/products/` 等）、`min_score: 0.5`
3. baseline 計測スクリプト or pytest 追加（`chunk_count`, `top_score`, `source_uris`）
4. 結果を `log/analysis/medicine_kb_baseline_YYYYMMDD.json` に保存

**完了条件:** 20 問の before スコアが数値で記録されていること

---

### Step 2 — Phase 1 医薬品 KB データ品質（3–5 日・最優先）

1. **新規** [scripts/build_medicine_kb_documents.py](scripts/build_medicine_kb_documents.py)

| 出力 | ソース | 単位 |
|------|--------|------|
| `medicine/products/{slug}.md` | `otc_medicine_data.csv` | 1 品目 = 1 doc（**全 7,494 件**） |
| `medicine/interactions/{pair}.md` | `medicine_interactions.csv` | 成分ペア（約 82） |
| `medicine/side_effects/{ingredient}.md` | `medicine_side_effects.csv` | 成分単位 |
| `medicine/kanpo/{name}.md` | `kanpo_medicine.csv` | 漢方単位 |
| `medicine/efficacy/{slug}.md` | `summarized_efficacy_data.csv` | 製品 + 要約効能 |

2. 各 doc に **metadata.json**（Bedrock 制限: **1KB / 35 keys 以内**）
   - 必須: `domain=medicine`, `doc_type`
   - interactions: `ingredient_a`, `ingredient_b`, `risk_level`
   - products: `product_name`, `manufacturer`, `classification`
   - 長い効能全文は MD 本文のみ（metadata はフィルタキー）

3. **slug 規則:** `{product_name}-{manufacturer}` 正規化、重複時 suffix。衝突テスト必須

4. [sync-medicine-kb-to-s3.sh](scripts/sync-medicine-kb-to-s3.sh) 更新
   - 生成物 `medicine/` を sync
   - 生 CSV は `medicine/raw/` 退避 or exclude

5. re-ingest（データソース `0ZCBZWSQ7N`）→ 20 問 **再計測**

**完了条件:** 20 問で **80%+** が `score >= 0.5` かつ期待 prefix 一致

**触らない:** [physical_orchestrator.py](src/agents/physical_orchestrator.py)

---

### Step 3 — Phase 2 接続範囲拡大（3–4 日）

**Phase 1 完了前に 3-2（retrieve クエリ）だけ先にやらない**

#### 3-1. SSE ストリーム（最優先）

- [medicine_response_builder.py](src/core/medicine/medicine_response_builder.py) — `answer_prompt` 前に `augment_medicine_prompt_with_kb()`
- 非ストリーム経路と同一 KB コンテキストを unit test で確認

#### 3-2. retrieve クエリ強化

- [bedrock_kb_retrieve.py](src/services/bedrock_kb_retrieve.py) — `build_medicine_retrieval_query()` 拡張
- Comprehend `medications` + NLU 症状 + 併用薬名を合成

#### 3-3. Explanation 経路

- `generate_individual_usage_notes_with_gpt()` に KB
- `generate_explanation()` — **方式 A**（citation 追記のみ）

#### 3-4. LINE 対応

- **Medicine KB RAG:** Ask / Explanation 全経路で Web 同等
- **Comprehend:** Ask/Q&A と retrieve クエリ強化時のみ（NLU 推奨前は呼ばない）
- `is_web_session` 使用箇所を grep し、KB 経路は LINE 含める

#### 3-5. 安全フォールバック（Phase 6 並行）

- retrieve が `risk_level=高` の interaction chunk 時、LLM より [medicine_interactions.csv](data/medicine_interactions.csv) 直引き段落を優先

**完了条件:** 相互作用 5 問で Ask ログに KB URI。SSE 経路 unit test pass

---

### Step 4 — Phase 4 Concierge（2–3 日）

1. [write_changelog_digest.py](scripts/write_changelog_digest.py) → `content/changelog-digest.json` を S3 sync
2. [concierge_agent.py](src/agents/concierge_agent.py) — intent 別 retrieve クエリ
3. `augment_reference_with_kb` unit test + retrieve モック
4. UI「ナレッジベースの全文同期は現在準備中です」削除（ingestion 自動化完了後）
5. [concierge_technical_faq.yaml](tests/fixtures/concierge_technical_faq.yaml) 40 問 — KB ON 時も pass

---

### Step 5 — Phase 5 / 3 / 6（後続）

- **Phase 5:** CodePipeline post_build sync + ingestion 2 本（失敗 warn）
- **Phase 3:** [enrich_ingredients_pubchem.py](scripts/enrich_ingredients_pubchem.py) — Phase 1 後・同義語不足分のみ
- **Phase 6:** Guardrails、[concierge_output_sanitize.py](src/services/concierge_output_sanitize.py) Ask 適用検討

---

## 外部データ（Phase 3 以降）

| ソース | 用途 | 備考 |
|--------|------|------|
| PMDA 医薬品医療機器総合情報 | `otc_medicine_data.csv` 更新 | 公開情報・利用条件順守 |
| [PubChem PUG REST](https://pubchem.ncbi.nlm.nih.gov/docs/pug-rest) | 成分同義語 | 無料 API、レート制限 |
| [ingredient_dictionary.json](data/ingredient_dictionary.json) | 正規化 | 既存 |
| UMLS / RxNorm | 任意 | ライセンス申請要 |
| JAPIC / e-薬Link | 将来 | 有償・今回スコープ外 |

---

## エージェント vs ユーザー作業分担

### エージェントが実施

- Step 1–4 のコード・スクリプト・テスト・S3 sync・ingestion CLI
- `medicine_kb_eval.yaml` 20 問ドラフト作成と baseline 計測
- staging `/health/aws` 確認と [log/analysis/](log/analysis/) 記録
- 変更後 `test_bedrock_kb_retrieve.py` / `test_aws_features.py` 実行

### ユーザー側（必要時のみ）

| タイミング | 作業 |
|------------|------|
| Phase 0 後（任意） | 20 問 YAML の医学的内容レビュー（自動作成のため） |
| Phase 1 re-ingest 後 | 初回全量 ingestion 完了まで **15–30 分** 待機（7,494 MD）— 進捗は Bedrock コンソールで確認可 |
| Phase 5 前 | CodePipeline post_build に ingestion 追加するか最終 GO |
| GCP 移行 | Phase 5 ADR 読了後、本番 Bedrock 導入の GO/NO-GO |
| コミット・push | **ユーザー明示指示まで行わない** |

---

## 作業時の注意

1. Phase 1 完了前に Phase 2 retrieve 強化だけ先にやらない
2. 行番号は drift しやすい — 関数名で grep してから編集
3. metadata.json は 1KB 制限
4. [log/](log/) 配下の評価成果物はコミット対象
5. コミット・push はユーザー指示まで禁止

---

## 報告フォーマット（各 Phase 完了時）

```
Phase X 完了
- 変更ファイル: （リスト）
- 評価結果: 20問中 N 問が score>=0.5（before: M 問）
- 未解決: （あれば）
- 次: Phase Y
```

---

## 成功の定義（全体）

- Medicine retrieve: 20 問で **80%+** が `score >= 0.5` かつ期待 prefix
- AskAgent: 相互作用 5 問で KB URI がログに出る
- Concierge: 技術 40 問 contract **既存 pass 維持**
- staging `/health/aws`: 両 KB ID 表示、ingestion 24h 以内
- **推奨順位** golden case に **回帰なし**

---

## 必読参照

| 用途 | パス |
|------|------|
| KB 運用 | [docs/ops/AWS_BEDROCK_KB.md](docs/ops/AWS_BEDROCK_KB.md) |
| RAG コア | [src/services/bedrock_kb_retrieve.py](src/services/bedrock_kb_retrieve.py) |
| AskAgent | [src/core/medicine/medicine_response_builder.py](src/core/medicine/medicine_response_builder.py) |
| Explanation | [src/core/explanation_generator.py](src/core/explanation_generator.py) |
| Concierge | [src/agents/concierge_agent.py](src/agents/concierge_agent.py) |
| 設定 | [config/aws_features.py](config/aws_features.py) |
| 技術 FAQ 評価 | [tests/fixtures/concierge_technical_faq.yaml](tests/fixtures/concierge_technical_faq.yaml) |
