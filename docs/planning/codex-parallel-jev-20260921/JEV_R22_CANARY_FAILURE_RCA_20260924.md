# JEV R22 Canary Failure RCA

**Date**: 2026-09-24  
**Source artifact**: `log/analysis/jev_r21_persona_canary.json`  
**Application SHA**: `f571480`  
**Task during canary**: `:10` (shadow ON)

## Executive

| Failure | Count | Layer (measured) | Same root cause? |
| --- | ---: | --- | --- |
| HTTP 503 | 5 (p02–p06) | **Staging wake HTML** upstream of app | No vs timeout |
| Timeout | 1 (p13) | **Client 75s ceiling** on long OTC path | Separate |

## 503×5 — measured

Body title (truncated, no PII): `ステージングを起動しています`.

| Persona | HTTP | elapsed_ms | Layer |
| --- | ---: | ---: | --- |
| p02 typo | 503 | ~76 | wake page |
| p03 short | 503 | ~101 | wake page |
| p04 incoherent | 503 | ~94 | wake page |
| p05 aggressive | 503 | ~114 | wake page |
| p06 joke | 503 | ~76 | wake page |

**Sequence**: p01 completed 200 in ~38s; immediately after, p02–p06 hit wake 503; then p07+ recovered 200.

### inferred

- Flag ON registered new task revision (`:10`); canary began when `/health` looked ok but edge still serving **staging-starting** interstitial (Cloudflare Tunnel / stop-start guard / rolling replace).
- Not ECS OOM, not LLM 503, not Jev queue — HTML interstitial proves **deploy/warm gate**, not app handler.

### Not claimed

- Not application bug in chat pipeline
- Not Jev shadow failure (shadow may not have been reached)

## Timeout×1 — measured

| Persona | HTTP | elapsed_ms | error |
| --- | ---: | ---: | --- |
| p13 multi | 0 | ~75078 | TimeoutError |

### inferred

- Canary harness client timeout was **75s**; full-path OTC often 30–70s+ (R21 latency report). p13 multi-symptom likely exceeded client ceiling while server may still have been working.
- Separate from wake 503.

## Remediation plan (Phase 2)

1. After flag ON: wait ECS `rolloutState=COMPLETED` + repeated `/health` ok + **probe POST** that is not wake HTML.
2. Bounded retry (≤3) only on wake-503 signature; never classify wake-503 as success.
3. Raise client timeout only for OTC paths with explicit cap (e.g. 120s) **and** record timeout as fail if exceeded — do not treat as pass.
4. Re-run identical 50 personas after warm-up; require 50/50.

## Non-claims

Not Production Shadow Ready. Not canary green until re-run.
