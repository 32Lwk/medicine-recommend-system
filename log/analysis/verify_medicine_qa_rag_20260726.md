# Medicine QA / Local RAG 検証レポート

## Summary

| 項目 | 値 |
|------|-----|
| **判定** | **GO**（warnings あり） |
| 実施日時 | 2026-07-26 11:11 JST 頃 |
| ブランチ | `main` |
| commit | `20db730` |
| `build/medicine/` | OK |
| Python | 3.12.13 (`.venv`) |
| `MEDICINE_RAG_PROVIDER` | local（検証時明示設定） |
| `CONCIERGE_RAG_PROVIDER` | local |
| `LOCAL_RAG_CONTEXT_LLM` | off |
| `OPENAI_API_KEY` | set（`.env` 経由、LLM stress 実行済） |

---

## Layer 結果

| Layer | 結果 | 詳細 |
|-------|------|------|
| 1 単体 | **pass** | 39/39 |
| 2a 公式 fixture | **100%** | raw 20/20、runtime 20/20、interaction **5/5** |
| 2b paraphrase | **100%** | 19/19 |
| 2c diverse | **100%** | 52/52（context 10/10 含む） |
| 2d LLM stress | **94.1%** | 64/68（llm_stress サブセット 12/16） |
| 3 Medicine QA 配線 | **5/5** | E2E script 10/10 も pass |
| 4 E2E retrieve | **100%** | 5/5 |
| 4 E2E HTTP | **skipped** | `:5000` server not ready |
| 5 benchmark | **pass** | P95=286ms（medicine P95=124ms） |
| 6 bedrock compare | **skipped** | AWS credentials 未設定 |

---

## Layer 2 — style breakdown（2c）

| style | pass | total | pct |
|-------|------|-------|-----|
| local_rag_paraphrase_eval | 19 | 19 | 100% |
| polite | 5 | 5 | 100% |
| dialect | 4 | 4 | 100% |
| english_mix | 5 | 5 | 100% |
| terse | 3 | 3 | 100% |
| verbose | 3 | 3 | 100% |
| question_form | 3 | 3 | 100% |
| **context** | **10** | **10** | **100%** |

### dialect / english_mix 個別

| スイート | pass | total | pct | 閾値 |
|---------|------|-------|-----|------|
| dialect | 4 | 4 | 100% | ≥75% |
| english_mix | 5 | 5 | 100% | ≥75% |

---

## Layer 2d — LLM stress breakdown

| style | pass | total |
|-------|------|-------|
| 敬語 | 6 | 8 |
| 関西弁 | 6 | 8 |
| llm_stress suite | 12 | 16 |

全体 pass_pct **94.1%**（閾値 ≥85% を満たす）。

---

## Layer 3 — Medicine QA 配線（最重要）

### 3a `augment_medicine_prompt_with_kb`（5 シナリオ）

| ID | KB block | URI prefix | retrieval_query 要点 |
|----|----------|------------|------------------------|
| ix-1 | ✓ | `medicine/interactions/` | ロキソニンとワーファリン併用大丈夫？ |
| se-1 | ✓ | `medicine/side_effects/` | 推奨医薬品: ロキソニン |
| us-1 | ✓ | `medicine/products/` | 推奨医薬品: カロナールA |
| age-1 | ✓ | `medicine/topics/` | 小学2年 風邪薬 |
| ctx-1 | ✓ | `medicine/interactions/` | `会話文脈: ワーファリン, ロキソプロフェン...` |

**結果: 5/5** — local provider でも KB ブロック（`医薬品ナレッジベース参照`）が非空で注入されることを確認。

### 3b 会話履歴の伝播

| 経路 | `conversation_history` 伝播 |
|------|----------------------------|
| `retrieve_medicine_context` | ✓ `build_medicine_retrieval_query(..., conversation_history=...)` |
| `medicine_response_builder.py` | ✓ `augment_medicine_prompt_with_kb(..., conversation_history=...)` ×2 |
| `explanation_generator._kb_citation_for_explanation` | △ `retrieve_medicine_context` 呼び出しに **history 未渡し**（advisory） |
| `medicine_side_effect_handlers.py` | △ history 未渡し（単発副作用クエリ想定） |

context session eval **10/10 pass**。ctx-1 で `retrieval_query` に `会話文脈:` と prior turn 薬名（ワーファリン / ロキソプロフェン）が含まれることを確認。

---

## Layer 5 — 性能・コスト（advisory）

