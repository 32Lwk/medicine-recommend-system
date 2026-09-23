# JEV R20 AWS Staging Optimization Report

**Date**: 2026-09-24  
**Profile**: `default` (account `6209****6973`)  
**Image commit**: `8a3c571`  
**Task**: `medicine-recommend-tunnel:4` (flags ON + `JEV_API_KEY` secret)

## Identity / uniqueness

| Check | Result |
| --- | --- |
| STS | OK on `default` |
| Staging hosts | `aws-medicine.yutok.dev` / origin |
| Production GCP | not touched |
| Deploy mode | fargate_tunnel |

## Deployment

| Step | Result |
| --- | --- |
| Local regression | 79 passed |
| Docker build/push/ECS | OK |
| Health flags OFF then ON | 200 |
| Temp flags | `JEV_ENABLED=1` `SHADOW=1` `PRIMARY=0` `D2=1` |
| Jev secret | created `medicine-recommend/aws-staging/jev-api-key` (value not logged) |
| Synthetic SSE smoke | 2/2 HTTP 200 (~120s/turn — **latency bottleneck**) |

## Privacy/DPA

```text
Privacy/DPA:
Owner-accepted residual for synthetic staging only.
Not approved for real-user production data.
```

## Open

- User-facing chat P95 ~120s on staging (LLM path dominant; shadow must stay async)
- Accuracy PDCA / holdout on staging with live shadow pending settle
- Flags must return OFF before session end

## Non-claims

Not production traffic / primary / D2 production / Gate B Go / push.
