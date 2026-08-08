# Physical 症状ルーティング・E2E 検証 SSOT

**最終更新**: 2026-08-08  
**関連**: [`CHAT_PIPELINE_V2.md`](CHAT_PIPELINE_V2.md) · [`E2E_TARGETED_TEST_MAP.md`](E2E_TARGETED_TEST_MAP.md) · [`MEDICINE_QA_ROUTING.md`](MEDICINE_QA_ROUTING.md)

---

## 目的

ユーザー視点の **日常表現・短文・部位痛・皮膚症状** を、テスト個別ハックではなく **一般化された NLU 補正 + ルーティング + 候補 0 件 UX** で扱う。GPT 多ターン E2E で回帰を担保し、PR では変更領域に応じた **targeted テスト** のみ実行してコストを抑える。

---

## アーキテクチャ概要

```
ユーザー入力
  → triage（rule fast-path / LLM）
  → apply_explicit_symptom_triage_override（短文 Physical 救済）
  → rule_based NLU
  → refine_nlu_symptoms_from_context（原文ベース canonical 化）
  → CSV スコアリング（同義語展開含む）
  → 候補あり → sage_reco / 候補なし → physical_no_recommendation
```

| レイヤ | モジュール | 役割 |
|--------|-----------|------|
| Triage fast-path | `medicine_discovery_routing.try_rule_based_symptom_triage` | ≤80 文字・明示症状で LLM triage スキップ |
| Triage override | `apply_explicit_symptom_triage_override` | Concierge greeting 誤判定を Physical へ救済 |
| 明示症状信号 | `input_helpers.has_explicit_symptom_signal` | 皮膚系（蕁麻疹・かぶれ等）含む |
| NLU 補正 | `symptom_helpers.refine_nlu_symptoms_from_context` | 「炎症」→「耳の痛み」等 |
| 同義語 | `scoring_utils` symptom_synonyms | じんましん ↔ 蕁麻疹 ↔ 発疹 |
| 候補 0 件 | `chat_recommendation_flow._build_empty_recommendation_fallback` | kind=`physical_no_recommendation` |
| 文脈ガイダンス | `physical_no_reco_guidance.build_physical_no_reco_message` | 皮膚/耳鼻等の受診・追加質問 |

---

## NLU 補正（`refine_nlu_symptoms_from_context`）

**問題**: Hybrid NLU が「耳が痛い」→「炎症」、「蕁麻疹出た」→「発疹」のみ返し、CSV 効能（「じんましん」「耳痛」）と不一致で `no_candidates` になる。

**方針**: ユーザー原文のパターン（部位+痛み、皮膚キーワード）で canonical 症状名を **追加・差し替え**。LLM 追加呼び出しなし。

| 原文例 | NLU（修正前） | 補正後 |
|--------|--------------|--------|
| 耳が痛い | 炎症 | 耳の痛み |
| 蕁麻疹出た | 発疹 | 発疹 + **じんましん** |
| のどが痛い | （そのまま） | のどの痛み（必要時） |

汎用 NLU（炎症・不調）のみで原文から具体症状が取れた場合は **先頭を差し替え**。

---

## 候補 0 件 UX（`physical_no_recommendation`）

**問題**: `status=no_candidates` で `error=True` が立ち、sage_reco エラー表示になり route が `unknown` 扱いになっていた。

**修正**: `no_candidates` 検知時に即 `_build_empty_recommendation_fallback` を返す。

- `diagnosis.kind`: `physical_no_recommendation` → E2E / IntentRouter で **Physical** と判定
- 本文: `physical_no_reco_guidance` が症状カテゴリ別に受診・市販薬の可能性・追加質問を提示
- **追加 LLM なし**（レイテンシ・コスト優先）

---

## GPT E2E・Follow-up（2026-08-05〜08）

| モジュール | 用途 |
|-----------|------|
| `reco_followup_signals.py` | pivot / travel / anaphora / bot-echo 等の follow-up シグナル集約 |
| `conversation_followup_resolver.py` | ルール inconclusive 時のみ LLM（≤120 文字） |
| `e2e_gpt_user_sim.py` | 患者ロール GPT sim + 出力検証 |
| `medicine_qa_routing` / `medicine_response_builder` | travel / doping / allergen fast path |

**ペルソナ fixture**

| ファイル | 規模 | 用途 |
|---------|------|------|
| `v2_gpt_expanded_personas_30.yaml` | 30×4 | 月次ベースライン |
| `v2_gpt_diverse_personas_20.yaml` | 20×4 | 多様口調 |
| `v2_gpt_context_personas_10.yaml` | 10×4 | 文脈 follow-up |
| `v2_gpt_tier1_targeted.yaml` | 4×4 | PR targeted（低コスト） |
| `v2_tier1_short_symptom.yaml` | 3 | 短文 Physical rule triage |

---

## Tier1 レイテンシ（コスト兼ね合い）

| 施策 | 内容 |
|------|------|
| `try_rule_based_symptom_triage` | コールドスタート短文明示症状で stage1 LLM スキップ |
| focus_llm skip 拡大 | 既知 source では focus LLM を省略 |
| followup LLM | ルール優先、≤120 文字のみ |

**KPI**: end-to-end **p95 < 15s**（現状 YAML physical 10 で p95 ~24s — Tier2 継続）

---

## 検証結果（2026-08-08 ローカル）

| スコープ | 結果 | レポート suffix |
|---------|------|-----------------|
| Tier1 短文 YAML | **3/3** | `tier1-short-yaml-v3` |
| Physical YAML 10 | **10/10** | `tier1-physical10-v3` |
| GPT Tier1 targeted 4×4 | **4/4** | `tier1-gpt-v3` |
| GPT 30 diverse（先行） | **~30/30** | `expanded-v6-diverse30` |

```powershell
python scripts/local_v2_chat_test_runner.py --scenarios-path tests/fixtures/v2_tier1_short_symptom.yaml --report-suffix tier1-short-yaml-v3
python scripts/local_v2_chat_test_runner.py --categories physical --limit 10 --report-suffix tier1-physical10-v3
python scripts/local_v2_chat_test_runner.py --skip-yaml --use-gpt-user --personas-path tests/fixtures/v2_gpt_tier1_targeted.yaml --sessions 4 --turns-per-session 4 --report-suffix tier1-gpt-v3
```

---

## CI

`.github/workflows/chat-pipeline-v2-pr.yml` に unit 追加:

- `test_reco_followup_signals`
- `test_conversation_followup_resolver`
- `test_e2e_gpt_user_sim`

PR では [`E2E_TARGETED_TEST_MAP.md`](E2E_TARGETED_TEST_MAP.md) に従い **GPT 30 フルは月次のみ**。

---

## RAG / Concierge 参照

- パイプライン FAQ: [`docs/concierge/rag/technical-pipeline-rag.md`](../concierge/rag/technical-pipeline-rag.md)（症状補正・no_candidates 節）
- 技術 FAQ: [`docs/concierge/technical/12-technical-faq-rag.md`](../concierge/technical/12-technical-faq-rag.md)
- Local RAG index: `config/concierge_rag_sources.CONCIERGE_DEV_DOCS` に本 doc を登録
