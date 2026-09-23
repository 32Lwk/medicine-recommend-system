# JEV R21 AWS Observability / Cost Guard Report

**Date**: 2026-09-24  
**Worker**: F (AWS Observability / Cost Guard)  
**Account**: `620992446973` (staging) · **Region**: `ap-northeast-1` · **Profile**: `default`  
**Constraint**: Jev flags remain **OFF**; **canary not started**; **no app image deploy**; **no git commit**

---

## 1. Verdict

CloudWatch **metric namespace + 8 alarms** are live in staging. App **EMF emit path** is wired in code (takes effect on next image deploy — intentionally not deployed this round). Staging task `medicine-recommend-tunnel:5` still has all Jev/D2 flags **0**.

---

## 2. AWS resources created

### 2.1 Custom namespace / metrics

| Item | Value |
| --- | --- |
| Namespace | `MedicineRecommend/Jev` |
| Dimensions | `Environment=development`, `Service=medicine-recommend` |
| Seed | `put-metric-data` Value=0 for each name (registration only; no PII) |

Metric names:

| Metric | Unit | Meaning |
| --- | --- | --- |
| `attempt` | Count | Shadow API attempted |
| `success` | Count | Shadow parse/success |
| `timeout` | Count | Timeout class |
| `parse_failure` | Count | invalid_schema / invalid_json / schema_error |
| `fallback` | Count | Attempted failure / fallback_reason |
| `mismatch` | Count | legacy vs jev mismatch |
| `circuit_open` | Count | Circuit open / half-open saturated |
| `queue_saturation` | Count | `queue_full` |
| `high_risk_attempt` | Count | High-risk API attempt anomaly |
| `cost_estimate` | None | Estimated USD (token×rate; **not invoice**) |
| `primary_flag_anomaly` | Count | PRIMARY unexpectedly ON |
| `D2_flag_anomaly` | Count | D2 ON without `JEV_D2_ALLOW` |

### 2.2 Alarms

| Alarm name | Signal | Threshold (staging defaults) | Missing data |
| --- | --- | ---: | --- |
| `medicine-recommend-jev-failure-rate` | Metric math `(attempt-success)/attempt` | > 0.25 (2×5m) | notBreaching |
| `medicine-recommend-jev-timeout-rate` | Metric math `timeout/attempt` | > 0.20 (2×5m) | notBreaching |
| `medicine-recommend-jev-queue-saturation` | Sum `queue_saturation` | > 0 / 5m | notBreaching |
| `medicine-recommend-jev-circuit-open` | Sum `circuit_open` | > 0 / 5m | notBreaching |
| `medicine-recommend-jev-cost-ceiling` | Sum `cost_estimate` | > **$0.50** / 1d | notBreaching |
| `medicine-recommend-jev-high-risk-anomaly` | Sum `high_risk_attempt` | > 0 / 5m | notBreaching |
| `medicine-recommend-jev-primary-flag-on` | Max `primary_flag_anomaly` | > 0 / 1m | notBreaching |
| `medicine-recommend-jev-d2-flag-on` | Max `D2_flag_anomaly` | > 0 / 1m | notBreaching |

SNS: not attached (set `ALARM_SNS_TOPIC_ARN` and re-run script to wire).  
Reversible delete: `DELETE=1 ./scripts/r21_setup_jev_cloudwatch.sh`

**Not created / not changed**: ECS task definition, service deployment, Jev env flags, canary, budget SNS subscriptions.

---

## 3. Code / script changes (local WT — not committed)

| Path | Change |
| --- | --- |
| `src/services/jev_cloudwatch_metrics.py` | **New** — EMF emit (+ optional `JEV_CW_PUT_METRIC=1` PutMetricData); PII-safe dims only |
| `src/services/jev_metrics.py` | After JSONL write → `emit_shadow_cloudwatch_metrics(payload)` |
| `src/dialogue/routing/router.py` | `_maybe_schedule_jev_shadow` always calls `emit_flag_anomaly_metrics()` (emits **only** when PRIMARY/D2 anomalous) |
| `tests/services/test_jev_cloudwatch_metrics.py` | **New** unit tests (6 passed) |
| `scripts/r21_setup_jev_cloudwatch.sh` | **New** — seed metrics + put alarms; account guard; no ECS mutate |
| `scripts/r21_verify_jev_flags_off.sh` | **New** — assert flags == 0; print secret **names** only |
| `scripts/setup-aws-cloudwatch.sh` | Opt-in hook: `SETUP_JEV_CW=true` → calls r21 script |

Kill switches:

- `JEV_CW_METRICS=0` — disable all app emits  
- `JEV_CW_PUT_METRIC=1` — also call PutMetricData (needs IAM; default off; EMF needs no extra IAM)  
- `JEV_D2_ALLOW=1` — suppress `D2_flag_anomaly` when D2 intentionally allowed

---

## 4. Flag verification (post-setup)

```
taskDefinition=medicine-recommend-tunnel:5
  JEV_ENABLED=0  [OK]
  JEV_INTENT_ROUTER_SHADOW=0  [OK]
  JEV_INTENT_ROUTER_PRIMARY=0  [OK]
  POLICY_ENFORCEMENT_D2=0  [OK]
```

Re-check anytime:

```bash
AWS_PROFILE=default ./scripts/r21_verify_jev_flags_off.sh
```

---

## 5. How emits reach CloudWatch (after future image deploy)

1. Shadow event → `record_shadow_event` → JSONL + EMF JSON line on logger `jev.cw_emf`  
2. Container stdout → awslogs → `/ecs/...` → CloudWatch Logs **auto-extracts EMF** into `MedicineRecommend/Jev`  
3. Flag anomalies → every route resolve path; **silent when flags OFF** (no metric spam)

Until the image with this code is deployed, alarms stay mostly `INSUFFICIENT_DATA` / OK with `notBreaching` — correct for flags-OFF shadow.

---

## 6. Non-claims / follow-ups

- Cost ceiling uses **estimate**, not AWS invoice / Typesafe bill.  
- Task role still lacks `cloudwatch:PutMetricData` (EMF path does not need it).  
- Optional: attach SNS (`medicine-recommend-budget-stage*` or ops topic), raise Owner-approved dollar caps, deploy RC image when Gate B allows.  
- **Do not** set `JEV_*` / D2 ON until Owner + canary plan.

---

## 7. Commands used (ops)

```bash
AWS_PROFILE=default ./scripts/r21_setup_jev_cloudwatch.sh
AWS_PROFILE=default ./scripts/r21_verify_jev_flags_off.sh
# rollback alarms only:
DELETE=1 AWS_PROFILE=default ./scripts/r21_setup_jev_cloudwatch.sh
```
