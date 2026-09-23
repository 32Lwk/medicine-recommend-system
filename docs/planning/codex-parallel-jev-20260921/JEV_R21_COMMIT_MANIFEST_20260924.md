# JEV R21 Commit Manifest

**Push**: Forbidden. Local commits only.

| # | SHA | Topic | INCLUDE | Tests / notes | Rollback |
| --- | --- | --- | --- | --- | --- |
| 1 | `469c9fe` | Phase 0 RC + Safety Action Contract SSOT | R21 docs | n/a | `git revert 469c9fe` |
| 2 | `047af9f` | Gate B Conditional Closed-candidate | policy_*/Gate B tests/docs | routing+HTTP Gate B green; Challenger rejects full Closed | `git revert 047af9f` |
| 3 | `3812e63` | CloudWatch Jev metrics/alarms | jev_cloudwatch + r21 CW scripts | unit tests; 8 alarms live; flags OFF | delete alarms via `DELETE=1` script; revert commit |

## Pending

4. Holdout fixtures + latency/canary tooling + state logs  
5. Staging RC image deploy (eval SHA match) — after Owner-ready  
6. Synthetic canary + rollback drill evidence  
7. Final supervisor report  

## EXCLUDE

- Dirty `docs/ops/AWS_*`, unrelated `scripts/setup-aws-*` WT dirt (except dedicated r21_*)  
- `tmp_*`, notebooklm-history, ux-pdca, image archives  
- Secrets / `.env`
