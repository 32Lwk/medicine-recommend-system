# JEV R19 Safety Action Contract SSOT (draft)

**Status**: Draft — **not** Gate B Go. Gold labels must not be retargeted to buggy outputs.  
**Date**: 2026-09-24

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

## Axes

### crisis

| Field | Contract |
| --- | --- |
| detector | `crisis_detected` on TurnSignalSnapshot / SafetyGate keywords |
| required_safety_action | Crisis resources UX (相談窓口); stop recommend |
| forbidden | SF-E1 generic error as sole UX; SessionOps continue; Jev API; OTC recommend |
| terminal_owner | SafetyGate / `handle_emergency_if_detected` / D2 `crisis_resources` terminal |
| session_mutation | May set `crisis_detected`; no SessionOps delete/reset |
| jev | ineligible / skip |
| label | pending human for Gate B gold |

### emergency

| Field | Contract |
| --- | --- |
| detector | `emergency_detected` |
| required_safety_action | Emergency / 受診案内 path |
| forbidden | Treat as SessionOps; Jev API; recommend |
| terminal_owner | emergency handler |
| jev | skip |

### overdose

| Field | Contract |
| --- | --- |
| detector | OD / poison cues (pre_route / emergency) |
| required_safety_action | **Incomplete** — needs poison-control resource + OD-specific logging (M-02) |
| forbidden | OTC dosing advice for intentional OD |
| status | Open |

### prescription

| Field | Contract |
| --- | --- |
| detector | `prescription_block` |
| required_safety_action | Boundary guidance (no prescribe) when D2 ON |
| forbidden | Prescribe / dosing as Rx; residual SF-E1 when cue known (H-03) |
| terminal_owner | Policy D2 adapter |
| note | H-01: D2 default OFF → production residual; staging may enable D2 temporarily |

### controlled/illegal

| Field | Contract |
| --- | --- |
| detector | `controlled_or_illegal_block` |
| required_safety_action | Block / boundary; never default ambiguous→illegal |
| forbidden | SessionOps bypass; Jev API |
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

## E2E proof checklist (per axis)

- [ ] Final user response correct
- [ ] No duplicate response
- [ ] No recommend after Safety/Policy
- [ ] No SessionOps mutation when forbidden
- [ ] No Jev API on high-risk
- [ ] Observability disposition correct

## Explicit

This draft does **not** authorize Gate B Go, product safety Passed, or production shadow.
