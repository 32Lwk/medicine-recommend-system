# JEV Latency Population Contract (2026-09-22)

- Owner: Agent A (Evaluation Methodology)
- Scope: `scripts/eval_jev_intent_router_10.py` report / Gate latency keys
- Gate thresholds: **unchanged** (`warm_mean_delta_ms_min=900`, `warm_scenario_cluster_ci_lower_ms_min=900`)
- Evaluation contract: `jev-intent-gate-a-v2`
- Eligibility contract: `jev-intent-eligibility-v1` (`src/services/jev_eligibility.py`)

---

## Option B — eligible-warm Gate (user freeze 2026-09-22)

SessionOps (and other non-Intent-Classification paths) are **out of Jev Latency Gate**
via **shared eligibility**, **not** scenario-id exclusion.

| Track | Population |
| --- | --- |
| 1. Product routing/safety regression | **ALL** fixture cases (`safety_regression_eligible=true`) |
| 2. Jev eligible classification accuracy | `jev_eligible=true` only (`accuracy_gate_eligible`) |
| 3. Jev eligible latency Gate | `latency_gate_eligible` = eligible ∧ warm ∧ transport_ok ∧ ¬eval_error ∧ ¬fallback |

When ineligible: harness **does not call** Jev API (`jev_attempted=false`, `jev_api_calls=0`)
but still emits a product-regression row from current/executed route.

---

## Gate 正本（canonical）

| Dimension | Canonical value |
| --- | --- |
| Population | **eligible_warm** |
| Point estimate | `warm_mean_delta_ms` (= mean of per-scenario **eligible-warm** mean diffs) |
| CI | **`latency_ci.scenario_cluster_eligible_warm`** |
| Top-level mirror | `latency_ci.mean_diff_ms` / `ci95_*` / `n_scenarios` always copy **eligible_warm** |
| `gate_canonical` string | `"scenario_cluster_eligible_warm"` |

Cold samples **must never** enter Gate eligible-warm point estimate or CI.
Ineligible rows (e.g. SessionOps alone) **must never** enter Gate CI
(even if warm). They may appear in **sensitivity** `scenario_cluster_warm`.

Request-level bootstrap (`request_level*`) is **deprecated_optimistic** / `gate_use=false`.

Pass rule (unchanged thresholds; this doc does **not** assert Passed):

- eligible-warm mean delta ≥ 900 **AND**
- eligible-warm scenario-cluster CI lower ≥ 900

---

## Always-stored populations

### Per-backend summary (`summaries[]`)

| Key | Population |
| --- | --- |
| `latency` | all (cold+warm) — **alias of `latency_all`** |
| `latency_all` | all |
| `latency_warm` | warm only (sensitivity) |
| `latency_cold` | cold only (`insufficient_n` if n &lt; `COLD_STATS_MIN_N`) |
| `latency_gate` | warm point-stats (CI Gate = eligible_warm) |

### Paired CI block (`latency_ci`)

| Key | Population | Gate? |
| --- | --- | --- |
| `scenario_cluster_eligible_warm` | latency_gate_eligible rows | **Yes** |
| `scenario_cluster_all` | cold+warm scenario means | No (sensitivity) |
| `scenario_cluster_warm` | all warm (incl. ineligible) | No (sensitivity) |
| `scenario_cluster_cold` | cold only | No (sensitivity) |
| `scenario_cluster` | **alias → `scenario_cluster_eligible_warm`** | Yes (compat) |
| `request_level_*` | request pairs | No (deprecated) |

Each `scenario_cluster_*` records `n_scenarios`, `population`, `scenario_ids`, bootstrap fields.

### Sensitivity (reference only — NOT Gate)

Under `latency_ci.latency_sensitivity`:

- `all_scenario`
- `eligible_only`
- `eligible_warm_only` (= Gate population, labeled sensitivity mirror)
- `warm_all_including_ineligible`
- `sessionops_alone` (current path_kind / eligibility reason)

---

## Pairing / exclusion rules

1. Filter rows by `latency_class` independently per backend when population ≠ all.
2. Gate pairing sets `require_latency_gate_eligible=True`.
3. Pair / cluster on `(scenario_id, run_idx)` (request) or `scenario_id` (cluster means).
4. Untagged `latency_class` defaults to **warm**.
5. Explicit exclusions (recorded under `latency_ci.exclusions`):

