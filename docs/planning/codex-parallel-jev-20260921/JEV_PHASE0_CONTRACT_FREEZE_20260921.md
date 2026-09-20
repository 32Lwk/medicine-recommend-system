# Jev Phase 0 契約凍結（2026-09-21）

- 作成日: 2026-09-21
- 位置づけ: Phase 1 local shadow 実装前の固定契約サマリ
- 正本: `JEV_PARALLEL_SYNTHESIS_20260921.md`、同期先: `docs/planning/JEV_IMPLEMENTATION_TEST_PLAN_2026-09-21.md` §8–§9

## 凍結チェックリスト

| 領域 | 凍結内容 |
| --- | --- |
| Mapping | Choice/Noul → shadow DTO。`primary_confidence` / `selected_sub_confidence` / Noul を分離。未知 enum・欠損・範囲外 = invalid。accuracy は **primary + 必須 sub-route の joint** |
| Adapter | **`jev:minimal` のみ**。`with_baseline_triage` 廃止。payload に **`baseline_triage_hint` を送らない**（contract test） |
| State allowlist | `channel`（web/line）、sanitized `user_input`、直近 **5 turn**（role/content）、`last_primary_route` / `last_sub_route`、`last_recommended_medicines`（商品名のみ最大 3）、既存の `active_symptoms` / `medicine_qa_focus`（あれば）、固定短い `app_context` |
| State 禁止 | 識別子・不要 PII・user attributes・RAG/生成 prompt 全文・生 triage category・`baseline_triage_hint`・5 turn 超履歴 |
| Flags（default OFF） | `JEV_ENABLED=false`、`JEV_INTENT_ROUTER_SHADOW=false`、`JEV_INTENT_ROUTER_PRIMARY=false`（**Phase 1 は PRIMARY を無視し実行 route 不変**） |
| Runtime | `JEV_MODEL=jev-latest`（shadow）、`JEV_TIMEOUT_SEC=3.5`、retry **429/5xx のみ最大 1**、floor 0.70 / high 0.85 は暫定観測 |
| Secret | **`JEV_API_KEY` のみ**。Phase 1 本番コードに `TYPESAFE_API_KEY` fallback **なし** |
| Safety | Emergency / Security / medical_examination は **Jev 単独確定禁止**。既存陽性を Jev 陰性で **解除しない** |
| SessionOps | 現行 fast-path 維持。**Jev primary 対象外** |
| Phase 1 scope | local shadow のみ。`resolve_route()` で legacy 確定後に shadow 1 回。常に同一 legacy を返す |
| Observability | 専用 JSONL **`log/jev_intent_router_shadow.jsonl`**。legacy / Jev / executed、usage、latency、failure reason。raw text / secret / 生 ID 禁止 |
| Cost metrics | 分離: **OpenAI IntentRouter saved** vs **total classification cost including Jev** |
| Fixture | 既存 10 は **pilot**。拡張器: `tests/fixtures/jev_intent_router_safety_expanded.yaml` |
| Pilot 格下げ | 10 シナリオ 100% は smoke のみ。**Gate B/C の十分条件にしない** |

## Gate B 前の open items（医療安全レビュー）

| 項目 | 状態 | 備考 |
| --- | --- | --- |
| expanded fixture ラベル初稿 | 未完 | 実装者が作成 |
| Emergency ± / hypothetical / quoted | レビュー待ち | combined FN=0 必須 |
| Security prompt injection / hard negative | レビュー待ち | 同上 |
| medical_examination / prescription / controlled | レビュー待ち | 独立採点 |
| Store+symptom / SessionOps+high-risk / Counseling+crisis | レビュー待ち | multi-intent |
| follow-up state none/correct/stale/conflicting | レビュー待ち | cold-start 悪化 0 |
| **医療安全レビュー承認** | **Gate B 必須** | 未承認のまま dev shadow しない |

## 参照

- Synthesis: `JEV_PARALLEL_SYNTHESIS_20260921.md`
- Test Plan: `../../JEV_IMPLEMENTATION_TEST_PLAN_2026-09-21.md`
- Progress: `JEV_PROGRESS_AND_NEXT_PLAN_20260921.md`
