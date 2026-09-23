# JEV R21 Latency / Full-Path Performance Report — 2026-09-24

**Worker**: E (Latency / Full-path Performance)  
**Scope**: Separate **Jev-only** latency from **full-path user-perceived** latency. Local synthetic + staging synthetic (flags OFF). No Primary ON. No commit/push. No Gate B policy edits. No AWS alarm creation.

## Executive verdict

| Layer | What it measures | R21 result | Claims allowed? |
| --- | --- | --- | --- |
| **Jev shadow API** | System One RTT only | mean **~240 ms** (local remasure) | Jev intent slice only |
| **Jev Latency Gate** | `current − jev` eligible_warm CI lower ≥ 900 | post-compact **983.75** (≥900); fragile pre **898.8** | Gate point/CI **Pass candidate** with thin margin; RNG notes below |
| **Full-path staging SSE** | User-perceived OTC chat | **TTFD ~31–68 s** (flags OFF); R20 ~120 s was **timeout ceiling** | **Must not** equate to Jev ~227 ms |

**Do not claim**: Jev ~227 ms = overall OTC speedup. Staging OTC remains tens of seconds of serial LLM / scoring / explain work, plus SSE content buffering.

---

## Contract (unchanged; frozen)

| Metric | Threshold | Role |
| --- | ---: | --- |
| warm scenario-cluster CI lower (`eligible_warm`) | ≥ **900 ms** | Latency Gate pass |
| warm_mean_delta_ms_min (point) | ≥ **900 ms** | Latency Gate pass |
| rng_sensitivity | — | **Report-only** (not Gate pass logic) |
| Recommended margin (historical) | ≥ **+50 ms** CI low vs 900 | Fragility buffer |

Bootstrap method: `numpy_bootstrap_scenario_cluster`, `n_boot=2000`, population=`eligible_warm` (SessionOps ineligible by `jev-intent-eligibility-v1`). Contract: `jev-intent-gate-a-v2`.

---

## Pre / Post SSOT (Jev Latency Gate)

### Pre-compact (fragile seed `20260922`, r10)

Artifact: `log/analysis/jev_r20_eval10_r10_seed20260922_20260924.json`

| Field | Value |
| --- | ---: |
| mean_diff_ms | 1197.67 |
| CI 95% lower | **898.8** |
| CI 95% upper | 1679.24 |
| n_scenarios | 7 |
| Latency Gate | **Not Passed** (−1.2 ms) |
| rng (report-only) | **0.51** below 900 (51/100 seeds); min CI low **891.4** |

### Post-compact (same seed/r10; `recent_context` wire drop)

Artifact: `log/analysis/jev_r20_eval10_r10_postcompact_20260924.json`

| Field | Value |
| --- | ---: |
| mean_diff_ms | 1255.51 |
| CI 95% lower | **983.75** |
| CI 95% upper | 1610.22 |
| n_scenarios | 7 |
| Latency Gate | **Pass candidate** (+83.75 vs 900) |
| rng (report-only) | **0.0** below 900 (0/50); min CI low **980.35** |

**Bootstrap / RNG notes**

1. Gate uses **scenario-cluster** bootstrap (resample scenarios), not request-level (deprecated_optimistic).
2. RNG block is **report-only**; do not fold into Gate pass/fail automation.
3. Post-compact margin vs recommended +50 ms: **+83.75** (meets). Fragile pre failed by **1.2 ms** with RNG half below threshold — treat as **seed-fragile**, not “fixed forever.”
4. R21 did **not** re-run full eval_10 r10 (cost/time); Gate SSOT remains R20 postcompact. Local shadow remasure only confirms API still ~0.2–0.5 s.

---

## A. Jev-only latency (local synthetic)

### A1. Shadow breakdown (R21 remasure)

Script: `scripts/r21_jev_shadow_latency_probe.py` → `scripts/measure_jev_shadow_latency_breakdown.py`  
Artifact: `log/analysis/jev_r21_latency_breakdown_20260923_173907.json`  
`JEV_API_KEY=present` · repeats=8 · API errors=all null · flags not enabled

| Phase | mean ms | p50 | p95 |
| --- | ---: | ---: | ---: |
| prep | 0.115 | 0.114 | 0.130 |
| payload_serialize | 0.041 | 0.038 | 0.061 |
| **api** | **240.2** | **218.3** | **463.7** |
| parse | 0.029 | 0.027 | 0.038 |
| jsonl | 2.84 | 0.64 | 18.3 |
| shadow_total | 243.3 | 219.1 | 482.2 |

Cold prep (first import/channel): **972.9 ms** (one-shot; not Gate).

**Bottleneck**: TypeSafe System One RTT (~99% of shadow total). Client already pools `httpx`; Jev retry = once on 429/5xx with jitter only (timeouts not retried). Wire questions still ~88% of payload (accuracy-sensitive — no R21 trim).

Compare R20: api mean 226.9 / p95 328.9. R21 variance higher (p95 463) — vendor jitter; not a regression claim without larger n.

