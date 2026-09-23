# JEV R19 Circuit Breaker / Rollback Report — 2026-09-24

**Worker:** E+G+F (SRE Circuit)  
**Scope:** local only — no AWS write, no push, no secrets  
**Flags default:** `JEV_ENABLED=false`, `JEV_INTENT_ROUTER_SHADOW=false`, `JEV_INTENT_ROUTER_PRIMARY=false`, `POLICY_ENFORCEMENT_D2=false`

---

## 1. Verdict

| Item | Status |
| --- | --- |
| Circuit breaker (closed → open → half-open probe) | ✅ Implemented |
| Max pending (~8) + concurrency | ✅ Soft cap + ThreadPoolExecutor |
| Per-request timeout | ✅ `JEV_TIMEOUT_SEC` (default 3.5s) via httpx |
| Retry cap + jitter | ✅ `JEV_HTTP_MAX_RETRIES` 0..2 + ms jitter |
| Queue full drop (fail-open user path) | ✅ |
| Manual kill (`JEV_ENABLED=0` / shadow=0) | ✅ |
| Emergency disable | ✅ `JEV_SHADOW_EMERGENCY_DISABLE` |
| User response independent / shadow-only | ✅ |
| Local kill-switch rehearsal | ✅ script + test |
| Staging AWS drill | ❌ Not in this worker (no AWS write) |

**Shadow async isolation:** Conditional Ready for *local* rehearsal; production shadow still blocked by privacy/Gate B (out of scope).

---

## 2. Implementation map

| Component | Location |
| --- | --- |
| Circuit / rate / cost admit | `src/dialogue/routing/jev_shadow_guards.py` |
| Schedule wiring | `src/dialogue/routing/jev_router.py` (`schedule_jev_shadow`) |
| HTTP timeout / retry+jitter | `src/services/jev_client.py` + `config/routing_config.py` |
| SRE metrics facade | `src/services/jev_sre_guards.py` |
| Local rehearsal | `scripts/jev_kill_switch_rollback_rehearsal.py` |

### Behavior (fail-open for users)

1. Kill flags OFF → `schedule_jev_shadow` returns `False` (no API).
2. Emergency disable / circuit open / rate / cost → skip shadow, record metric, **legacy route unchanged**.
3. Queue full / submit failed → drop shadow task, record `queue_full` / `submit_failed`.
4. Consecutive failures → circuit **open** for `JEV_CIRCUIT_OPEN_SEC`; then **half-open** with limited probes.

---

## 3. Candidate env vars (circuit / runtime)

| Env | Default (staging-tiny candidate) | Notes |
| --- | ---: | --- |
| `JEV_ENABLED` | false | Master kill |
| `JEV_INTENT_ROUTER_SHADOW` | false | Shadow kill |
| `JEV_SHADOW_EMERGENCY_DISABLE` | false | Extra drop |
| `JEV_MAX_PENDING` | 8 | Soft pending |
| `JEV_EXECUTOR_WORKERS` | 2 | Concurrency |
| `JEV_TIMEOUT_SEC` | 3.5 | Per-request |
| `JEV_HTTP_MAX_RETRIES` | 1 (0..2) | 429/5xx only |
| `JEV_RETRY_JITTER_MS_MIN/MAX` | 50..150 | Retry sleep |
| `JEV_CIRCUIT_FAILURE_THRESHOLD` | 5 | Open trigger |
| `JEV_CIRCUIT_OPEN_SEC` | 60 | Open duration |
| `JEV_CIRCUIT_HALF_OPEN_PROBES` | 1 | Probe cap |

Legacy aliases `JEV_SHADOW_*` still accepted by the guard loader when `routing_config` import fails.

---

## 4. Local kill-switch / rollback rehearsal

```powershell
cd d:\Programing\medicine-recommend
$env:JEV_ENABLED = "false"
$env:JEV_INTENT_ROUTER_SHADOW = "false"
.venv\Scripts\python.exe scripts\jev_kill_switch_rollback_rehearsal.py
.venv\Scripts\python.exe -m pytest tests\dialogue\routing\test_jev_shadow_guards.py tests\scripts\test_jev_kill_switch_rollback_rehearsal.py -q
```

**Not covered here:** Cloud Run / AWS ECS env update drill (Owner / Worker D).

---

## 5. Remaining gaps

1. Multi-process pending/circuit state is process-local (no Redis/SQS).
2. Staging drill with live Task Definition env still unproven.
3. Half-open probe accounting is best-effort under extreme concurrency.
4. Production shadow still Not Ready (privacy / Gate B — other workers).

---

*R19 local. NOT PUSHED. NOT LIVE.*
