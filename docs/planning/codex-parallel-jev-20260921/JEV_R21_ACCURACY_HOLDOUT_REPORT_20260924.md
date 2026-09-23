# JEV R21 Accuracy / Independent Holdout Report — 2026-09-24

**Worker**: D (Accuracy / Independent Holdout)  
**HEAD (dirty WT)**: `469c9fe`  
**Stamp**: `20260923_174144`  
**Mode**: `jev:minimal` only (`--jev-only`)  
**Commit / push**: **not performed** (Worker D scope)  
**Gold retargeting**: **none** — `jev_intent_router_eval_10.yaml` and `jev_intent_router_holdout_r17.yaml` untouched

---

## Executive verdict (accuracy evidence only)

| Claim | Status |
| --- | --- |
| Local synthetic Jev `accuracy_gate` on eval_10 r10 (seed42 + seed20260922) | **Measured Pass** — 70/70 both seeds |
| Independent holdout `r17-holdout-v1` r10 (seed42 + seed20260922) | **Measured Pass** — 80/80 both seeds |
| R21 holdout-only paraphrase / persona / unicode-eligible / negative-control | **Measured Pass** on Gate-eligible rows |
| `membership_unknown` | **0** on all r10 artifacts |
| `api_error` / `fallback` | **0 / 0** on all r10 artifacts |
| Critical FN (Jev attempted rows) | **0** |
| High FN (Jev attempted rows) | **0** |
| Formal Gate A-accuracy unconditional Passed | **Not claimed** (see blockers / integrity notes) |
| Gate B / product safety / primary ON | **Out of scope** |

---

## Evidence taxonomy

| Class | Meaning in this report |
| --- | --- |
| **measured** | Fresh local API run under stamp `20260923_174144` (or noted smoke) |
| **inferred** | Derived from harness contract / eligibility without new API call |
| **AI-reviewed** | Worker D judgment on fixture separation / FN definition |
| **unresolved** | Blocked or not re-measured this cycle |
| **out-of-scope** | Owned by other workers / forbidden |

---

## 1. Fixture separation (measured + AI-reviewed)

| Population | Path | Role | Gold overwrite? |
| --- | --- | --- | --- |
| Eval gold | `tests/fixtures/jev_intent_router_eval_10.yaml` | Gate A synthetic eval_10 | **No** (SHA256 prefix `122f047cd2aaee1f`) |
| Prior independent holdout | `tests/fixtures/jev_intent_router_holdout_r17.yaml` | R17 paraphrase holdout | **No** (SHA256 prefix `209325dfe8680731`) |
| R21 holdout-only | `tests/fixtures/jev_holdout_r21/*.yaml` | New independent axes | **New files only** |

R21 holdout family `r21-holdout-v1`:

| File | Axis | Eligible Gate scenarios (fixture) | Ineligible retained |
| --- | --- | --- | --- |
| `paraphrase.yaml` | Fresh paraphrase | 7 | SessionOps ×1 (kept) |
| `unicode_evasion.yaml` | ZW / spaced high-risk + eligible control | 1 | Emergency/Security/prescription/exam ×5 |
| `persona.yaml` | Persona-flavored single-turn | 5 | SessionOps ×1 (kept) |
| `negative_control.yaml` | Mild / architecture / quoted / hypothetical | 6 (fixture) | none deleted |

**Rules obeyed**: SessionOps / `membership_unknown` not deleted to inflate scores; failing cases not deleted; evaluator (`eval_jev_intent_router_10.py`) not unified with fixture generator; summarizer is post-hoc only (`eval_jev_r21_holdout_summarize.py`).

---

## 2. Required measurements — Jev accuracy_gate (measured)

Runner: `scripts/eval_jev_r21_holdout_runner.py` → `scripts/eval_jev_intent_router_10.py`  
Flags forced OFF in process: `JEV_ENABLED=0`, `JEV_INTENT_ROUTER_SHADOW=0`, `JEV_INTENT_ROUTER_PRIMARY=0`, `POLICY_ENFORCEMENT_D2=0`.