### A2. What Jev Gate saves (intent slice only)

Eval summaries show `current` warm mean ~1.5–1.6 s vs `jev:minimal` ~0.24 s on **IntentRouter-comparable** paths. That delta is **classification**, not OTC recommend TTFD.

---

## B. Full-path user-perceived latency

### B1. Staging synthetic SSE (flags OFF) — R21 probe

Script: `scripts/r21_staging_sse_latency_probe.py`  
Artifact: `log/analysis/jev_r21_staging_sse_latency_20260923_173908.json`  
Host: `https://aws-medicine.yutok.dev` · image `git_commit=8a3c571` · task `medicine-recommend-tunnel:5`

Flag verify (`scripts/r21_verify_staging_flags.py`):  
`JEV_ENABLED=0` · `SHADOW=0` · **`PRIMARY=0`** · `D2=0` · secret present (value not read).

| Turn | TTFT (first status) | TTF advice_delta | TTF cards | TTFD (done) | total | stream_timeout |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| greeting | 42 ms | — | — | **3.9 s** | 3.9 s | false |
| crisis_fast | 123 ms | — | — | **0.17 s** | 0.17 s | false |
| otc_headache_1 | 77 ms | — | — | **30.9 s** | 30.9 s | false |
| otc_headache_2 | 101 ms | — | — | **68.3 s** | 68.3 s | false |

**TTFT vs content**: `advice_chunks=0` on all turns. Status events arrive in tens of ms, but **user-visible reply text waits until `done`**. Cause: `REPLY_STREAM_SSE_ENABLED` defaults **OFF** (`src/services/sse_emit.py`), so `emit_advice_delta` / cards are no-ops.

**Status timeline (OTC)**: validate → triage/counseling → attributes → symptom_analysis → medicine_select (long stalls ~8–27 s and ~35–65 s) → usage_notes → finalize/done. Matches serial LLM + scoring, not Jev.

### B2. R20 ~120 s reinterpretation (pre-SSOT staging)

Artifact: `log/analysis/jev_r20_staging_synthetic_smoke.json`  
Turns ~**120463 / 120058 ms**, `done_keys=[]`.

| Finding | Evidence |
| --- | --- |
| Ceiling = `CHAT_STREAM_TIMEOUT_SEC` default **120** | `src/handlers/chat_stream.py` L49, L568–583 (`code: stream_timeout`) |
| Aligned with Gunicorn | `config/gunicorn_config.py` `timeout=120` |
| R20 smoke missed timeout events | Looked for `status`/`done` only; ignored `event: error` + `stream_timeout` |
| R21 flags OFF completed under ceiling | OTC TTFD 31–68 s (successful done) |

So “staging OTC ~120 s” is often **SSE abort / incomplete delivery**, not a measured successful recommend finish. Hardpath smoke also showed headache **126 s** (`jev_r20_staging_hardpath_smoke.json`) — same ceiling class.

### B3. Local pipeline_perf historical SSOT (full path)

Script: `scripts/r21_local_pipeline_perf_summary.py`  
Artifact: `log/analysis/jev_r21_local_pipeline_perf_summary_20260923_173907.json`  
Source: `log/pipeline_perf_log.jsonl` · **n=3946**

| Metric | P50 | P95 | P99 | max |
| --- | ---: | ---: | ---: | ---: |
| **total_ms (wall)** | **9.9 s** | **38.0 s** | **49.4 s** | **227 s** |
| llm_total_latency_ms | 4.3 s | 16.3 s | — | 64.3 s |
| non_llm_gap_ms | 3.1 s | 23.1 s | — | (large hang cases) |
| llm_call_count | 3 | 8 | — | 20 |

Thresholds: ≥30 s: 378 · ≥60 s: 13 · ≥100 s: 7 · ≥120 s: 5.

**Serial LLM paths dominating ≥20 s turns**: `medicine_qa/focus_llm` ≫ `missing_info_service` · `explanation_generator.batch_usage_notes` · `chat_response_service.personalized_advice` · `llm_triage.stage1`. Intent router (`dialogue.intent_router_llm`) is **not** the OTC wall-time driver.

Example chain (≥60 s): triage → focus_llm×N → missing_info → focus_llm×N → explanation → personalized_advice; sometimes **non_llm_gap ≫ llm_sum** (scoring / RAG / KB / unmetered wait / orphan after SSE cut).

---

## C. Investigation checklist (full path)

