# JEV R7 — D2 Safety Blocker Repair Supervisor Report

**Date**: 2026-09-23  
**Cycle**: R7 Emergency Correction + Follow-up  
**Commit/push/live**: **禁止・未実行**

## Label correction（正式・変更なし）

| Label | Status |
| --- | --- |
| Jev導入基盤実装完了候補 | **撤回** |
| Implementation state | **Units A–F implemented, Safety Blocked** |
| AI多重医療監修済み候補 | **Reject / Hold** |
| D2 ON 導入 | **禁止** |
| `POLICY_ENFORCEMENT_D2` default | **OFF 維持** |
| product safety / Gate A-accuracy / Gate B | **未変更・未合格 / Not Passed / Hard No-Go** |

## AI review panel（R7）

| Reviewer | Doc | Verdict |
| --- | --- | --- |
| Primary | `JEV_R7_MEDICAL_PRIMARY_20260923.md` | 4項 Accept・ラベル付与主張 |
| Adversarial | `JEV_R7_MEDICAL_ADVERSARIAL_20260923.md` | **Reject**（R7-C01）；detector_text→emergency follow-up 後 |
| Second opinion | `JEV_R7_MEDICAL_SECOND_OPINION_20260923.md` | Conditional；**外部未取得** |
| Amendment | `JEV_R7_MEDICAL_REVIEW_AMENDMENT_SLEEP_CRISIS_20260923.md` | ambiguous sleep 一律危機窓口は **不採用** |

**Supervisor 採用（安全側）**: 公式 **Reject / Hold**。製品安全合格ではない。D2 ON 禁止。

## Criticals addressed

### C1 — crisis/policy × SessionOps pure=True
**Fix**: detector comparison view；`evasion_fail_closed`；D2 ON 時 `detector_text` → `handle_emergency_if_detected`；safety full も detector_text。  
**Tests**: `test_r7_c01_pipeline_integration.py`（full `run_chat_post_pipeline`）。

### C2 — rollback + false SF-E1-NM
**Fix**: `CheckpointEntry`；NM disabled。  
**Tests**: `test_r7_c2_rollback_integration.py`（empty session / unknown / rollback fail）。

### Ambiguous sleep × crisis separation（follow-up）
- `_AMBIGUOUS_SLEEP_BOUNDARY` からいのちの電話 **削除**
- 危機窓口は crisis/emergency/overdose·self-harm 陽性時のみ（既存 Emergency 経路）
- sleep+self-harm キューを pre_route で emergency 化（H04 非変更）

## measured

```
pytest tests/dialogue/routing/ --ignore=tests/dialogue/routing/test_jev_router.py
→ 181 passed  (2026-09-23 R7 follow-up re-run)
```

（注: 以前の報告の 165/167 passed はそれ以前の測定時点。）

### Code fingerprint（commit 未作成）

| SHA256[:16] | File |
| --- | --- |
| `52f815b663906554` | `src/dialogue/routing/policy_adapters.py` |
| `21c981684489fb6d` | `src/dialogue/routing/pre_route_signals.py` |
| `ed748a516b4af775` | `src/dialogue/routing/policy_enforce.py` |
| `0a56240da102870b` | `src/dialogue/routing/detector_text_view.py` |
| `c7ead8f2edb1c182` | `src/dialogue/routing/turn_signal_snapshot.py` |
| `2fa67280ae08c214` | `src/handlers/chat/chat_post_pipeline.py` |

## unresolved / High residual (non-intro)

- H04 crisis_detection fixture 変更なし
- Durable exactly-once / client_request_id — 主張しない
- SF-E1-NM 文言 — UX 別フェーズへ凍結
- Adversarial R7-H01: flag OFF 既定のため「出荷済み防御」と主張不可
- Masked SI via ambiguous sleep — **監視仮説**（一律窓口不採用）
- D2 ON 本番導入 — **禁止**

## staging

概念候補のみ。「安全な commit 候補」とは呼ばない。

## 次回 Supervisor 再審査チェック

- [x] ambiguous sleep から一律危機窓口削除
- [x] 危機陽性時のみ Emergency/Crisis
- [x] C1 full pipeline 統合テスト
- [x] C2 rollback 統合テスト
- [x] routing suite green（jev_router 除外 181）
- [x] vacuous assert 0（integrity test）
- [x] flag default OFF
- [x] commit / push / live 未実行

満たしても **Jev導入基盤完成 / AI医療監修済み / 製品安全合格 / Gate Passed とは呼ばない**。
