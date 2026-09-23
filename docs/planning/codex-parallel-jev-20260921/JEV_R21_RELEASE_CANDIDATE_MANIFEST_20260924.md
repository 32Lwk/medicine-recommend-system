# JEV R21 Release Candidate Manifest

**Date**: 2026-09-24  
**Purpose**: Isolate Jev IntentRouter RC for evaluate↔deploy SHA alignment.  
**Push**: Forbidden.

## SHA snapshot (Phase 0)

| Role | SHA | Notes |
| --- | --- | --- |
| Local HEAD | `56889ea` | Includes R20 docs + postcompact evidence |
| Staging health image | `8a3c571` | **Mismatch** vs HEAD |
| Staging task | `medicine-recommend-tunnel:5` | flags all 0 |
| Rollback image target | `8a3c571` / prior ECR `:latest` before next deploy | documented |
| Proposed RC deploy tip (after Gate B green) | TBD — last Jev code commit at deploy time | must equal health `git_commit` |

## INCLUDE (Jev / D2 / eval / staging tooling)

Committed chain (origin..HEAD, Jev-relevant):

| SHA | Topic |
| --- | --- |
| `b536620`…`9bcb882` | Phase1 foundations |
| `a40f353` | eval membership |
| `67b8ea9`…`74e4337` | evidence |
| `9ee28b4`…`46d687b` | trim/persona/meta |
| `876c718`…`5bf3f07` | SessionOps FN + R18 |
| `c446ab0`…`669d966` | R19 Gate B / guards / PII / false-pass |
| `8f03b03` | R20 staging tooling + `jev_client` compact |
| `56889ea` | R20 postcompact evidence / flag OFF docs |

Source areas: `src/dialogue/routing/jev_*`, `policy_*`, `pre_route_*`, `src/services/jev_*`, `config/routing_config.py` (Jev keys), `tests/**/jev*`, `tests/**/r19*`, `tests/reliability/*`, `scripts/r20_*`, `scripts/jev_*`, `scripts/eval_jev_*`, `docs/planning/codex-parallel-jev-20260921/JEV_R*`

## EXCLUDE (do not stage/commit into RC or deploy context)

- `docs/ops/AWS_*` dirty (unless R21 observability narrowly scoped later)
- `scripts/setup-aws-*.sh` / `tune-aws-*` / `sync-*` unrelated dirt
- `scripts/aws-env.ps1`, `scripts/lib/aws_common.sh` dirt unless intentional
- `log/*.jsonl` runtime churn (analysis artifacts may be committed per project log rule when intended)
- `tmp_*`, `tools/`, `local_outputs/`, `static/img/about/generated/archive/`
- `docs/planning/notebooklm-history/`, `ux-pdca-20260922/`, `..bfg-report/`
- `.env` / secrets

## Commit dependency order (future R21 commits)

1. Gate B detector/policy + HTTP E2E fidelity  
2. Safety Action Contract SSOT + fixtures  
3. Medical/Unicode/holdout tests  
4. Observability/alarms  
5. Latency full-path improvements (if any)  
6. Canary/rollback tooling  
7. Evidence/docs  

## Known residuals

- Gate B Hard No-Go; H-03/H-04 Open  
- product safety 未合格  
- Production Shadow Not Ready  
- staging OTC ~120s (full LLM path ≠ Jev ~227ms)  
- evaluated HEAD ≠ deployed image until redeploy after RC freeze  

## Non-claims

Not Gate Passed. Not product safety Passed. Not production Go. Not push.