| Area | Finding | Latency impact |
| --- | --- | --- |
| Serial LLM calls | 3–9+ calls/turn on OTC; focus_llm repeated | **Dominant** for TTFD |
| Retry / backoff | Jev: 1× on 429/5xx only; OpenAI path no generic tenacity in `llm_client` | Secondary for Jev; OpenAI SDK defaults may still retry |
| Bedrock / OpenAI waits | Staging OTC uses OpenAI roles (gpt-5.4 / mini); long medicine_select / usage_notes gaps | **Dominant** |
| Retrieval / RAG | `local_rag/context_rewrite` rare in slow set; KB augment historically unbounded vs SSE 120s | Medium / hang-class |
| Prompt tokens | Triage prompts 3k+ tokens in historical logs; explain batch heavy | Medium |
| Unnecessary agent/tool | Repeated `medicine_qa/focus_llm` on same turn | High (waste) |
| First-token buffering | `REPLY_STREAM_SSE_ENABLED` default OFF → no advice_delta | **TTFT-content = TTFD** |
| SSE | Keepalive 10s; timeout/orphan/queue wait all **120s**; status progresses but text late | Ceiling + UX |
| Cold start | Jev cold prep ~1 s; ECS Fargate task typically warm via Tunnel | Low for staging warm |
| Task CPU/mem | Fargate **512 CPU / 1024 MiB** (`AWS_FARGATE_TUNNEL.md`) | Possible scoring pressure; not proven primary |
| Connection pool | Jev shared httpx OK; OpenAI client reuse exists | Fine for Jev |
| DNS/TLS / Cloudflare Tunnel | Greeting TTFT ~42 ms via `aws-medicine.yutok.dev` | Tunnel hop **not** OTC bottleneck |
| Safety | Crisis path TTFD **166 ms** (fast path OK); do not weaken detectors for speed | Keep |

---

## D. Reversible improvement proposals only

Ordered by expected user-perceived gain / reversibility. **None implemented in R21** (measure-only). Safety unchanged.

| ID | Change | Reversible how | Expected effect | Risk |
| --- | --- | --- | --- | --- |
| E1 | Staging flag `REPLY_STREAM_SSE_ENABLED=1` | Unset env / redeploy prior task | Content TTFT ≪ TTFD when stream paths used | Partial text UX; verify cards/disclaimer order |
| E2 | Emit `cards` / safe interim status earlier in medicine_select | Feature flag | Perceived wait ↓ without cutting safety | Must not skip safety_gate |
| E3 | Cap / dedupe `medicine_qa/focus_llm` per turn (existing latency plan hooks) | Flag off | Cut serial OpenAI waits | Accuracy remasure required |
| E4 | Parallelize explain vs non-dependent work (`LATENCY_RECO_PARALLEL` / score parallel already in v3 SSOT) | Env flags | TTFD ↓ on OTC | Race / cache bugs |
| E5 | Keep Jev **async shadow only**; never block request on System One | Already fail-open | Avoid adding ~0.2–0.5 s (or timeout) to path | Primary ON forbidden here |
| E6 | Raise `CHAT_STREAM_TIMEOUT_SEC` **only with** partial SSE + orphan budget | Env rollback | Fewer false 120s aborts | Orphan CPU/cost; does **not** fix root serial LLM |
| E7 | Optional Fargate bump 512→1024 CPU / 1024→2048 MiB | Task def rollback | Help CPU-bound scoring | Cost; measure before/after |
| E8 | Question payload trim for Jev | Revert compact | Gate margin | Accuracy Gate remasure mandatory |

**Deferred / avoid**

- Claiming Gate A / production speedup from Jev numbers alone.  
- Weakening crisis / Gate B / safety for latency.  
- AWS alarm creation (Worker F).  
- Turning Primary ON.

---

## E. Scripts added (R21 probes)

| Script | Purpose |
| --- | --- |
| `scripts/r21_staging_sse_latency_probe.py` | Staging SSE TTFT / TTFD / `stream_timeout` detection |
| `scripts/r21_local_pipeline_perf_summary.py` | Local `pipeline_perf` P50/P95 + serial chains |
| `scripts/r21_jev_shadow_latency_probe.py` | Wrapper → Jev shadow phase breakdown |
| `scripts/r21_verify_staging_flags.py` | Confirmed flags OFF (pre-existing in tree) |

---

## F. Artifacts index

| Artifact | Role |
| --- | --- |
| `log/analysis/jev_r21_latency_breakdown_20260923_173907.json` | Jev-only remasure |
| `log/analysis/jev_r21_staging_sse_latency_20260923_173908.json` | Full-path staging TTFT/TTFD |
| `log/analysis/jev_r21_local_pipeline_perf_summary_20260923_173907.json` | Historical full-path P50/P95 |
| `log/analysis/jev_r20_eval10_r10_seed20260922_20260924.json` | Gate pre-SSOT fragile |
| `log/analysis/jev_r20_eval10_r10_postcompact_20260924.json` | Gate post-SSOT Pass candidate |
| `log/analysis/jev_r20_staging_synthetic_smoke.json` | R20 ~120 s / empty done |
| `docs/ops/LATENCY_IMPROVEMENT_V3.md` | Prior latency env SSOT (GCP-era; flags reusable) |

---

## Explicit non-claims

- Jev ~227–240 ms ≠ staging OTC user speed.  
- Latency Gate formal Closed / Gate A production: **No** (Pass **candidate** only; fragile seed history).  
- Gate B / product safety / Production Go: **No**.  
- Primary / Shadow / D2 ON: **No** (verified OFF).  
- Commit / push: **No**.
