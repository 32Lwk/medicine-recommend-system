# JEV Overnight Commit Manifest — draft

## Commit 1 — foundation freeze (proposed)

`refactor(jev): freeze local shadow and D2 foundations`

### Include (runtime + tests)

**New**
- `src/core/session_ops_classify.py`
- `src/dialogue/routing/canonical_normalize.py`
- `src/dialogue/routing/detector_text_view.py`
- `src/dialogue/routing/medical_emergency_hints.py`
- `src/dialogue/routing/policy_*.py` (adapters,d2_pipeline,enforce,resolve,types)
- `src/dialogue/routing/pre_route_signals.py`
- `src/dialogue/routing/security_terminal_bridge.py`
- `src/dialogue/routing/sleep_med_policy.py`
- `src/dialogue/routing/turn_signal_snapshot.py`
- `src/services/jev_eligibility.py`
- matching `tests/dialogue/routing/test_*` new files (r7/r8/r10/r11/policy/pre_route/turn_signal/canonical)
- `tests/services/test_jev_eligibility*.py`
- `tests/services/test_medical_exam_br_h01.py`
- `tests/core/test_crisis_br_*.py`

**Modified**
- `config/llm_flags.py`, `config/routing_config.py` (if D2/flag only)
- `src/agents/session_agent.py`
- `src/core/crisis_detection.py`
- `src/dialogue/routing/gate.py`, `jev_router.py`
- `src/handlers/chat/chat_post_pipeline.py`, `chat_symptom_route.py`, `chat_triage_follow_ups.py`
- `src/handlers/chat_orchestrator.py`
- `src/services/jev_client.py`, `jev_decisions.py`, `jev_metrics.py`, `llm_triage.py`, `medical_examination_request.py`
- matching modified tests (gate, jev_router, crisis, session_agent, controlled_drug, medical_examination, jev_*)

### Exclude
- `scripts/eval_*` (commit 2)
- `docs/planning/**` mass (later docs commit)
- `log/**` (chore sync later)
- `tmp_*`, `..bfg-report/`, `local_outputs/`, `tools/`, `.env`
- `docs/planning/notebooklm-history/`, `ux-pdca-20260922/`

### Pre-commit tests
- foundation 164 + crisis/sleep 64 = green (2026-09-23)
