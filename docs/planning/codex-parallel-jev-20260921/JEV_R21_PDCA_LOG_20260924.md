# JEV R21 PDCA Log — 2026-09-24

## Cycle 0 — Phase 0 state fix

### measured
- local HEAD `56889ea`; ahead of origin/main by 21 commits
- staging health `git_commit=8a3c571`; task `medicine-recommend-tunnel:5`
- staging flags all 0; secret names include `JEV_API_KEY` (value not read)
- dirty WT: AWS ops scripts/docs, logs, unrelated untracked (EXCLUDE from RC)

### inferred
- SHA mismatch: staging image behind local HEAD (missing `8f03b03` wire compact + docs commits)

### Plan
- Freeze RC INCLUDE to Jev IntentRouter chain only
- Do not deploy dirty AWS/UX WT files
- Next: Gate B Closed-candidate work before redeploy

### Act
- Accept Phase 0 docs commit `469c9fe` (INCLUDE only R21 docs)
- Flags: task-def env absent → defaults OFF (measured)
- Deploy deferred until Gate B Closed-candidate + observability ready
- Do not deploy dirty WT or unconditional HEAD

## Cycle 1 — Gate B Closed-candidate (in progress)

### Plan
- Close F-H03-R1/R2, F-H04-R1, F-H05-R1 residuals without gold retargeting
- Workers: B (policy), C (medical), D (accuracy), E (latency), F (CW)
- Supervisor avoids concurrent edits on Worker B owned files

### Check
- False-pass Challenger: Reject full Closed; soft SI FP + H-05 tautology found
- Supervisor: soft FP narrowed; H-05 assert strengthened; R7 rollback session-clean preserved
- routing/reliability/HTTP: 338 passed wave; targeted Gate B green

### Act
- Accept Conditional Closed-candidate (not Owner Go)
- Commits: `047af9f` Gate B, `3812e63` CloudWatch
- Observability alarms live; canary not started (flags OFF)
- SHA mismatch remains (staging `8a3c571` vs local HEAD)

## Cycle 2 — Accuracy holdout + RC deploy prep (next)

### Plan
- Independent holdout fixtures committed; run eval10 when scripts ready
- Do not deploy until Gate B Conditional + observability + Owner-ready RC tip

## Cycle E — Latency / full-path (Worker E)

### measured
- staging flags all 0 (`medicine-recommend-tunnel:5`, health `8a3c571`)
- Jev shadow local remasure api mean **240 ms** (p95 464); cold prep ~973 ms
- Gate SSOT: pre-compact CI low **898.8** (Not Passed); post-compact **983.75** (Pass candidate); RNG report-only 0.51 → 0.0
- staging SSE probe: greeting TTFD 3.9s; OTC1 **30.9s**; OTC2 **68.3s**; advice_delta=0 (`REPLY_STREAM_SSE_ENABLED` default OFF)
- R20 ~120s reinterpreted as `CHAT_STREAM_TIMEOUT_SEC` ceiling + smoke missing `stream_timeout` events
- local pipeline_perf n=3946: total P50 **9.9s** / P95 **38s**; serial focus_llm / missing_info / explain / advice dominate

### inferred
- Jev ~227–240 ms must not be claimed as OTC speedup; full-path TTFD tens of seconds
- Content TTFT = TTFD until reply-stream SSE flag ON

### Plan / output
- Report: `JEV_R21_LATENCY_FULL_PATH_REPORT_20260924.md`
- Probes: `scripts/r21_staging_sse_latency_probe.py`, `r21_local_pipeline_perf_summary.py`, `r21_jev_shadow_latency_probe.py`
- Reversible proposals E1–E8 only; no Primary ON; no commit/push