### benchmark (`verify_benchmark.json`)

| メトリクス | 値 | 閾値 | 判定 |
|-----------|-----|------|------|
| 全体 P50 | 82ms | router <400ms | ✓ |
| 全体 P95 | 286ms | <800ms | ✓ |
| medicine P95 | 124ms | <800ms | ✓ |
| concierge P95 | 308ms | — | — |

### cost report（7日）

- embed API calls: 44、推定コスト $0
- retrieve samples: 1408、P50 1.68ms（ログ集計）

---

## FAIL 詳細（LLM stress のみ — 固定 eval は全 pass）

| id | query（要約） | expected | actual | 推定原因 |
|----|--------------|----------|--------|----------|
| llm-ix-colloquial-loxo-warfarin-2-0 | 血液をサラサラにする薬＋ロキソプロフェン（敬語） | interaction | usage（product hit） | 敬語「よろしいでしょうか」が age/usage 系に誤分類、interaction 意図が弱い |
| llm-se-colloquial-sleepy-1 | この痛み止め…めっちゃ眠たくなるわ（関西弁） | side_effect | doping/ix 誤ルート | 指示代名詞＋関西弁で substance 抽出失敗 |
| llm-se-colloquial-stomach-0 | イブプロフェンでお腹がきつく（敬語） | side_effect | doping/ix | 長い敬語文で category 空 → fallback 誤ヒット |
| llm-se-colloquial-stomach-1 | イブプロフェン飲んでお腹張った（関西弁） | side_effect | interaction | 「一緒に」系パターン誤発火の可能性 |

固定 fixture / paraphrase / diverse / context は **全件 pass**。LLM 生成バリアントのみ 4 件 fail（ルール限界、advisory）。

---

## Warnings（advisory）

1. **LLM stress 4/68 fail** — 全体 94.1% で GO 閾値（≥85%）は満たすが、敬語・関西弁の LLM 言い換えで side_effect / interaction 分類が不安定。
2. **Bedrock 比較未実施** — `Unable to locate credentials`。local vs bedrock regression は評価不能。
3. **HTTP E2E skipped** — `http://127.0.0.1:5000/` が eval 時点で not ready（retrieve tier は 100%）。
4. **Comprehend Medical 未使用** — AWS credentials なし。GCP ルールベース NER で代替（eval 時 `use_comprehend=False` も使用）。
5. **Redis 未接続** — `No module named 'redis'`。retrieve cache 無効（性能への影響は benchmark 上軽微）。
6. **explanation_generator** — KB citation 取得時に `conversation_history` 未伝播（マルチターン Explanation は弱い可能性）。

---

## 結論

### 本番投入可否

**GO（local RAG / Medicine QA 配線）**

厳格 NO-GO 条件はいずれも該当なし:

- Layer 3a: **5/5** ✓
- 公式 fixture raw: **100%**（≥95%）✓
- interaction: **5/5** ✓
- 単体テスト: **全 pass** ✓

### 残課題（優先度付き）

| 優先度 | 課題 | 備考 |
|--------|------|------|
| P2 | LLM stress 敬語 side_effect / interaction 分類 | 固定 eval は pass。ルール改善 or LLM category fallback 検討 |
| P2 | Bedrock 回帰比較 | AWS 環境で `eval_medicine_kb.py --provider bedrock` + `compare_rag_eval.py` |
| P3 | HTTP E2E | app 起動後 `--with-http` で advisory 確認 |
| P3 | explanation_generator history 伝播 | マルチターン Explanation KB citation 強化 |
| P3 | Redis cache 本番有効化 | レイテンシ・コスト最適化 |

---

## 成果物一覧

| ファイル | 内容 |
|---------|------|
| `log/analysis/verify_medicine_kb_local.json` | 2a 公式 fixture |
| `log/analysis/verify_paraphrase.json` | 2b |
| `log/analysis/verify_diverse.json` | 2c |
| `log/analysis/verify_llm_stress.json` | 2d |
| `log/analysis/verify_medicine_qa_e2e.json` | Layer 3 E2E（10 scenarios） |
| `log/analysis/verify_e2e_retrieve.json` | Layer 4 retrieve |
| `log/analysis/verify_benchmark.json` | Layer 5 benchmark |
| `log/analysis/verify_medicine_kb_bedrock.json` | Layer 6（credentials 不足で 0% — 参考） |
| `log/analysis/verify_layer1_pytest.txt` | pytest ログ |
