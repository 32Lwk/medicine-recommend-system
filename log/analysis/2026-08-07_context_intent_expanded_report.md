# 文脈・意図 E2E 拡張テスト統合レポート (2026-08-07)

## エグゼクティブサマリ

| 実行 | シナリオ/セッション | ターン | 自動合格 | 備考 |
|------|---------------------|--------|----------|------|
| 拡張 YAML（初回） | 29 | 60 | **29/29** | 日常表現・方言・省略・複数比較 |
| GPT 医薬品スレッド 4 ペルソナ（初回） | 4 | 32 | **4/4** | 自動合格だが品質課題あり（下記） |
| 拡張 YAML（修正後 v2） | 29 | 60 | **27/29** | store pivot 修正済み（v3 PASS） |
| 拡張 YAML pivot 再検 | 1 | 2 | 要確認 | `exp-concierge-pivot-01` — dispatcher 修正中 |
| GPT ペルソナ（初回・32T） | 4 | 32 | **4/4** | 自動合格（品質課題は別途修正） |
| GPT ペルソナ（v2・中断） | 4 | 16 | 2/4 | サーバー再起動で中断 |

**ルーティング（意図読み取り）**: 拡張 YAML 29/29、GPT 4/4 で自動合格。医薬品スレッド継続の誤ルーティング（`concierge_greeting` 奪い）は初回再テスト 3/3 修正済み。

**応答品質（GPT 長尺で顕在化）**: 自動合格でも以下の問題が確認されたため、一般化修正を実施。

---

## テスト構成

### 拡張 YAML (`v2_context_intent_expanded.yaml`)

- **29 シナリオ / 60 ターン**
- カテゴリ: `medicine_thread_casual`(16), `medicine_thread`(5), `physical_context`(3), 他
- カバー: 関西弁、スラング、英語混じり、タイポ、高齢者曖昧表現、複数推奨比較、ワーファリン併用、店舗 pivots 等

### GPT シミュレーション (`v2_gpt_medicine_thread_personas.yaml`)

- **4 ペルソナ × 8 ターン = 32 ターン**
- `medicine-thread-loxonin-casual` / `multi-compare` / `elderly-vague` / `young-slang`
- レポート: `log/analysis/2026-08-07_local_v2_chat_test_gpt-medicine-0807.md`

---

## GPT テストで見つかった品質課題（自動合格を超えたレビュー）

| 問題 | 例 | 根本原因 | 修正 |
|------|-----|----------|------|
| 文脈喪失 → 別症状推奨 | loxonin-casual T3: のどスプレー・ベンザブロック | 「痛み」含有で新規症状と誤判定 | `_is_medicine_discussion_continuation` |
| 比較質問の繰り返し | multi-compare T3–8: イブプロフェン系のみ | 成分クエリで CSV ヒットが単一系統に置換 | `expand_medicines_for_comparison` |
| JSON 生漏れ | loxonin-casual T6–8: `{ "answer": ...` | LLM JSON 全体が answer に残存 | `sanitize_medicine_ask_output` で unwrap |
| 誤 Emergency | young-slang T6: アレルギー説明で 119 案内 | 「呼吸困難」キーワード gate | 仮定話法 side-effect ガード |

---

## 実装した一般化修正（テスト合わせではない）

| ファイル | 内容 |
|---------|------|
| `medicine_thread_context.py` | 医薬品スレッド内の感想・用法確認（「痛みが和らぐ」等）を継続判定 |
| `medicine_qa_comparison_quality.py` | 比較時に成分系統代表をセッション文脈とマージ |
| `medicine_response_builder.py` | 比較 intent 時のブランド上書き抑止 + expand 呼び出し |
| `concierge_output_sanitize.py` | JSON blob answer の unwrap |
| `gate.py` | 副作用・アレルギー説明の仮定話法で Emergency 抑止 |

### Local RAG / 複数医薬品

- `resolve_session_recommended_medicines()`: sage_qa 等から CSV 解決し **最大 5 品目** を Q&A/RAG 用に復元（前セッション実装）
- `expand_medicines_for_comparison()`: 比較質問で **イブプロフェン vs アセトアミノフェン** 等、異なる成分系統を網羅
- 比較 Q&A は `_try_fast_comparison_qa_response` で **ルールベース + Local CSV メタ** を優先（重い JSON LLM を省略しレイテンシ改善）

---

## レイテンシ KPI（初回計測）

| 実行 | p50 E2E | p95 E2E | 目標 p95 |
|------|---------|---------|----------|
| 拡張 YAML 60T | 10.3s | **23.9s** | < 5s ❌ |
| GPT 32T | 10.6s | **18.4s** | < 5s ❌ |

ボトルネック: `medicine_qa/focus_llm`, `llm_triage.stage1`, `medicine_response_builder.chat_context`（比較 fast-path 適用で chat_context 呼び出し削減を継続）

---

## ユニットテスト

```
tests/services/test_medicine_thread_context.py  — 7 passed
tests/routing/test_medicine_qa_comparison_broad.py — 53 passed
```

---

## レポートファイル一覧

| ファイル | 内容 |
|---------|------|
| `2026-08-07_local_v2_chat_test_expanded-0807.md` | 拡張 YAML 完全トランスクリプト |
| `2026-08-07_local_v2_simulation_eval_expanded-0807.md` | 拡張 YAML 意図評価 |
| `2026-08-07_local_v2_chat_test_gpt-medicine-0807.md` | GPT ペルソナ 完全トランスクリプト |
| `2026-08-07_local_v2_simulation_eval_gpt-medicine-0807.md` | GPT 意図評価 |
| `2026-08-07_context_intent_e2e_report.md` | 初回 12 シナリオ + 再テスト |

---

## 方針確認のための質問（未回答）

1. **Local RAG の適用範囲**: 全 medicine_qa に常時 KB 注入 vs フォローアップ/曖昧入力時のみ（レイテンシ trade-off）
2. **複数推奨時の網羅性**: ユーザー言及品目のみ vs 推奨全件（3–5 品）を比較回答に含めるか
3. **GPT E2E 予算**: 許容 API コスト / ターン数 / p95 レイテンシ目標（現状 18–24s p95）
4. **副作用回答の表記**: ブランド名（ロキソニン）優先 vs 成分名（ロキソプロフェン）優先

---

## Admin 確認

[http://127.0.0.1:5000/admin](http://127.0.0.1:5000/admin) → 「v2テストのみ」ON  
session_ids: `2026-08-07_local_v2_session_ids_expanded-0807.json` / `..._gpt-medicine-0807.json`