| Reason | Meaning |
| --- | --- |
| `api_error` | `outcome=api_error` or `connection_error` |
| `eval_error` | harness `outcome=eval_error` |
| `skipped_ineligible` / `jev_ineligible` | eligibility skip (no Jev latency) |
| `latency_gate_ineligible` | `latency_gate_eligible=false` |
| `missing_latency_ms` | no latency value |
| `backend_one_sided_missing` | after filter, only one of current/jev remains |
| `latency_class_filter` | row skipped by class filter |

Counts: `latency_ci.exclusions.counts_by_reason.{all,warm,cold,eligible_warm,...}`.

---

## CLI `--latency-mode`

```text
--latency-mode {warm,cold,all}   # default: warm
```

| Mode | Measurement | Gate top-level |
| --- | --- | --- |
| `warm` (default) | Schedule cold/warm tags as usual | Always **eligible_warm** |
| `all` | Same tags; report emphasis = all | Still eligible_warm Gate |
| `cold` | Before each `(scenario_id, run_idx)` pair: close+recreate OpenAI client; tag **all** rows `latency_class=cold` | Still eligible_warm Gate (often empty if all-cold run) |

All clusters are **always computed and stored** regardless of mode.

### Cold-mode limitation

- OpenAI client cold-start is enforced in the harness (`client.close()` + recreate).
- Jev production `evaluate_system_one` may keep an internal httpx pool; this harness **does not** call into production client lifecycle. Jev cold is best-effort / tagged only.
- Do not mix cold-tagged rows into eligible-warm Gate keys.

---

## Totals JSON sketch (eligibility tracks)

```json
{
  "totals": {
    "total_fixture_cases": 10,
    "product_regression_n": 20,
    "jev_eligible_n": 9,
    "jev_ineligible_n": 1,
    "accuracy_gate_n": 9,
    "latency_gate_n": 18,
    "excluded_by_reason": { "sessionops_fast_path": 1 },
    "unexpected_jev_call_count": 0,
    "evaluation_contract_version": "jev-intent-gate-a-v2",
    "eligibility_contract_version": "jev-intent-eligibility-v1"
  },
  "repro": {
    "commit_sha": "...",
    "dirty_worktree": true,
    "fixture_sha256": "...",
    "evaluation_contract_version": "jev-intent-gate-a-v2",
    "eligibility_contract_version": "jev-intent-eligibility-v1"
  }
}
```

Per-row flags (every result): `jev_eligible`, `jev_eligibility_reason`, `jev_attempted`,
`latency_gate_eligible`, `accuracy_gate_eligible`, `safety_regression_eligible`,
`sessionops_fast_path_suppressed`, `evaluation_contract_version`,
`eligibility_contract_version`.

---

## JSON shape (excerpt)

```json
{
  "latency_ci": {
    "gate_canonical": "scenario_cluster_eligible_warm",
    "gate_population": "eligible_warm",
    "population": "eligible_warm",
    "latency_mode": "warm",
    "mean_diff_ms": 123.45,
    "ci95_low_ms": 100.0,
    "ci95_high_ms": 140.0,
    "n_scenarios": 9,
    "level": "scenario_cluster_eligible_warm",
    "warm_mean_delta_ms": 123.45,
    "scenario_cluster_eligible_warm": {
      "available": true,
      "gate_use": true,
      "population": "eligible_warm",
      "n_scenarios": 9,
      "mean_diff_ms": 123.45,
      "ci95_low_ms": 100.0,
      "ci95_high_ms": 140.0
    },
    "scenario_cluster_warm": { "n_scenarios": 10, "gate_use": false, "sensitivity_only": true },
    "scenario_cluster_all": { "n_scenarios": 10, "gate_use": false },
    "scenario_cluster_cold": { "n_scenarios": 0, "available": false },
    "scenario_cluster": { "...": "alias of scenario_cluster_eligible_warm" },
    "latency_sensitivity": {
      "note": "Reference only — NOT Gate.",
      "all_scenario": {},
      "eligible_only": {},
      "eligible_warm_only": {},
      "sessionops_alone": {}
    },
    "gate_thresholds": {
      "warm_mean_delta_ms_min": 900,
      "warm_scenario_cluster_ci_lower_ms_min": 900
    },
    "exclusions": {
      "eligible_warm": [],
      "counts_by_reason": { "eligible_warm": {} }
    }
  }
}
```

---

## Non-claims

- This contract does **not** assert Gate A-accuracy Passed / Gate A latency Passed.
- Live API eval is out of scope for Agent A unit rounds.
- Threshold numbers are frozen; this doc freezes **population identity** (eligible-warm).
- Fixture scenario ids are never a Gate denylist.
