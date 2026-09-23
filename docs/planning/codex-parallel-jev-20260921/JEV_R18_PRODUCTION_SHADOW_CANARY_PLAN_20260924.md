# JEV R18 Production Shadow Canary Plan (design only)

**Execution**: **R18 does not run canary.** Human approval required each stage.

## Preconditions (all required before Stage 0)

- Production Shadow readiness ≠ Not Ready (privacy/DPA, Gate B shadow-scope contract, kill switch drill, rollback drill)
- `JEV_INTENT_ROUTER_PRIMARY=0`, `POLICY_ENFORCEMENT_D2=0` in production config
- Push/PR/release approved by Owner

## Stages

| Stage | Action | Shadow % | Max duration | Auto-expand |
| --- | --- | ---: | --- | --- |
| 0 | Deploy bits only; flags OFF; health | 0 | — | No |
| 1 | Shadow ON | 0.1% | short window | No — human |
| 2 | Expand | 1% | after Stage1 green | No — human |
| 3 | Expand | 5% | after Stage2 green | No — human |
| 4 | Cap | ≤10% | until Gate B decision | No — human |

## Invariants every stage

- executed route = legacy only
- user response = legacy only
- high-risk / SessionOps = eligibility skip (no Jev API)
- SessionOps excluded from latency Gate population
- kill switch drillable without redeploy if possible; else documented redeploy OFF
- mismatch triage on-call playbook live

## Abort immediately

queue saturation, user P95 regression, error/retry storm, memory growth, continuous API timeout, privacy incident, any executed-route change.
