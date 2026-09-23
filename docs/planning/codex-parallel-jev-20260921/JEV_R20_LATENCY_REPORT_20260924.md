# JEV R20 Latency / Payload Report — 2026-09-24

**Workers**: D+E+F (Accuracy / Latency / Payload)  
**Scope**: Local synthetic Jev shadow path. No AWS deploy. Flags default OFF.  
**Companion**: `JEV_R20_ACCURACY_REPORT_20260924.md`

## Contract (unchanged)

| Metric | Threshold |
| --- | ---: |
| warm scenario-cluster CI lower (eligible_warm) | ≥ 900 ms |
| warm_mean_delta_ms_min (point) | ≥ 900 ms |
| rng_sensitivity | **report-only** (not Gate pass logic) |

## Shadow-path latency breakdown (local, synthetic)

Script: `scripts/measure_jev_shadow_latency_breakdown.py`  
Artifact: `log/analysis/jev_r20_latency_breakdown_20260924.json`  
Repeats: 8 · `JEV_API_KEY=present` · API error classes: all null

| Phase | mean ms | p50 | p95 | Notes |
| --- | ---: | ---: | ---: | --- |
| prep (`build_jev_router_state`) | 0.132 | 0.138 | 0.148 | Warm; cold first build ~616 ms (import/channel) |
| payload_serialize | 0.045 | 0.045 | 0.054 | `json.dumps` of wire body |
| **api** (`evaluate_system_one`) | **226.9** | **222.4** | **328.9** | **Dominates (~99% of shadow total)** |
| parse (`parse_jev_answers`) | 0.032 | 0.031 | 0.035 | Local |
| jsonl (`record_shadow_event`) | 1.37 | 0.63 | 6.60 | Already off request path when async shadow |
| shadow_total | 228.5 | 223.2 | 335.7 | Sum of above |

**Bottleneck verdict**: TypeSafe System One RTT/inference. Local prep / serialize / parse are noise. JSONL is secondary (~1 ms mean).

## Payload composition

| Item | Bytes | Share |
| --- | ---: | ---: |
| Questions (`INTENT_ROUTER_QUESTIONS`) | 3503 | **87.6%** of wire |
| Compact state (no `recent_context`) | 447 | ~11% |
| Wire after `recent_context` drop | **3999** | — |
| Wire if `recent_context` kept (duplicate turns) | 4216 | — |
| **Saved by drop** | **217** | ~5.1% of prior wire |

Safety/Policy signals (emergency / security / store / counseling Noul questions + criteria) **retained**.

## Implemented reversible win

1. **`src/services/jev_client.py` — `_compact_outbound_state`**  
   - Omit wire `recent_context` when `recent_turns` is present (JSON cannot preserve Python aliases; questions already say use `recent_turns`).  
   - Caller state unchanged. Empty `meta` omit retained.  
   - Test: `tests/services/test_jev_client.py` (38 passed).

## Already in place (no change needed)

- Process-level **httpx.Client reuse** (`_get_shared_client`) — confirmed by unit test.
- Recent turns already trimmed (`_MAX_RECENT_TURNS=2`, `_MAX_RECENT_TURN_CHARS=160`).
- Shadow worker runs on executor (request path not blocked when async).

## Not implemented (candidates)

| Candidate | Why deferred |
| --- | --- |
| Question / criteria trim | Accuracy-sensitive; needs full remasure; largest remaining byte share |
| Async JSONL from shadow worker | ~1 ms; complexity > benefit vs ~227 ms API |
| Replace `deepcopy` in shadow worker | Warm deepcopy ≪ 0.1 ms |
| orjson / custom serialization | Dependency / risk; serialize ≪ 0.1 ms |

## Gate remasure (paired current − jev:minimal)

### eval_10 fragile seed `20260922`

| Run | CI low | margin vs 900 | rng frac(CI low &lt; 900) | Latency Gate |
| --- | ---: | ---: | ---: | --- |
| r3 | **976.84** | +76.8 | 0.0 (n=50) | Point/CI Pass (small n) |
| **r10** | **898.8** | **−1.2** | **0.51** (n=100; min 891.4) | **Not Passed** |

Artifacts:
- `log/analysis/jev_r20_eval10_r3_seed20260922_20260924.json`
- `log/analysis/jev_r20_eval10_r10_seed20260922_20260924.json`

Compare R17 post-trim r10 same seed: CI low **999.18**, rng below 900 = **0.0**.  
**R20 r10 remasure re-introduces latency fragility** (margin missed by ~1.2 ms; report-only RNG half of seeds below threshold). **Do not invent Pass.**

### Holdout `r17-holdout-v1` (r3 only this cycle)

| Run | CI low | margin | rng frac &lt; 900 | Latency Gate (r3) |
| --- | ---: | ---: | ---: | --- |
| seed42 | 1375.38 | +475 | 0.0 | Pass (local r3) |
| seed20260922 | 1112.02 | +212 | 0.0 | Pass (local r3) |

Holdout r10 not re-run this cycle.

## Remaining bottlenecks / next PDCA

1. **Primary**: Reduce **System One** latency or variance (vendor / model / payload questions). Local client already pooled.
2. **Secondary**: Question payload (~3.5 KB, 88% of wire) — only with accuracy remasure.
3. **Gate risk**: Fragile seed `20260922` r10 CI lower **&lt; 900** — treat Latency Gate as **open / fragile**; need more margin (≥50 ms recommended historically) before staging claims.
4. Re-run holdout r10 + eval_10 seed42 r10 after any further payload change.
5. AWS staging latency owned by Supervisor/Worker A — out of scope here.

## Explicit non-claims

- Latency Gate Closed / Gate A latency formal Pass: **No** (fragile r10 Not Passed)
- Gate B Closed: **No**
- Production enablement: **No**
