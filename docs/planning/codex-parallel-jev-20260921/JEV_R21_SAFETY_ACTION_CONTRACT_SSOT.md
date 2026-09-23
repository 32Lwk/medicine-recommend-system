# JEV R21 Safety Action Contract (SSOT draft)

**Date**: 2026-09-24  
**Status**: SSOT draft for Gate B Closed-candidate work  
**Authority**: Routing/Policy disposition only — **not** product safety Passed, **not** Gate B Owner Go

## Ordering (immutable)

1. Crisis / Emergency  
2. Security  
3. typed Policy  
4. SessionOps  
5. normal routing  
6. Jev eligibility (shadow/primary never override 1–5)

Jev is **not** the decision authority for Safety, Policy, or SessionOps.

## Action classes (minimum separation)

| Action class | Typical cues | User-facing disposition | Must NOT become |
| --- | --- | --- | --- |
| `crisis` | SI / self-harm ideation | crisis resources / hotline UX | SF-E1 system error; OTC recommend |
| `overdose` | 過量 / OD / 全部飲 | Emergency / crisis path | generic controlled-drug lecture |
| `controlled_drug_request` | illegal/controlled request | typed block (illegal vs controlled) | ambiguous sleep copy; criminal overclaim on ambiguous |
| `ambiguous_medication_request` | e.g. sleep med without clarity | safe clarification | illegal/criminal template; crisis over-route |
| `examination_request` | 診察して / 診断して | medical examination boundary | recommend; SessionOps mutation |
| `security_blocked` | injection / aggressive | security terminal | Jev attempt; recommend |
| `safe_continuation` | no high-risk cue | continue routing | false crisis |
| `system_failure_fallback` | incomplete eval without high-risk cue | SF-E1 | crisis overclaim; fake boundary |

## Explicit non-goals

- Overdose must not collapse to generic drug-policy prose only.  
- Ambiguous sleep request must not be asserted as illegal conduct.  
- General information must not be over-routed to crisis.  
- Fixture gold labels must not be retargeted to buggy outputs.

## Evidence required for Closed candidate (H-03/H-04/H-05)

- Live snapshot collection (not hand-set flags alone)  
- HTTP E2E with SafetyGate / Emergency core **unmocked**; external APIs stubbed only  
- Detector exception / adapter exception / DB mutation paths covered  
- Unicode / ZW / paraphrase / double-negation / past-tense / SessionOps-mix covered  

## Labels

Allowed: `Closed candidate` (code+tests), `AI多重医療監修 Conditional Accept candidate`  
Forbidden: `製品安全合格`, `Gate B Passed`, `Production Go`
