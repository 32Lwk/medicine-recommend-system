# JEV R22 Rollback Drill

**Date**: 2026-09-24  
**Application SHA**: `f3af9c3`

## measured

| Step | Result |
| --- | --- |
| Canary end OFF | task `:17`, flags 0 |
| Kill-switch ON→OFF | `:18` → `:19` |
| Final flags (API) | all 0 on `:19` |
| Final health | `ok` / `f3af9c3` (after settle) |
| Intentional failure-injection alarm fire | **not** separately executed |

## Verdict

**Kill-switch Pass candidate** (env OFF proven twice). Alarm-injection drill incomplete.

## Non-claims

Not production rollback proof.
