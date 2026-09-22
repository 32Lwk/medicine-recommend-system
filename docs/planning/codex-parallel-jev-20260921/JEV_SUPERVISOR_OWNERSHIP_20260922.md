# Jev 並列エージェント所有権表（Supervisor Round 0 → Autonomous PDCA）

- 作成: 2026-09-22
- 更新: 2026-09-22（自律PDCA開始・Worker A/E/F 再起動）
- Supervisor: autonomous-pdca-20260922
- PDCA状態: `JEV_AUTONOMOUS_PDCA_STATE.json`
- 作業開始時点の正式判定（ユーザー固定・変更不可）:

| 項目 | 判定 |
| --- | --- |
| Phase 1 local shadowコード | Passed |
| Gate A-code | Passed |
| Gate A-accuracy | **Not Passed** |
| Gate B / dev shadow有効化 | Hard No-Go |
| primary canary | Hard No-Go |
| staging / production | Hard No-Go |
| Focus本配線 | No-Go（scaffold 維持可） |

**禁止語:** 条件付きPassed / ほぼPassed / 実質合格  
**許可語:** Passed / Not Passed / Hard No-Go のみ

旧最終レポートの「A-accuracy: 条件付き Passed」は **棄却**。正本は本表とユーザー指示。

---

## ファイル所有権

| file | primary owner | read-only reviewers | merge order | expected output |
| --- | --- | --- | --- | --- |
| `src/services/jev_eligibility.py` | **Supervisor** (+ A/C read) | E, F | 1a | eligibility v1 共用判定 |
| `tests/services/test_jev_eligibility.py` | **Supervisor** / A | E | 1a | 契約 unit |
| `tests/scripts/test_eval_jev_intent_router_10.py` | **A** | E | 1 | 上記の unit |
| `src/services/jev_decisions.py` | **B** Safety/Decision | E, F | 2 | joint(primary+sub+safety)、alias、fail-safe、Emergency優先、invalid時risk保持 |
| `tests/services/test_jev_decisions.py` | **B** | E, F | 2 | 契約テスト |
| `tests/fixtures/jev_intent_router_safety_expanded.yaml` | **B** schemaのみ / **F** 臨床ラベル | E | 2b | schema整合。**ラベル変更はF承認なし禁止** |
| `src/services/jev_client.py` | **C** Runtime | E | 3 | reuse/timeout/retry/fail-open/secret非出力 |
| `src/dialogue/routing/jev_router.py` | **C** | E | 3 | bounded executor、queue、shutdown、corr lifecycle |
| `config/llm_flags.py` | **C** | E, G | 3 | default OFF 維持。PRIMARY無視維持 |
| `config/routing_config.py` | **C** | E | 3 | timeout/retry getters |
| `src/services/jev_metrics.py` | **D** Observability | E, G | 4 | event完全性、disagreement、cost分離、PII検査 |
| `log/jev_intent_router_shadow.jsonl` schema docs | **D** | G | 4 | schema文書 |
| `docs/planning/codex-parallel-jev-20260921/*` Gate/正本 | **G** Docs + Supervisor | E | 5 | 判定語統一・古い数値検出 |
| `src/dialogue/routing/router.py` | **Supervisor only** | E | last | 共有変更は提案→Supervisor統合 |
| `src/dialogue/dispatcher.py` | **Supervisor only** | E | last | 同上 |
| `src/handlers/chat/chat_post_pipeline.py` | **Supervisor only** | E | last | 同上 |

### 競合ルール

1. 同一 production ファイルを複数エージェントが同時編集しない。
2. 共有ファイル変更は提案のみ → Supervisor が所有者へ依頼 → Supervisor 統合。
3. 他エージェント変更の reset / checkout / 上書き禁止。
4. 既存未追跡ファイル（`tmp_*`, `..bfg-report/` 等）は削除・移動・commit対象化禁止。
5. fixture の医療ラベル変更は Agent F レビューなしで禁止。不合格を閾値・ラベル改変で消すな。

---

## Round 0 仮説（Supervisor）

| ID | 仮説 | 検証方法 |
| --- | --- | --- |
| H1 | 現行 eval は current全件→Jev全件で **方法論違反** | コード監査（確認済） |
| H2 | request-level bootstrap のみで scenario cluster 未実装 → CIが楽観的 | Agent A |
| H3 | joint に `required_safety_action` が未接続 | Agent A+B |
| H4 | P95/CI 未達は再現する（033321の Hard 事実） | live repeat≥10 |
| H5 | 医療ラベルは `pharmacist_reviewed_draft` のまま → Gate B Hard No-Go 不変 | Agent F |

---

## 今回の完了条件

```text
Gate A-accuracy: Passed
```
または
```text
Gate A-accuracy: Not Passed
未達項目:
根拠:
次の改善:
```

速度・コスト改善だけでは Go にしない。Critical/High 未解決が1件あれば次ゲート Hard No-Go。

## 現行証跡ポインタ（2026-09-22）

- Gate A-accuracy: **Not Passed** — `JEV_GATE_A_ACCURACY_VERDICT_20260922.md`
- live: `log/analysis/jev_intent_router_eval_10_20260922_012129.{json,md}`（**実測**）
- 文書監査: `JEV_DOCS_AUDIT_AGENT_G_20260922.md`