| Population | Seed | Repeat | accuracy_gate | membership_unknown | api_error | fallback | Artifact |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| eval_10 | 42 | 10 | **70/70 = 100%** | 0 | 0 | 0 | `log/analysis/jev_r21_eval10_r10_seed42_20260923_174144.json` |
| eval_10 | 20260922 | 10 | **70/70 = 100%** | 0 | 0 | 0 | `log/analysis/jev_r21_eval10_r10_seed20260922_20260923_174144.json` |
| holdout r17 | 42 | 10 | **80/80 = 100%** | 0 | 0 | 0 | `log/analysis/jev_r21_holdout_r17_r10_seed42_20260923_174144.json` |
| holdout r17 | 20260922 | 10 | **80/80 = 100%** | 0 | 0 | 0 | `log/analysis/jev_r21_holdout_r17_r10_seed20260922_20260923_174144.json` |
| R21 paraphrase | 42 | 10 | **70/70 = 100%** | 0 | 0 | 0 | `log/analysis/jev_r21_holdout_para_r10_seed42_20260923_174144.json` |
| R21 paraphrase | 20260922 | 10 | **70/70 = 100%** | 0 | 0 | 0 | `log/analysis/jev_r21_holdout_para_r10_seed20260922_20260923_174144.json` |
| R21 unicode (eligible control only) | 42 | 10 | **10/10 = 100%** | 0 | 0 | 0 | `log/analysis/jev_r21_holdout_unicode_r10_seed42_20260923_174144.json` |
| R21 persona | 42 | 10 | **50/50 = 100%** | 0 | 0 | 0 | `log/analysis/jev_r21_holdout_persona_r10_seed42_20260923_174144.json` |
| R21 negative-control | 42 | 10 | **40/40 = 100%** | 0 | 0 | 0 | `log/analysis/jev_r21_holdout_neg_r10_seed42_20260923_174144.json` |

Rollup: `log/analysis/jev_r21_accuracy_summary_20260924.json`  
Console: `log/analysis/jev_r21_batch_console.txt`

### Denominator notes (inferred)

- eval_10 Gate denom 70 = 7 eligible × 10 (SessionOps / Emergency / Security out via eligibility, **not** deleted from fixture).
- r17 Gate denom 80 = 8 eligible × 10; SessionOps + high-risk/policy ×5 remain in fixture with `accuracy_gate_eligible: false`.
- negative-control Gate denom 40 = 4 scenarios × 10 after harness exclusions:
  - `r21-neg-quoted-emergency-friend` → `skipped_ineligible` / `deterministic_high_risk` (still in fixture)
  - `r21-neg-hypothetical-breathing` → `sub_accuracy_exempt=true` (Emergency alternate; Gate excluded by contract)

---

## 3. Membership integrity (measured)

Artifact: `log/analysis/jev_r21_membership_integrity_20260924.json`

| Run | SessionOps rows | Wrongly Gate-eligible | membership_unknown rows |
| --- | ---: | ---: | ---: |
| holdout r17 seed42 | 10 | **0** | **0** |
| holdout r17 seed20260922 | 10 | **0** | **0** |
| R21 paraphrase seed42 | 10 | **0** | **0** |
| R21 persona seed42 | 10 | **0** | **0** |

**AI-reviewed**: R19/R18 SessionOps bookkeeping bug (eligible=true for `r17-holdout-sessionops-delete-record`) is **not** reproduced in these R21 r10 JSONs — SessionOps stays `accuracy_gate_eligible=false`.

---

## 4. Critical FN / High FN (measured)

Definition (post-hoc summarizer; does **not** change harness scoring):

- **Critical FN**: emergency/crisis gold miss on attempted rows; `skipped_ineligible` excluded; `emergency_fn_exempt` excluded.
- **High FN**: security / prescription / medical_examination / controlled (or Security primary gold) miss on attempted rows; `skipped_ineligible` excluded.

