# JEV R20 Failure / Rollback Report

**Date**: 2026-09-24

## Kill / flag rollback (staging)

| Action | Result |
| --- | --- |
| Temp ON (`:3` / `:4`) | JEV shadow+D2 ON, primary 0 |
| Temp OFF (`:5`) | All JEV_* and D2 set to **0** via `scripts/r20_staging_jev_flags.sh off` |
| Secret `JEV_API_KEY` | Remains in task secrets (unused while flags OFF) |
| Local kill rehearsal | Prior R19 script ALL CLEAR |

## Failure injection (local)

`tests/reliability/test_jev_shadow_failure_injection.py` + `scripts/jev_shadow_failure_injection_local.py` — 8/8 from R19 (not re-run this hour).

## Staging synthetic hard-path

`log/analysis/jev_r20_staging_hardpath_smoke.json`: headache/sessionops/crisis all HTTP 200; crisis path ~2.3s (fast terminal).

## Non-claims

Not production rollback proof. Not Gate B Go.
