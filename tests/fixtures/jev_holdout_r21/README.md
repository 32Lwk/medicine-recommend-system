# JEV R21 Independent Holdout Fixtures

**holdout_family**: `r21-holdout-v1`  
**Created**: 2026-09-24  
**Role**: Accuracy / Independent Holdout only (Worker D)

## Separation from gold / eval fixtures

| Set | Path | Role |
| --- | --- | --- |
| Training/eval gold | `tests/fixtures/jev_intent_router_eval_10.yaml` | Gate A synthetic eval_10 — **do not retarget** |
| Prior independent holdout | `tests/fixtures/jev_intent_router_holdout_r17.yaml` | R17 paraphrase holdout — **do not overwrite** |
| R21 holdout-only | `tests/fixtures/jev_holdout_r21/*.yaml` | New independent populations for R21 |

These YAML files are **holdout-only**. Labels are provisional for measurement; they must not be merged into `eval_10` gold, and gold must not be edited to pass them.

## Files

| File | Axis |
| --- | --- |
| `paraphrase.yaml` | Fresh paraphrases (not reshape of eval_10 / r17) |
| `unicode_evasion.yaml` | Zero-width / fullwidth / spaced evasion of high-risk phrases |
| `persona.yaml` | Persona-flavored single-turn utterances |
| `negative_control.yaml` | Mild / non-crisis controls (FP / wrong-route observation) |

## Evaluator

Run with existing `scripts/eval_jev_intent_router_10.py` only.  
Do **not** unify the evaluator with any fixture generator.  
Post-run FN / membership summary: `scripts/eval_jev_r21_holdout_summarize.py`.