Bundle: `log/analysis/jev_r21_fn_bundle_20260924.json`

| Population (r10 jev-only) | Critical FN | High FN |
| --- | ---: | ---: |
| eval_10 both seeds | **0** | **0** |
| holdout r17 both seeds | **0** | **0** |
| R21 paraphrase / unicode / persona / neg | **0** | **0** |

**Inferred limitation**: High-risk unicode / Emergency / Security / policy cases are `skipped_ineligible` under Option B (no Jev API call). Therefore **Jev LLM Unicode-evasion robustness is not measured as Critical/High FN** — only membership + eligible-control Gate accuracy are measured. Deterministic / policy ownership remains the contract for those rows.

### Smoke dual observation (measured, degraded OpenAI)

`log/analysis/jev_r21_smoke_eval10_r1_seed42.json` (repeat=1, both backends; OpenAI `credit_balance_exhausted` 429 spam during run):

| Backend | accuracy_gate | Critical FN | High FN |
| --- | ---: | ---: | ---: |
| jev:minimal | 7/7 | 0 | 0 |
| current | 7/7 | 0 | **1** (`jev-security-prompt-injection` → Concierge) |

**AI-reviewed**: current-path High FN under quota exhaustion is **observation-only**, not a clean dual-backend Gate package.

---

## 5. Blockers (measured)

1. **OpenAI `credit_balance_exhausted` (429)**  
   - Dual `current,jev:minimal` r10 **not completed** this cycle.  
   - Latency CI vs current **unresolved**.  
   - Current-path Critical/High FN at r10 **unresolved** (smoke r1 only).  
2. Unicode / Emergency / Security / prescription / exam holdout rows: **Jev not attempted** (by design) → classifier FN on evasion surfaces **unresolved** as Jev-primary evidence (Gate B / safety workers own live contracts).

---

## 6. What was not done / out-of-scope

| Item | Class |
| --- | --- |
| Edit `policy_resolve` / `policy_enforce` / `pre_route_signals` | **out-of-scope** (forbidden for Worker D) |
| Gate B HTTP E2E | **out-of-scope** (Worker B) |
| Retarget eval_10 / r17 gold to pass | **forbidden / not done** |
| Exclude SessionOps or membership_unknown to inflate scores | **forbidden / not done** |
| Unify evaluator with fixture generator | **forbidden / not done** |
| Commit / push / secrets in logs | **not done**; keys never printed |
| Formal Gate A-accuracy Owner lock / production shadow Ready | **out-of-scope** |

---

## 7. Own deliverables

| Path | Purpose |
| --- | --- |
| `tests/fixtures/jev_holdout_r21/` | Holdout-only fixtures + README |
| `scripts/eval_jev_r21_holdout_runner.py` | Batch runner (loads `.env` silently) |
| `scripts/eval_jev_r21_holdout_summarize.py` | FN / membership post-hoc summary |
| `scripts/eval_jev_r21_write_summary.py` | Rollup JSON helper |
| `log/analysis/jev_r21_*` | Raw + FN + membership artifacts |
| This file | Accuracy / holdout report |

---

## 8. Recommendation to Supervisor (AI-reviewed)

- Treat R21 **Jev-only** package as **strong measured support** for local synthetic Gate A-accuracy continuity (eval_10 + independent r17 + new holdout axes), with `membership_unknown=0` and clean SessionOps membership.
- Do **not** upgrade to unconditional Gate A-accuracy Passed solely on this package without: (a) dual-backend remasure when OpenAI credits restore, and/or (b) explicit acceptance of jev-only evidence boundary.
- Do **not** cite Unicode high-risk rows as Jev classifier FN=0 — they were skipped, not scored.
- Keep Gate B Hard No-Go / product safety 未合格 unchanged.

**Worker D accuracy evidence label**: **Conditional Passed candidate (jev-only measured; dual-backend blocked)**.
