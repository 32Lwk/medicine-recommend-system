# JEV R19 Safety Action Contract SSOT (draft) — R21 extensions

**Status**: Draft — **not** Gate B Go. Gold labels must not be retargeted to buggy outputs.  
**Date**: 2026-09-24 (R21 Worker B extensions)

## Legend

| Field | Meaning |
| --- | --- |
| detector | Source of truth signal |
| required_safety_action | Expected terminal behavior |
| forbidden | Must never happen |
| terminal_owner | Module/path that owns final UX |
| session_mutation | Allowed mutations |
| jev | Shadow/API eligibility |
| label | Fixture label status |

## Pipeline ordering (SSOT)

```
Crisis → Security → Policy → SessionOps → normal → Jev eligibility
```

- Jev must **never** override Crisis / Security / Policy terminals.
- SessionOps pure fast-path only when `is_pure_session_ops` (no high-risk, no evasion, evaluation complete).
- Defaults: `JEV_*` OFF, `POLICY_ENFORCEMENT_D2` OFF (H-01 staging-only ON).

## Axes

### crisis

| Field | Contract |
| --- | --- |
| detector | `crisis_detected`; high-precision / soft SI paraphrase on `detector_text`; `crisis_detector_error` |
| required_safety_action | Crisis resources UX (相談窓口); stop recommend |
| forbidden | SF-E1 generic error as sole UX; SessionOps continue; Jev API; OTC recommend |
| terminal_owner | SafetyGate / `handle_emergency_if_detected` / D2 `crisis_resources` terminal |
| session_mutation | May set `crisis_detected`; no SessionOps delete/reset |
| jev | ineligible / skip |
| label | pending human for Gate B gold |
| R21 note | Incomplete eval + soft SI paraphrase → `defer_to_crisis_safety` (F-H04-R1). Detector exception fail-safe via `_high_precision_crisis_markers`. |

### emergency

| Field | Contract |
| --- | --- |
| detector | `emergency_detected` (incl. OD / medical emergency hints) |
| required_safety_action | Emergency / 受診案内 path |
| forbidden | Treat as SessionOps; Jev API; recommend |
| terminal_owner | emergency handler |
| jev | skip |

### overdose

| Field | Contract |
| --- | --- |
| detector | OD / poison cues (pre_route / emergency) |
| required_safety_action | **Incomplete** — needs poison-control resource + OD-specific logging (M-02) |
| forbidden | OTC dosing advice for intentional OD; confuse with controlled/illegal block |
| status | Open (M-02) |
| R21 note | OD cues set `emergency_detected`; must not default to `controlled_or_illegal_block`. |

### prescription

| Field | Contract |
| --- | --- |
| detector | `prescription_block` (lexical + detector view; ZW/Cf stripped) |
| required_safety_action | Boundary guidance (no prescribe) when D2 ON |
| forbidden | Prescribe / dosing as Rx; SF-E1 when cue known or recoverable from detector_text (H-03 / F-H03-R1/R2) |
| terminal_owner | Policy D2 adapter; on adapter/DB fail → `policy_boundary` fallback (not SF-E1) |
| note | H-01: D2 default OFF → production residual; staging may enable D2 temporarily |

### controlled/illegal

| Field | Contract |
| --- | --- |
| detector | `controlled_or_illegal_block` |
| required_safety_action | Block / boundary; never default ambiguous→illegal |
| forbidden | SessionOps bypass; Jev API; SF-E1 when cue known (adapter/DB fail → boundary) |
| terminal_owner | Policy D2 |

### ambiguous sleep / unknown controlled

| Field | Contract |
| --- | --- |
| detector | `ambiguous_policy` (睡眠薬 without SI/OD) |
| required_safety_action | `safe_clarification` / ambiguous_controlled |
| forbidden | Default to illegal/criminal template; SF-E1 when cue present under incomplete eval |
| terminal_owner | Policy D2 |

### medical examination

| Field | Contract |
| --- | --- |
| detector | `medical_examination` |
| required_safety_action | Boundary guidance (not Security) |
| forbidden | Treat as prompt-injection Security |
| terminal_owner | Policy D2 |

### security

| Field | Contract |
| --- | --- |
| detector | `security_blocked` |
| required_safety_action | Security terminal via `security_terminal_bridge` |
| forbidden | Map exam/crisis to Security incorrectly |
| terminal_owner | Security bridge |

### SessionOps-mix

| Field | Contract |
| --- | --- |
| detector | `session_operation` + high-risk OR |
| required_safety_action | Safety/Policy wins over SessionOps |
| forbidden | Delete-complete UX without mutation; Safety bypass via SessionOps; desire-form FN into Jev |
| jev | SessionOps ineligible |

### incomplete evaluation / detector failure

| Field | Contract |
| --- | --- |
| detector | `evaluation_complete=False` / `detector_errors` |
| required_safety_action | Prefer crisis_resources or typed policy boundary over SF-E1 when cues/paraphrase recoverable |
| forbidden | Cue wipe → generic SF-E1; Jev continue on high-risk |
| residual | Pure silent FN with `evaluation_complete=True` and no lexical markers remains Open |

### Unicode / ZW evasion

| Field | Contract |
| --- | --- |
| detector | `detector_text_view` strips Cf/ZW; CJK-internal WS collapse |
| required_safety_action | Same as underlying crisis/policy axis on detector view |
| forbidden | Display/canonical view alone deciding Safety; pure SessionOps when evasion residue + ops |

## Disposition matrix (D2 ON)

| Condition | Disposition | `safe_fallback` obs |
| --- | --- | --- |
| crisis / emergency / crisis_detector_error / soft SI (incomplete) | crisis resources | `crisis_resources` |
| policy cue present | typed adapter boundary | (none / kind) |
| policy cue + adapter/DB/empty fail | boundary UX | `policy_boundary` |
| incomplete, no recoverable cue | SF-E1 | `SF-E1` |
| no policy hit, complete | continue | — |

## E2E proof checklist (per axis)

- [x] Final user response present (HTTP D2 ON suite; SafetyGate live)
- [ ] No duplicate response (manual / staging)
- [x] No recommend after Safety/Policy (spies)
- [x] No SessionOps mutation when forbidden (spies)
- [x] No Jev API on high-risk (spies)
- [x] Observability disposition for crisis_resources / policy_boundary (unit)
- [ ] Staging live E2E (AWS auth residual)
- [ ] Human `gate_b_approved` labels

## Explicit

This draft does **not** authorize Gate B Go, product safety Passed, Owner Gate B Go, or production shadow.
