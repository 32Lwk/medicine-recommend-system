# Jev Phase 0 契約凍結（2026-09-21）

- 作成日: 2026-09-21
- 最終更新: 2026-09-22（Agent G: A-accuracy live 実行済だが **Not Passed** に同期）
- 位置づけ: Phase 1 local shadow の固定契約サマリ（実装前凍結 → 実装後も契約は不変、配線状態のみ更新）
- 正本: `JEV_PARALLEL_SYNTHESIS_20260921.md`
- 同期: `docs/planning/JEV_IMPLEMENTATION_TEST_PLAN_2026-09-21.md` §8–§9、`JEV_PHASE1_LOCAL_SHADOW_SUPERVISOR_REPORT_20260921.md`

## 実装ステータス（契約とは別）

| 項目 | 状態 |
| --- | --- |
| Phase 1 local shadow コード | **実装済**（Gate A-code Passed） |
| `recent_turns` + `recent_context` alias | **実装済** |
| `deterministic_signals` → shadow worker | **実装済**（実行 route は不変） |
| `_jev_shadow_correlation_id` clear | **実装済**（schedule 失敗時 / notify 後） |
| Gate A-accuracy（live 再評価） | **Not Passed**（live `012129` 実行済・CI/コスト未達。旧「未完」表記は廃止） |
| Gate B（dev shadow） | **Hard No-Go** |

## 凍結チェックリスト

| 領域 | 凍結内容 |
| --- | --- |
| Mapping | Choice/Noul → shadow DTO。`primary_confidence` / `selected_sub_confidence` / Noul 分離。未知 enum・欠損・範囲外 = invalid。accuracy は **primary + 必須 sub-route の joint** |
| Adapter | **`jev:minimal` のみ**。`with_baseline_triage` 廃止。payload に **`baseline_triage_hint` を送らない**（contract test） |
| State allowlist | `channel`（web/line）、sanitized `user_input`、履歴キーは契約名 **`recent_turns`**（直近 5 turn role/content）。本番 builder は pilot eval 互換で **`recent_context` に同一 list を alias**。`last_primary_route` / `last_sub_route`、`last_recommended_medicines`（商品名のみ最大 3）、既存の `active_symptoms` / `medicine_qa_focus`（あれば）、固定短い `app_context` |
| State 禁止 | 識別子・不要 PII・user attributes・RAG/生成 prompt 全文・生 triage category・`baseline_triage_hint`・5 turn 超履歴 |
| Shadow 比較用（非 payload） | `deterministic_signals`（legacy/triage 由来の高リスク陽性）。**Jev HTTP state には載せない**。shadow DTO 比較・override 観測用 |
| Flags（default OFF） | `JEV_ENABLED=false`、`JEV_INTENT_ROUTER_SHADOW=false`、`JEV_INTENT_ROUTER_PRIMARY=false`（**Phase 1 は PRIMARY を無視し実行 route 不変**） |
| Runtime | `JEV_MODEL=jev-latest`（shadow）、`JEV_TIMEOUT_SEC=3.5`、retry **429/5xx のみ最大 1**、floor 0.70 / high 0.85 は暫定観測 |
| Secret | **`JEV_API_KEY` のみ**。Phase 1 本番コードに `TYPESAFE_API_KEY` fallback **なし** |
| Safety | Emergency / Security / medical_examination は **Jev 単独確定禁止**。既存陽性を Jev 陰性で **解除しない** |
| SessionOps | 現行 fast-path 維持。**Jev primary 対象外** |
| Phase 1 scope | local shadow のみ。`resolve_route()` で legacy 確定後に shadow 1 回。常に同一 legacy を返す |
| Observability | 専用 JSONL **`log/jev_intent_router_shadow.jsonl`**。legacy / Jev / executed、usage、latency、failure reason。raw text / secret / 生 ID 禁止。corr は schedule 失敗時・notify 後に clear |
| Cost metrics | 分離: **OpenAI IntentRouter saved** vs **total classification cost including Jev**（Phase 1 は saved 実測未完で可） |
| Fixture | 既存 10 は **pilot**。拡張器: `tests/fixtures/jev_intent_router_safety_expanded.yaml`（**draft — CI hard-fail 禁止**） |
| Pilot 格下げ | 10 シナリオ 100% は smoke のみ。**Gate A-accuracy クローズ条件でも Gate B/C 入場条件でもない** |

## Gate 辛口定義（要約）

| ゲート | Pass の意味 | これだけでは足りないこと |
| --- | --- | --- |
| Gate A-code | 構造・配線・unit・本線不変 | 精度・医療安全・dev 運用 |
| Gate A-accuracy | production 契約での live 再評価完了 | 医療ラベル承認・dev shadow |
| Gate B | 医療レビュー承認 + A-accuracy + 運用準備後の **dev shadow 開始可否** | primary / staging |
| Gate C | 150 eligible・disagreement・FN 監査後の **primary 設計開始可否** | 本番 |

## Gate B 前の open items（医療安全レビュー）

| 項目 | 状態 | 備考 |
| --- | --- | --- |
| expanded fixture ラベル初稿 | 器あり・draft | 実装者初稿。**承認なしで Gate B 不可** |
| Emergency ± / hypothetical / quoted | レビュー待ち | combined FN=0 必須 |
| Security prompt injection / hard negative | レビュー待ち | 同上 |
| medical_examination / prescription / controlled | レビュー待ち | 独立採点 |
| Store+symptom / SessionOps+high-risk / Counseling+crisis | レビュー待ち | multi-intent |
| follow-up state none/correct/stale/conflicting | レビュー待ち | cold-start 悪化 0 |
| live 再評価（A-accuracy） | **Not Passed** | 証跡 `012129` / `JEV_GATE_A_ACCURACY_VERDICT_20260922.md`。Gate B 入場不可 |
| `medicine_qa_focus` router 注入 | 未完（任意だが観測品質に影響） | session 既存値のみ |
| **医療安全レビュー承認** | **Gate B 必須** | 未承認のまま dev shadow しない |

## 参照

- Synthesis: `JEV_PARALLEL_SYNTHESIS_20260921.md`
- Test Plan: `../../JEV_IMPLEMENTATION_TEST_PLAN_2026-09-21.md`
- Supervisor: `JEV_PHASE1_LOCAL_SHADOW_SUPERVISOR_REPORT_20260921.md`
- Progress: `JEV_PROGRESS_AND_NEXT_PLAN_20260921.md`
