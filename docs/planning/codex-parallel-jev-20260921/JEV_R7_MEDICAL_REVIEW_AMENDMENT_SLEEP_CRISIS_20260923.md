# R7 Medical Review Follow-up Amendment — Ambiguous Sleep Crisis Copy

**Date**: 2026-09-23  
**Scope**: Correct recording of ambiguous-sleep crisis-hotline policy after Supervisor follow-up.

## Policy (authoritative)

| Rule | Status |
| --- | --- |
| Ambiguous sleep alone shows いのちの電話 / crisis hotline | **不採用** |
| Crisis hotline display | Only when `crisis_detected` OR `emergency_detected` OR overdose/self-harm signal |
| Ambiguous sleep boundary copy | OTC/処方境界・情報確認促しのみ（違法・自殺・依存を断定しない） |
| Crisis path owner | Existing Emergency/Crisis handlers — **policy adapter does not substitute** |
| Masked suicidal ideation via ambiguous sleep | **監視仮説**（一律危機窓口では扱わない） |

## Do not conflate

- Prior second-opinion *recommendation* to append hotline to `_AMBIGUOUS_SLEEP_BOUNDARY` was **not adopted** as shipped safety control.
- Code after this follow-up removed any such hotline from ambiguous sleep copy.
- Older review docs describing that recommendation remain historical; this amendment is the current policy.

## Code fingerprint (post follow-up, commit未作成)

| SHA256[:16] | File |
| --- | --- |
| `52f815b663906554` | `src/dialogue/routing/policy_adapters.py` |
| `21c981684489fb6d` | `src/dialogue/routing/pre_route_signals.py` |
| `2fa67280ae08c214` | `src/handlers/chat/chat_post_pipeline.py` |

**外部医療セカンドオピニオン未取得。** AI監修 ≠ 人間医療監修。製品安全合格ではない。
