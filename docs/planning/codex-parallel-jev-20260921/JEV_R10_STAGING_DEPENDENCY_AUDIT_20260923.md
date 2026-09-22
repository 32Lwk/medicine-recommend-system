# JEV R10 Staging / Dependency Audit

**Date**: 2026-09-23  
**Commit/push**: 未実行 / 禁止

## Verdict

| Bucket | Contents | Separable? |
| --- | --- | --- |
| A boundary | gate / jev_router / eligibility | 依存統合の一部 |
| B D2 domain | policy_*, snapshot, pre_route, detector_text, sleep_med | 依存統合 |
| C pipeline + **security bridge** | chat_post_pipeline, security_terminal_bridge, follow_ups, orch, symptom | 依存統合（CにH-SEC含む） |
| D R7 safety | embedded in B/C | 分離不可 |
| E evaluator | eval scripts + tests | **Yes** |
| F mock hygiene | test_jev_router | **Yes** |
| G R10 reliability/telemetry | policy_enforce FB-REASON, policy_d2_pipeline M-OBS | B/Cと密結合 → **依存統合寄り** |
| H tests/docs | test_r10_*, R10 docs, runbook | **Yes**（明示path） |

**A–D (+G production)** = 依存統合候補。独立微小commitと主張しない。

## R10 dry-run

1. `git add -- tests/dialogue/routing/test_r10_*.py`（3 files）
2. pytest → 11 passed
3. `git restore --staged -- …`
4. cached empty

確認:

- H04金ラベル変更なし（fixture不変）
- default ON変更なし（`_flag(..., False)` 維持）
- logs/tmp を候補に混ぜず
- 候補外 WT（crisis_detection / medical_examination_request 等）は **別監査** — 広域 `git add` 禁止

## DAG

```
B domain → C wiring (+ security bridge) → D R7
E / F / H tests ─ independent of runtime ON
G telemetry/fb ─ edits B modules (policy_enforce, policy_d2_pipeline)
```
