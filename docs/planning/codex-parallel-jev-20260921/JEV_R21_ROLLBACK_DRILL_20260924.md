# JEV R21 Rollback Drill

**Date**: 2026-09-24  
**Deployed SHA**: `f571480`  
**Method**: `scripts/r21_staging_shadow_flags.sh` ON → OFF (PRIMARY=0, D2=0 locked)

## measured

| Step | Time (UTC) | Task rev |
| --- | --- | ---: |
| Drill start | 2026-09-23T18:23:27Z | — |
| Shadow ON | 18:23:30Z | :12 |
| Shadow OFF | 18:23:53Z | :13 |
| Flags verify (API) | post-settle | :13 all 0 |
| Health | ok | `git_commit=f571480` |

MTTR (flag OFF register): ~23s ON→OFF register; settle to healthy verify ~4 min including deploys.

## Checks

- [x] kill-switch via env flags OFF  
- [x] PRIMARY remains 0  
- [x] D2 remains 0  
- [x] health maintained after settle  
- [x] final flags OFF via AWS API (`r21_verify_staging_flags.py`)  
- [ ] pending Jev request drain instrumentation (inferred OK; no in-flight metric proof)  
- [ ] failure-injection alarm fire (not separately injected this drill)

## Verdict

**Kill-switch drill Pass candidate** (flags OFF proven). Not full alarm-injection drill.

## Non-claims

Not production rollback proof. Not local-only rehearsal claimed as AWS green alone — this ran on staging ECS.
