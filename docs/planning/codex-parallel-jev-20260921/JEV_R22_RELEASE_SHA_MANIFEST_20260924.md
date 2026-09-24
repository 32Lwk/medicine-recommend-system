# JEV R22 Release SHA Manifest

**Date**: 2026-09-24  
**Push**: Forbidden

## SHA relation (Phase 0 measured)

| Role | SHA | Notes |
| --- | --- | --- |
| Application / deployed | `f571480` | staging `/health` `git_commit` |
| Evaluation tooling / local HEAD | `cbed3c4` | runners + reports after deploy tip |
| Fixture family | holdout `tests/fixtures/jev_holdout_r21/` + eval_10 / r17 (unchanged gold) | |
| Report tip (will advance) | R22 docs on subsequent commits | |

## Proof: no app code delta f571480..cbed3c4

```
git diff --stat f571480..HEAD -- src/ config/ main.py start.sh requirements-prod.txt Dockerfile
→ empty
```

Commits after `f571480` are docs/scripts/log/analysis only (`9bf0f15`, `27457af`, `cbed3c4`).

## Decision

**Do not redeploy** for SHA alignment. Keep application SHA = `f571480`. Tooling SHA = `cbed3c4` (and later R22 commits).

## Staging snapshot

- task: `medicine-recommend-tunnel:13`
- flags: all 0
- deployment: PRIMARY COMPLETED
- alarms: 8× OK
- secret `JEV_API_KEY`: present (value not read)

## Rollback target

- image: ECR `:latest` baked as `f571480`
- flags OFF script: `scripts/r21_staging_shadow_flags.sh off`
